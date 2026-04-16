"""FastAPI inference service for the transaction anomaly detection pipeline.

Endpoints:
  POST /predict        — predict anomaly for a transaction
  POST /predict/batch  — batch predictions
  GET  /health         — liveness probe
  GET  /metrics        — model performance metrics
  GET  /feature-schema — list of engineered features

Every response includes request_id + timestamp.
"""

import json
import pickle
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

MODELS_DIR = Path("models")
SCHEMA_PATH = Path("data/processed/feature_schema.json")


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Pre-load models at startup, release resources on shutdown."""
    _load_models()
    yield


app = FastAPI(
    title="Transaction Anomaly Detection API",
    version="1.0.0",
    description="Detects fraudulent/anomalous transactions using Isolation Forest + XGBoost.",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Model loading (lazy, loaded once on first request or startup)
# ---------------------------------------------------------------------------
_xgb_bundle: dict[str, Any] | None = None
_if_bundle: dict[str, Any] | None = None


def _load_models() -> None:
    """Load XGBoost and Isolation Forest bundles from disk (idempotent)."""
    global _xgb_bundle, _if_bundle
    if _xgb_bundle is None:
        xgb_path = MODELS_DIR / "xgboost.pkl"
        if not xgb_path.exists():
            raise RuntimeError(f"XGBoost model not found: {xgb_path}")
        with xgb_path.open("rb") as fh:
            _xgb_bundle = pickle.load(fh)
    if _if_bundle is None:
        if_path = MODELS_DIR / "isolation_forest.pkl"
        if not if_path.exists():
            raise RuntimeError(f"Isolation Forest model not found: {if_path}")
        with if_path.open("rb") as fh:
            _if_bundle = pickle.load(fh)



# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class TransactionInput(BaseModel):
    """Input schema for a single transaction prediction request."""

    amount: float = Field(..., gt=0, description="Transaction amount in USD")
    num_prev_txn_1h: int = Field(0, ge=0, description="Number of prior transactions in last hour")
    distance_from_home_km: float = Field(0.0, ge=0, description="Distance from home location")
    hour_of_day: int = Field(..., ge=0, le=23, description="Hour of transaction (0–23)")
    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Mon, 6=Sun)")
    card_present: bool = Field(True, description="Whether physical card was used")
    is_foreign: int = Field(0, ge=0, le=1, description="1 if country != US")
    merchant_risk_score: int = Field(2, ge=1, le=3, description="Merchant risk score (1=low, 3=high)")
    customer_txn_count: int = Field(1, ge=1, description="Total transactions for this customer")
    customer_avg_amount: float = Field(50.0, gt=0, description="Customer's average transaction amount")
    customer_amount_std: float = Field(10.0, ge=0, description="Std dev of customer transaction amounts")
    customer_max_amount: float = Field(100.0, gt=0, description="Customer's max transaction amount")


class PredictionResponse(BaseModel):
    """Response schema for a single prediction."""

    request_id: str
    timestamp: str
    is_anomaly: int
    anomaly_probability: float
    model: str
    input_features: dict[str, float]


class BatchPredictionResponse(BaseModel):
    """Response schema for a batch prediction."""

    request_id: str
    timestamp: str
    predictions: list[dict[str, Any]]
    total: int
    anomaly_count: int


class HealthResponse(BaseModel):
    """Response schema for health check."""

    request_id: str
    timestamp: str
    status: str
    models_loaded: list[str]


class MetricsResponse(BaseModel):
    """Response schema for model metrics."""

    request_id: str
    timestamp: str
    metrics: dict[str, Any]


# ---------------------------------------------------------------------------
# Feature engineering (mirrors src/features.py for single-row inference)
# ---------------------------------------------------------------------------

def _build_feature_vector(txn: TransactionInput, feature_cols: list[str]) -> np.ndarray:
    """Construct the model input vector from a TransactionInput.

    Args:
        txn: Incoming transaction data.
        feature_cols: Ordered list of features the model was trained on.

    Returns:
        1-D numpy array aligned with feature_cols.
    """
    import math

    log_amount = math.log1p(txn.amount)
    median_log = math.log1p(txn.customer_avg_amount)  # approximate
    global_log_median = 3.5  # approximate global log-amount median

    feature_map = {
        "log_amount": log_amount,
        "amount_zscore": (log_amount - 3.5) / 1.2,
        "amount_log_ratio": log_amount / (global_log_median + 1e-9),
        "amount_squared_log": log_amount ** 2,
        "num_prev_txn_1h": float(txn.num_prev_txn_1h),
        "distance_from_home_km": txn.distance_from_home_km,
        "hour_sin": math.sin(2 * math.pi * txn.hour_of_day / 24),
        "hour_cos": math.cos(2 * math.pi * txn.hour_of_day / 24),
        "dow_sin": math.sin(2 * math.pi * txn.day_of_week / 7),
        "dow_cos": math.cos(2 * math.pi * txn.day_of_week / 7),
        "is_business_hours": float(9 <= txn.hour_of_day <= 17),
        "is_weekend": float(txn.day_of_week >= 5),
        "is_night": float(txn.hour_of_day >= 22 or txn.hour_of_day <= 5),
        "is_foreign": float(txn.is_foreign),
        "card_present": float(txn.card_present),
        "merchant_risk_score": float(txn.merchant_risk_score),
        "customer_txn_count": float(txn.customer_txn_count),
        "customer_avg_amount": txn.customer_avg_amount,
        "customer_amount_std": txn.customer_amount_std,
        "customer_max_amount": txn.customer_max_amount,
        "amount_vs_customer_avg": txn.amount / (txn.customer_avg_amount + 1e-9),
    }
    return np.array([feature_map.get(col, 0.0) for col in feature_cols], dtype=float)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe — returns OK when models are loaded."""
    _load_models()
    loaded = []
    if _xgb_bundle is not None:
        loaded.append("xgboost")
    if _if_bundle is not None:
        loaded.append("isolation_forest")
    return HealthResponse(
        request_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        status="ok",
        models_loaded=loaded,
    )


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics() -> MetricsResponse:
    """Return stored model evaluation metrics."""
    summary_path = MODELS_DIR / "training_summary.json"
    if not summary_path.exists():
        raise HTTPException(status_code=404, detail="Training summary not found.")
    metrics = json.loads(summary_path.read_text())
    return MetricsResponse(
        request_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        metrics=metrics,
    )


