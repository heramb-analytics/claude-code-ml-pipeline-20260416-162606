"""Data ingestion and preprocessing for the transaction anomaly detection pipeline.

Reads data/raw/transactions.csv, cleans and validates, saves data/processed/clean.parquet.
Logs every operation to logs/ingest.jsonl.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


class DataQualityError(Exception):
    """Raised when a critical data quality check fails."""


RAW_PATH = Path("data/raw/transactions.csv")
PROCESSED_DIR = Path("data/processed")
CLEAN_PATH = PROCESSED_DIR / "clean.parquet"
LOG_PATH = Path("logs/ingest.jsonl")

REQUIRED_COLUMNS = [
    "transaction_id",
    "timestamp",
    "amount",
    "merchant_category",
    "card_present",
    "country_code",
    "hour_of_day",
    "day_of_week",
    "customer_id",
    "merchant_id",
    "num_prev_txn_1h",
    "distance_from_home_km",
    "is_anomaly",
]


def _log(event: str, payload: dict[str, Any]) -> None:
    """Append a JSON Lines entry to the ingest log.

    Args:
        event: Short event name.
        payload: Key/value data to record.
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


def load_raw(path: Path = RAW_PATH) -> pd.DataFrame:
    """Load the raw transactions CSV.

    Args:
        path: Path to the CSV file.

    Returns:
        Raw DataFrame.

    Raises:
        DataQualityError: If the file is missing or has no rows.
    """
    if not path.exists():
        raise DataQualityError(f"Raw file not found: {path}")
    df = pd.read_csv(path, parse_dates=["timestamp"])
    if df.empty:
        raise DataQualityError("Raw file contains no rows.")
    _log("load_raw", {"path": str(path), "rows": len(df), "cols": list(df.columns)})
    return df


def validate_schema(df: pd.DataFrame) -> None:
    """Check that all required columns are present.

    Args:
        df: DataFrame to validate.

    Raises:
        DataQualityError: If any required column is missing.
    """
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise DataQualityError(f"Missing required columns: {missing}")
    _log("validate_schema", {"status": "ok", "columns": list(df.columns)})


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the raw transaction DataFrame.

    Steps:
      1. Drop exact duplicates.
      2. Drop rows with null transaction_id or timestamp.
      3. Clip amount to [0.01, 100_000].
      4. Fill remaining nulls with sensible defaults.
      5. Normalise string columns to lowercase.
      6. Cast types.

    Args:
        df: Raw DataFrame.

    Returns:
        Cleaned DataFrame.
    """
    before = len(df)
    df = df.drop_duplicates(subset=["transaction_id"])
    df = df.dropna(subset=["transaction_id", "timestamp"])
    df["amount"] = df["amount"].clip(lower=0.01, upper=100_000)
    df["num_prev_txn_1h"] = df["num_prev_txn_1h"].fillna(0).astype(int)
    df["distance_from_home_km"] = df["distance_from_home_km"].fillna(df["distance_from_home_km"].median())
    df["merchant_category"] = df["merchant_category"].str.lower().str.strip()
    df["country_code"] = df["country_code"].str.upper().str.strip()
    df["card_present"] = df["card_present"].astype(bool)
    df["is_anomaly"] = df["is_anomaly"].astype(int)
    after = len(df)
    _log("clean", {"rows_before": before, "rows_after": after, "dropped": before - after})
    return df.reset_index(drop=True)


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add lightweight derived columns useful for downstream modelling.

    Args:
        df: Cleaned DataFrame.

    Returns:
        DataFrame with additional columns:
          - is_weekend: 1 if day_of_week in {5, 6}
          - is_night: 1 if hour_of_day between 22 and 6
          - log_amount: natural log of amount
          - is_foreign: 1 if country_code != 'US'
    """
    df = df.copy()
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["is_night"] = df["hour_of_day"].apply(lambda h: 1 if (h >= 22 or h <= 5) else 0)
    df["log_amount"] = np.log1p(df["amount"])
    df["is_foreign"] = (df["country_code"] != "US").astype(int)
    _log("add_derived_columns", {"new_cols": ["is_weekend", "is_night", "log_amount", "is_foreign"]})
    return df


def save_parquet(df: pd.DataFrame, path: Path = CLEAN_PATH) -> None:
    """Save DataFrame to Parquet.

    Args:
        df: DataFrame to save.
        path: Destination path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    _log("save_parquet", {"path": str(path), "rows": len(df), "size_kb": round(path.stat().st_size / 1024, 1)})


def run() -> pd.DataFrame:
    """Execute the full ingestion pipeline.

    Returns:
        Cleaned and enriched DataFrame saved to CLEAN_PATH.
    """
    _log("pipeline_start", {"stage": "ingest"})
    df = load_raw()
    validate_schema(df)
    df = clean(df)
    df = add_derived_columns(df)
    save_parquet(df)
    _log("pipeline_end", {"stage": "ingest", "final_rows": len(df)})
    print(f"Ingestion complete: {len(df):,} rows → {CLEAN_PATH}")
    return df


if __name__ == "__main__":
    run()
