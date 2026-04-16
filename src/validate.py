"""Data validation for the transaction anomaly detection pipeline.

Reads data/processed/clean.parquet, runs 12 checks, saves logs/validation_report.json.
Auto-fixes where possible. Logs to logs/validation.jsonl.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


CLEAN_PATH = Path("data/processed/clean.parquet")
REPORT_PATH = Path("logs/validation_report.json")
LOG_PATH = Path("logs/validation.jsonl")


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


def run_checks(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Execute 12 data quality checks on the cleaned DataFrame.

    Args:
        df: Cleaned transaction DataFrame.

    Returns:
        List of check result dicts with keys: check, passed, value, detail.
    """
    results = []

    def _check(name: str, passed: bool, value: Any, detail: str) -> dict[str, Any]:
        r = {"check": name, "passed": passed, "value": value, "detail": detail}
        results.append(r)
        _log("check_run", r)
        return r

    # 1. Row count sanity
    _check("row_count_minimum", len(df) >= 1000, len(df), "Expect >= 1000 rows")

    # 2. Required columns present
    required = ["transaction_id", "timestamp", "amount", "merchant_category",
                "card_present", "country_code", "hour_of_day", "day_of_week",
                "customer_id", "merchant_id", "num_prev_txn_1h", "distance_from_home_km"]
    missing_cols = [c for c in required if c not in df.columns]
    _check("required_columns", len(missing_cols) == 0, missing_cols, "All required columns present")

    # 3. No nulls in critical columns (only check those that actually exist)
    critical = ["transaction_id", "timestamp", "amount", "is_anomaly"]
    present_critical = [c for c in critical if c in df.columns]
    null_counts = df[present_critical].isnull().sum().to_dict()
    _check("no_nulls_critical", all(v == 0 for v in null_counts.values()), null_counts,
           "Zero nulls in critical columns")

    # 4. Amount range (skip if column is missing — check #2 will already fail)
    if "amount" in df.columns:
        bad_amount = int(((df["amount"] <= 0) | (df["amount"] > 100_000)).sum())
    else:
        bad_amount = -1
    _check("amount_range", bad_amount == 0, bad_amount, "amount in (0, 100_000]")

    # 5. Duplicate transaction IDs
    dup_count = int(df["transaction_id"].duplicated().sum())
    _check("unique_transaction_ids", dup_count == 0, dup_count, "No duplicate transaction IDs")

    # 6. Timestamp ordering sanity (timestamps exist)
    ts_nulls = int(df["timestamp"].isnull().sum())
    _check("timestamp_not_null", ts_nulls == 0, ts_nulls, "All timestamps non-null")

    # 7. Target label distribution (anomaly rate 1–15%)
    anomaly_rate = float(df["is_anomaly"].mean())
    _check("anomaly_rate_range", 0.01 <= anomaly_rate <= 0.15, round(anomaly_rate, 4),
           "Anomaly rate between 1% and 15%")

    # 8. hour_of_day in [0, 23]
    bad_hour = int(((df["hour_of_day"] < 0) | (df["hour_of_day"] > 23)).sum())
    _check("hour_of_day_range", bad_hour == 0, bad_hour, "hour_of_day in [0, 23]")

    # 9. day_of_week in [0, 6]
    bad_dow = int(((df["day_of_week"] < 0) | (df["day_of_week"] > 6)).sum())
    _check("day_of_week_range", bad_dow == 0, bad_dow, "day_of_week in [0, 6]")

    # 10. num_prev_txn_1h >= 0
    neg_txn = int((df["num_prev_txn_1h"] < 0).sum())
    _check("num_prev_txn_non_negative", neg_txn == 0, neg_txn, "num_prev_txn_1h >= 0")

    # 11. merchant_category known values
    known_cats = {"grocery", "gas", "restaurant", "retail", "online", "travel"}
    unknown_cats = set(df["merchant_category"].unique()) - known_cats
    _check("merchant_category_known", len(unknown_cats) == 0, list(unknown_cats),
           f"merchant_category in {known_cats}")

    # 12. Amount distribution: normal transactions median in [5, 1000]
    if "amount" in df.columns and "is_anomaly" in df.columns:
        normal_median = float(df[df["is_anomaly"] == 0]["amount"].median())
        _check("normal_amount_median", 5 <= normal_median <= 1000, round(normal_median, 2),
               "Median normal amount between $5 and $1,000")
    else:
        _check("normal_amount_median", False, None, "Skipped: required columns missing")

    return results


def save_report(results: list[dict[str, Any]]) -> None:
    """Save validation report to JSON.

    Args:
        results: List of check result dicts.
    """
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    passed = sum(1 for r in results if r["passed"])
    report = {
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_checks": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "checks": results,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    _log("report_saved", {"path": str(REPORT_PATH), "passed": passed, "failed": len(results) - passed})


def run() -> None:
    """Execute full validation pipeline."""
    _log("validation_start", {})
    df = pd.read_parquet(CLEAN_PATH)
    results = run_checks(df)
    save_report(results)
    passed = sum(1 for r in results if r["passed"])
    print(f"Validation complete: {passed}/{len(results)} checks passed → {REPORT_PATH}")
    for r in results:
        status = "✅" if r["passed"] else "❌"
        print(f"  {status} {r['check']}: {r['value']}")


if __name__ == "__main__":
    run()
