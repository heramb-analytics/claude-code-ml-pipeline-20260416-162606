"""Unit tests for src/features.py."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from features import (
    add_categorical_features,
    add_statistical_features,
    add_time_features,
    add_velocity_features,
)


@pytest.fixture()
def base_df() -> pd.DataFrame:
    """Minimal DataFrame that mirrors the clean.parquet schema."""
    return pd.DataFrame(
        {
            "transaction_id": [f"TXN{i:07d}" for i in range(5)],
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="h"),
            "amount": [100.0, 5000.0, 0.5, 250.0, 80.0],
            "log_amount": np.log1p([100.0, 5000.0, 0.5, 250.0, 80.0]),
            "merchant_category": ["grocery", "online", "travel", "retail", "gas"],
            "card_present": [True, False, False, True, True],
            "country_code": ["US", "NG", "US", "US", "CA"],
            "hour_of_day": [10, 3, 14, 22, 9],
            "day_of_week": [0, 6, 2, 4, 5],
            "customer_id": [1, 2, 1, 3, 2],
            "merchant_id": [100, 200, 300, 100, 200],
            "num_prev_txn_1h": [1, 0, 2, 1, 0],
            "distance_from_home_km": [5.0, 500.0, 2.0, 10.0, 300.0],
            "is_anomaly": [0, 1, 0, 0, 1],
        }
    )


class TestAddTimeFeatures:
    def test_cyclical_columns_created(self, base_df: pd.DataFrame) -> None:
        df = add_time_features(base_df)
        for col in ["hour_sin", "hour_cos", "dow_sin", "dow_cos", "is_business_hours", "month"]:
            assert col in df.columns

    def test_cyclical_range(self, base_df: pd.DataFrame) -> None:
        df = add_time_features(base_df)
        assert df["hour_sin"].between(-1, 1).all()
        assert df["hour_cos"].between(-1, 1).all()

    def test_business_hours_flag(self, base_df: pd.DataFrame) -> None:
        df = add_time_features(base_df)
        assert df.loc[0, "is_business_hours"] == 1   # hour 10
        assert df.loc[1, "is_business_hours"] == 0   # hour 3


class TestAddStatisticalFeatures:
    def test_zscore_mean_near_zero(self, base_df: pd.DataFrame) -> None:
        df = add_statistical_features(base_df)
        assert abs(df["amount_zscore"].mean()) < 1.0

    def test_columns_created(self, base_df: pd.DataFrame) -> None:
        df = add_statistical_features(base_df)
        for col in ["amount_zscore", "amount_log_ratio", "amount_squared_log"]:
            assert col in df.columns


class TestAddVelocityFeatures:
    def test_columns_created(self, base_df: pd.DataFrame) -> None:
        df = add_velocity_features(base_df)
        for col in ["customer_txn_count", "customer_avg_amount", "customer_amount_std",
                    "customer_max_amount", "amount_vs_customer_avg"]:
            assert col in df.columns

    def test_customer_txn_count_correct(self, base_df: pd.DataFrame) -> None:
        df = add_velocity_features(base_df)
        # customer_id=1 appears twice
        assert df[df["customer_id"] == 1]["customer_txn_count"].iloc[0] == 2
        # customer_id=3 appears once
        assert df[df["customer_id"] == 3]["customer_txn_count"].iloc[0] == 1


class TestAddCategoricalFeatures:
    def test_dummy_columns_created(self, base_df: pd.DataFrame) -> None:
        df = add_categorical_features(base_df)
        dummy_cols = [c for c in df.columns if c.startswith("cat_")]
        assert len(dummy_cols) >= 1

    def test_risk_score_in_range(self, base_df: pd.DataFrame) -> None:
        df = add_categorical_features(base_df)
        assert df["merchant_risk_score"].between(1, 3).all()

    def test_online_high_risk(self, base_df: pd.DataFrame) -> None:
        df = add_categorical_features(base_df)
        online_row = df[df["merchant_category"] == "online"].iloc[0]
        assert online_row["merchant_risk_score"] == 3