@app.get("/feature-schema")
async def feature_schema() -> dict[str, Any]:
    """Return the feature engineering schema."""
    if not SCHEMA_PATH.exists():
        raise HTTPException(status_code=404, detail="Feature schema not found.")
    schema = json.loads(SCHEMA_PATH.read_text())
    return {
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "features": schema,
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict(txn: TransactionInput) -> PredictionResponse:
    """Predict whether a single transaction is anomalous using XGBoost.

    Args:
        txn: Transaction features.

    Returns:
        Prediction with probability, request_id, and timestamp.
    """
    _load_models()
    feature_cols: list[str] = _xgb_bundle["feature_cols"]  # type: ignore[index]
    xgb_model = _xgb_bundle["model"]  # type: ignore[index]

    x = _build_feature_vector(txn, feature_cols).reshape(1, -1)
    proba = float(xgb_model.predict_proba(x)[0, 1])
    label = int(proba >= 0.5)

    return PredictionResponse(
        request_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        is_anomaly=label,
        anomaly_probability=round(proba, 4),
        model="xgboost",
        input_features={k: float(v) for k, v in txn.model_dump().items() if isinstance(v, (int, float, bool))},
    )


@app.post("/predict/batch", response_model=BatchPredictionResponse)
async def predict_batch(transactions: list[TransactionInput]) -> BatchPredictionResponse:
    """Predict anomaly status for a batch of transactions.

    Args:
        transactions: List of transaction inputs.

    Returns:
        Batch predictions with summary counts.
    """
    if not transactions:
        raise HTTPException(status_code=400, detail="transactions list is empty.")
    _load_models()
    feature_cols: list[str] = _xgb_bundle["feature_cols"]  # type: ignore[index]
    xgb_model = _xgb_bundle["model"]  # type: ignore[index]

    X = np.stack([_build_feature_vector(t, feature_cols) for t in transactions])
    probas = xgb_model.predict_proba(X)[:, 1]
    labels = (probas >= 0.5).astype(int)

    predictions = [
        {"index": i, "is_anomaly": int(labels[i]), "anomaly_probability": round(float(probas[i]), 4)}
        for i in range(len(transactions))
    ]

    return BatchPredictionResponse(
        request_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        predictions=predictions,
        total=len(transactions),
        anomaly_count=int(labels.sum()),
    )
