"""Unit tests for src/ingest.py."""

import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from ingest import (
    DataQualityError,
    REQUIRED_COLUMNS,
    add_derived_columns,
    clean,
    validate_schema,
)


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """Return a minimal valid DataFrame matching the expected schema."""
    return pd.DataFrame(
        {
            "transaction_id": ["TXN0000001", "TXN0000002", "TXN0000003"],
            "timestamp": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "amount": [100.0, 50.0, 200.0],
            "merchant_category": ["grocery", "online", "retail"],
            "card_present": [True, False, True],
            "country_code": ["US", "CA", "US"],
            "hour_of_day": [10, 2, 15],
            "day_of_week": [0, 1, 2],
            "customer_id": [1001, 1002, 1003],
            "merchant_id": [501, 502, 503],
            "num_prev_txn_1h": [1, 0, 2],
            "distance_from_home_km": [5.0, 300.0, 2.0],
            "is_anomaly": [0, 1, 0],
        }
    )


class TestValidateSchema:
    def test_passes_with_all_columns(self, sample_df: pd.DataFrame) -> None:
        validate_schema(sample_df)  # should not raise

    def test_raises_on_missing_column(self, sample_df: pd.DataFrame) -> None:
        df = sample_df.drop(columns=["amount"])
        with pytest.raises(DataQualityError, match="Missing required columns"):
            validate_schema(df)


class TestClean:
    def test_drops_duplicates(self, sample_df: pd.DataFrame) -> None:
        df = pd.concat([sample_df, sample_df.iloc[[0]]], ignore_index=True)
        cleaned = clean(df)
        assert cleaned["transaction_id"].duplicated().sum() == 0

    def test_clips_amount(self, sample_df: pd.DataFrame) -> None:
        sample_df.loc[0, "amount"] = -50.0
        sample_df.loc[1, "amount"] = 200_000.0
        cleaned = clean(sample_df)
        assert (cleaned["amount"] >= 0.01).all()
        assert (cleaned["amount"] <= 100_000).all()

    def test_normalises_merchant_category(self, sample_df: pd.DataFrame) -> None:
        sample_df.loc[0, "merchant_category"] = "  GROCERY  "
        cleaned = clean(sample_df)
        assert cleaned.loc[0, "merchant_category"] == "grocery"

    def test_drops_null_transaction_id(self, sample_df: pd.DataFrame) -> None:
        sample_df.loc[0, "transaction_id"] = None
        cleaned = clean(sample_df)
        assert len(cleaned) == len(sample_df) - 1


class TestAddDerivedColumns:
    def test_adds_expected_columns(self, sample_df: pd.DataFrame) -> None:
        import numpy as np
        sample_df["log_amount"] = np.log1p(sample_df["amount"])
        df = add_derived_columns(sample_df)
        for col in ["is_weekend", "is_night", "is_foreign"]:
            assert col in df.columns

    def test_is_weekend_correct(self, sample_df: pd.DataFrame) -> None:
        import numpy as np
        sample_df["log_amount"] = np.log1p(sample_df["amount"])
        sample_df.loc[0, "day_of_week"] = 6  # Sunday
        sample_df.loc[1, "day_of_week"] = 0  # Monday
        df = add_derived_columns(sample_df)
        assert df.loc[0, "is_weekend"] == 1
        assert df.loc[1, "is_weekend"] == 0

    def test_is_night_correct(self, sample_df: pd.DataFrame) -> None:
        import numpy as np
        sample_df["log_amount"] = np.log1p(sample_df["amount"])
        sample_df.loc[0, "hour_of_day"] = 3
        sample_df.loc[1, "hour_of_day"] = 14
        df = add_derived_columns(sample_df)
        assert df.loc[0, "is_night"] == 1
        assert df.loc[1, "is_night"] == 0

    def test_is_foreign_correct(self, sample_df: pd.DataFrame) -> None:
        import numpy as np
        sample_df["log_amount"] = np.log1p(sample_df["amount"])
        df = add_derived_columns(sample_df)
        assert df.loc[1, "is_foreign"] == 1   # CA
        assert df.loc[0, "is_foreign"] == 0   # US
