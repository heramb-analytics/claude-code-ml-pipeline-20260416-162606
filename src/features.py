"""Feature engineering for the transaction anomaly detection pipeline.

Reads data/processed/clean.parquet.
Engineers 8+ new features and saves:
  data/processed/features.parquet
  data/processed/feature_schema.json
Logs to logs/features.jsonl.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


CLEAN_PATH = Path("data/processed/clean.parquet")
FEATURES_PATH = Path("data/processed/features.parquet")
SCHEMA_PATH = Path("data/processed/feature_schema.json")
LOG_PATH = Path("logs/features.jsonl")


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


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add cyclical time encoding and business-hour flag.

    Args:
        df: Input DataFrame with timestamp column.

    Returns:
        DataFrame with additional columns:
          hour_sin, hour_cos, dow_sin, dow_cos, is_business_hours, month
    """
    df = df.copy()
    df["hour_sin"] = np.sin(2 * np.pi * df["hour_of_day"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour_of_day"] / 24)
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
    df["is_business_hours"] = df["hour_of_day"].between(9, 17).astype(int)
    df["month"] = pd.to_datetime(df["timestamp"]).dt.month
    return df


def add_statistical_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add amount-based statistical features.

    Args:
        df: Input DataFrame.

    Returns:
        DataFrame with additional columns:
          amount_zscore, amount_log_ratio, amount_squared_log
    """
    df = df.copy()
    mu = df["log_amount"].mean()
    sigma = df["log_amount"].std() + 1e-9
    df["amount_zscore"] = (df["log_amount"] - mu) / sigma
    df["amount_log_ratio"] = df["log_amount"] / (df["log_amount"].median() + 1e-9)
    df["amount_squared_log"] = df["log_amount"] ** 2
    return df


def add_velocity_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add transaction velocity features per customer.

    Args:
        df: Input DataFrame sorted by timestamp.

    Returns:
        DataFrame with additional columns:
          customer_txn_count, customer_avg_amount, customer_amount_std,
          customer_max_amount, amount_vs_customer_avg
    """
    df = df.copy()
    df = df.sort_values("timestamp").reset_index(drop=True)
    agg = df.groupby("customer_id")["amount"].agg(
        customer_txn_count="count",
        customer_avg_amount="mean",
        customer_amount_std="std",
        customer_max_amount="max",
    ).reset_index()
    agg["customer_amount_std"] = agg["customer_amount_std"].fillna(0)
    df = df.merge(agg, on="customer_id", how="left")
    df["amount_vs_customer_avg"] = df["amount"] / (df["customer_avg_amount"] + 1e-9)
    return df


def add_categorical_features(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode merchant_category and add risk score.

    Args:
        df: Input DataFrame.

    Returns:
        DataFrame with merchant category dummies and merchant_risk_score.
    """
    df = df.copy()
    dummies = pd.get_dummies(df["merchant_category"], prefix="cat", dtype=int)
    df = pd.concat([df, dummies], axis=1)
    risk_map = {"online": 3, "travel": 3, "retail": 2, "restaurant": 1, "grocery": 1, "gas": 1}
    df["merchant_risk_score"] = df["merchant_category"].map(risk_map).fillna(2).astype(int)
    return df


def build_feature_schema(df: pd.DataFrame, engineered_cols: list[str]) -> list[dict[str, str]]:
    """Build a feature schema list for each engineered column.

    Args:
        df: Final DataFrame.
        engineered_cols: Names of engineered feature columns.

    Returns:
        List of dicts with name, dtype, description.
    """
    descriptions = {
        "hour_sin": "Sine of hour_of_day for cyclical encoding",
        "hour_cos": "Cosine of hour_of_day for cyclical encoding",
        "dow_sin": "Sine of day_of_week for cyclical encoding",
        "dow_cos": "Cosine of day_of_week for cyclical encoding",
        "is_business_hours": "1 if transaction occurred between 9–17h",
        "month": "Calendar month extracted from timestamp",
        "amount_zscore": "Z-score of log(amount+1)",
        "amount_log_ratio": "Ratio of log_amount to median log_amount",
        "amount_squared_log": "Square of log(amount+1)",
        "customer_txn_count": "Total transactions for this customer",
        "customer_avg_amount": "Mean transaction amount for this customer",
        "customer_amount_std": "Std deviation of transaction amount for this customer",
        "customer_max_amount": "Max transaction amount seen for this customer",
        "amount_vs_customer_avg": "Ratio of current amount to customer's average",
        "merchant_risk_score": "Risk score (1–3) for merchant category",
    }
    schema = []
    for col in engineered_cols:
        schema.append({
            "name": col,
            "dtype": str(df[col].dtype),
            "description": descriptions.get(col, "Engineered feature"),
        })
    return schema


def run() -> pd.DataFrame:
    """Execute full feature engineering pipeline.

    Returns:
        DataFrame with all engineered features.
    """
    _log("features_start", {})
    df = pd.read_parquet(CLEAN_PATH)
    _log("data_loaded", {"rows": len(df)})

    original_cols = set(df.columns)

    df = add_time_features(df)
    df = add_statistical_features(df)
    df = add_velocity_features(df)
    df = add_categorical_features(df)

    engineered_cols = [c for c in df.columns if c not in original_cols]
    _log("features_engineered", {"count": len(engineered_cols), "names": engineered_cols})

    df.to_parquet(FEATURES_PATH, index=False)
    _log("saved_features", {"path": str(FEATURES_PATH), "rows": len(df)})

    schema = build_feature_schema(df, engineered_cols)
    SCHEMA_PATH.write_text(json.dumps(schema, indent=2))
    _log("saved_schema", {"path": str(SCHEMA_PATH), "features": len(schema)})

    _log("features_end", {"total_cols": len(df.columns)})
    print(f"Feature engineering complete: {len(engineered_cols)} new features → {FEATURES_PATH}")
    return df


if __name__ == "__main__":
    run()
