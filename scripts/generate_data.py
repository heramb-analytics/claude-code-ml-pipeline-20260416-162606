"""Generate synthetic transaction data for anomaly detection.

Produces data/raw/transactions.csv with realistic normal and anomalous transactions.
"""

from pathlib import Path
import numpy as np
import pandas as pd


def generate_transactions(
    n_normal: int = 9500,
    n_anomalies: int = 500,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic transaction dataset with labeled anomalies.

    Args:
        n_normal: Number of normal transactions to generate.
        n_anomalies: Number of anomalous transactions to generate.
        seed: Random seed for reproducibility.

    Returns:
        DataFrame with transaction records.
    """
    rng = np.random.default_rng(seed)

    # --- normal transactions ---
    n = n_normal
    timestamps_normal = pd.date_range("2024-01-01", periods=n, freq="5min")
    normal = pd.DataFrame(
        {
            "transaction_id": [f"TXN{i:07d}" for i in range(n)],
            "timestamp": timestamps_normal,
            "amount": rng.lognormal(mean=3.5, sigma=1.2, size=n).round(2),
            "merchant_category": rng.choice(
                ["grocery", "gas", "restaurant", "retail", "online", "travel"],
                size=n,
                p=[0.25, 0.15, 0.20, 0.20, 0.15, 0.05],
            ),
            "card_present": rng.choice([True, False], size=n, p=[0.75, 0.25]),
            "country_code": rng.choice(
                ["US", "US", "US", "CA", "GB", "MX"],
                size=n,
                p=[0.70, 0.10, 0.05, 0.07, 0.05, 0.03],
            ),
            "hour_of_day": (timestamps_normal.hour + rng.integers(0, 3, size=n)) % 24,
            "day_of_week": timestamps_normal.dayofweek,
            "customer_id": rng.integers(1000, 5000, size=n),
            "merchant_id": rng.integers(100, 2000, size=n),
            "num_prev_txn_1h": rng.poisson(1.5, size=n),
            "distance_from_home_km": rng.exponential(scale=10, size=n).round(1),
            "is_anomaly": 0,
        }
    )

    # --- anomalous transactions (5 attack patterns) ---
    n_a = n_anomalies
    timestamps_anomaly = pd.date_range("2024-01-01 02:00:00", periods=n_a, freq="30min")
    anomaly_patterns = rng.choice(5, size=n_a)

    amounts = np.where(
        anomaly_patterns == 0, rng.uniform(5000, 25000, n_a),        # large fraud
        np.where(
            anomaly_patterns == 1, rng.uniform(0.01, 0.99, n_a),      # micro-testing
            np.where(
                anomaly_patterns == 2, rng.uniform(500, 1500, n_a),    # card-not-present spike
                np.where(
                    anomaly_patterns == 3, rng.uniform(200, 800, n_a), # rapid sequential
                    rng.uniform(1000, 4000, n_a),                       # foreign unusual
                ),
            ),
        ),
    ).round(2)

    anomalies = pd.DataFrame(
        {
            "transaction_id": [f"TXN{n + i:07d}" for i in range(n_a)],
            "timestamp": timestamps_anomaly,
            "amount": amounts,
            "merchant_category": rng.choice(
                ["online", "travel", "retail", "grocery", "gas", "restaurant"],
                size=n_a,
                p=[0.40, 0.25, 0.15, 0.08, 0.07, 0.05],
            ),
            "card_present": np.where(anomaly_patterns <= 1, False, rng.choice([True, False], size=n_a)),
            "country_code": rng.choice(
                ["NG", "RO", "BR", "US", "RU", "CN"],
                size=n_a,
                p=[0.20, 0.20, 0.15, 0.15, 0.15, 0.15],
            ),
            "hour_of_day": rng.choice([2, 3, 4, 23, 0, 1], size=n_a),  # odd hours
            "day_of_week": rng.integers(0, 7, size=n_a),
            "customer_id": rng.integers(1000, 5000, size=n_a),
            "merchant_id": rng.integers(100, 2000, size=n_a),
            "num_prev_txn_1h": np.where(anomaly_patterns == 3, rng.integers(8, 20, n_a), rng.poisson(0.5, n_a)),
            "distance_from_home_km": rng.uniform(200, 5000, n_a).round(1),
            "is_anomaly": 1,
        }
    )

    df = pd.concat([normal, anomalies], ignore_index=True)
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    return df


def main() -> None:
    """Entry point: generate and save transactions to data/raw/transactions.csv."""
    out_path = Path(__file__).parent.parent / "data" / "raw" / "transactions.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = generate_transactions()
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df):,} rows → {out_path}")
    print(f"Anomaly rate: {df['is_anomaly'].mean():.2%}")
    print(df.dtypes)


if __name__ == "__main__":
    main()
