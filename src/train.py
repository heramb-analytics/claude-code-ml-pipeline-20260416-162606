"""Model training for the transaction anomaly detection pipeline.

Trains Isolation Forest (unsupervised) and XGBoost (supervised) models.
Saves {model}.pkl + {model}_metrics.json to models/.
Logs to logs/train.jsonl.
"""

import json
import pickle
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


FEATURES_PATH = Path("data/processed/features.parquet")
MODELS_DIR = Path("models")
LOG_PATH = Path("logs/train.jsonl")

# Feature columns used for both models
FEATURE_COLS = [
    "log_amount", "amount_zscore", "amount_log_ratio", "amount_squared_log",
    "num_prev_txn_1h", "distance_from_home_km",
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    "is_business_hours", "is_weekend", "is_night", "is_foreign",
    "card_present", "merchant_risk_score",
    "customer_txn_count", "customer_avg_amount", "customer_amount_std",
    "customer_max_amount", "amount_vs_customer_avg",
]


def _log(event: str, payload: dict[str, Any]) -> None:
    """Append a JSON Lines log entry.

    Args:
        event: Short event name.
        payload: Additional data to record.
    """
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **payload,
    }
    with LOG_PATH.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


def _save_model(name: str, obj: Any) -> Path:
    """Pickle a model to models/{name}.pkl.

    Args:
        name: Model name (filename stem).
        obj: Object to pickle.

    Returns:
        Path to saved pkl file.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = MODELS_DIR / f"{name}.pkl"
    with path.open("wb") as fh:
        pickle.dump(obj, fh)
    return path


def _save_metrics(name: str, metrics: dict[str, Any]) -> Path:
    """Save metrics JSON alongside the model.

    Args:
        name: Model name (filename stem).
        metrics: Metrics dictionary.

    Returns:
        Path to saved JSON file.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = MODELS_DIR / f"{name}_metrics.json"
    payload = {
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": name,
        **metrics,
    }
    path.write_text(json.dumps(payload, indent=2))
    return path


def train_isolation_forest(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    contamination: float = 0.05,
) -> dict[str, Any]:
    """Train an Isolation Forest anomaly detector.

    Args:
        X_train: Training feature matrix.
        X_test: Test feature matrix.
        y_test: True test labels (1 = anomaly).
        contamination: Expected proportion of anomalies.

    Returns:
        Dict with model, scaler, and metrics.
    """
    scaler = StandardScaler()
    X_tr = scaler.fit_transform(X_train)
    X_te = scaler.transform(X_test)

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_tr)

    # IsolationForest predicts -1=anomaly, 1=normal → map to 1=anomaly, 0=normal
    raw_pred = model.predict(X_te)
    y_pred = np.where(raw_pred == -1, 1, 0)
    # Scores: lower = more anomalous
    scores = -model.decision_function(X_te)  # negate so higher = more anomalous

    metrics = {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, scores)), 4),
        "average_precision": round(float(average_precision_score(y_test, scores)), 4),
        "test_samples": int(len(y_test)),
        "anomaly_predicted": int(y_pred.sum()),
        "anomaly_actual": int(y_test.sum()),
    }
    _log("isolation_forest_trained", metrics)
    return {"model": model, "scaler": scaler, "metrics": metrics}


def train_xgboost(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
) -> dict[str, Any]:
    """Train an XGBoost binary classifier for supervised anomaly detection.

    Args:
        X_train: Training feature matrix.
        X_test: Test feature matrix.
        y_train: Training labels.
        y_test: Test labels.

    Returns:
        Dict with model and metrics.
    """
    scale_pos_weight = float((y_train == 0).sum() / (y_train == 1).sum())

    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        use_label_encoder=False,
        eval_metric="aucpr",
        random_state=42,
        n_jobs=-1,
        verbosity=0,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, y_proba)), 4),
        "average_precision": round(float(average_precision_score(y_test, y_proba)), 4),
        "test_samples": int(len(y_test)),
        "anomaly_predicted": int(y_pred.sum()),
        "anomaly_actual": int(y_test.sum()),
        "scale_pos_weight": round(scale_pos_weight, 2),
    }
    _log("xgboost_trained", metrics)
    return {"model": model, "metrics": metrics}


def run() -> None:
    """Execute the full model training pipeline."""
    _log("train_start", {})
    df = pd.read_parquet(FEATURES_PATH)

    # Align available feature cols
    available = [c for c in FEATURE_COLS if c in df.columns]
    X = df[available].values.astype(float)
    y = df["is_anomaly"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    _log("data_split", {"train": len(X_train), "test": len(X_test), "anomaly_rate_train": float(y_train.mean())})

    # --- Isolation Forest ---
    print("Training Isolation Forest ...")
    if_result = train_isolation_forest(X_train, X_test, y_test)
    _save_model("isolation_forest", {"model": if_result["model"], "scaler": if_result["scaler"], "feature_cols": available})
    _save_metrics("isolation_forest", if_result["metrics"])
    print(f"  IF F1={if_result['metrics']['f1']}  AUC={if_result['metrics']['roc_auc']}")

    # --- XGBoost ---
    print("Training XGBoost ...")
    xgb_result = train_xgboost(X_train, X_test, y_train, y_test)
    _save_model("xgboost", {"model": xgb_result["model"], "feature_cols": available})
    _save_metrics("xgboost", xgb_result["metrics"])
    print(f"  XGB F1={xgb_result['metrics']['f1']}  AUC={xgb_result['metrics']['roc_auc']}")

    # --- Save combined summary ---
    summary = {
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "models": {
            "isolation_forest": if_result["metrics"],
            "xgboost": xgb_result["metrics"],
        },
        "feature_cols": available,
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
    }
    (MODELS_DIR / "training_summary.json").write_text(json.dumps(summary, indent=2))

    _log("train_end", {"models_saved": ["isolation_forest", "xgboost"]})
    print(f"\nTraining complete. Models saved to {MODELS_DIR}/")


if __name__ == "__main__":
    run()
