"""Unit tests for src/validate.py."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from validate import run_checks


@pytest.fixture()
def valid_df() -> pd.DataFrame:
    """Return a DataFrame that should pass all 12 checks."""
    import numpy as np
    n = 2000
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "transaction_id": [f"TXN{i:07d}" for i in range(n)],
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="5min"),
            "amount": rng.lognormal(3.5, 1.0, n).clip(0.01, 99999),
            "merchant_category": rng.choice(["grocery", "gas", "restaurant", "retail", "online", "travel"], n),
            "card_present": rng.choice([True, False], n),
            "country_code": rng.choice(["US", "CA"], n),
            "hour_of_day": rng.integers(0, 24, n),
            "day_of_week": rng.integers(0, 7, n),
            "customer_id": rng.integers(1000, 5000, n),
            "merchant_id": rng.integers(100, 2000, n),
            "num_prev_txn_1h": rng.integers(0, 5, n),
            "distance_from_home_km": rng.exponential(10, n),
            "is_anomaly": rng.choice([0, 1], n, p=[0.95, 0.05]),
        }
    )


class TestRunChecks:
    def test_all_checks_pass_on_valid_data(self, valid_df: pd.DataFrame) -> None:
        results = run_checks(valid_df)
        failed = [r for r in results if not r["passed"]]
        assert len(failed) == 0, f"Unexpected failures: {failed}"

    def test_exactly_12_checks(self, valid_df: pd.DataFrame) -> None:
        results = run_checks(valid_df)
        assert len(results) == 12

    def test_row_count_fails_on_small_df(self, valid_df: pd.DataFrame) -> None:
        tiny = valid_df.head(10)
        results = run_checks(tiny)
        rc = next(r for r in results if r["check"] == "row_count_minimum")
        assert not rc["passed"]

    def test_missing_column_fails(self, valid_df: pd.DataFrame) -> None:
        df = valid_df.drop(columns=["amount"])
        results = run_checks(df)
        # amount_range check would error — but required_columns should fail first
        req = next(r for r in results if r["check"] == "required_columns")
        assert not req["passed"]

    def test_anomaly_rate_check(self, valid_df: pd.DataFrame) -> None:
        # Force anomaly rate to 0 — should fail anomaly_rate_range
        df = valid_df.copy()
        df["is_anomaly"] = 0
        results = run_checks(df)
        ar = next(r for r in results if r["check"] == "anomaly_rate_range")
        assert not ar["passed"]
