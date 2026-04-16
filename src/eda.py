"""EDA and visualisation for the transaction anomaly detection pipeline.

Reads data/processed/clean.parquet.
Generates 5 charts and saves them to reports/figures/.
Logs to logs/eda.jsonl.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns


CLEAN_PATH = Path("data/processed/clean.parquet")
FIGURES_DIR = Path("reports/figures")
LOG_PATH = Path("logs/eda.jsonl")

sns.set_theme(style="whitegrid", palette="muted")


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


def plot_target_distribution(df: pd.DataFrame) -> Path:
    """Bar chart of normal vs anomalous transaction counts.

    Args:
        df: Cleaned transaction DataFrame.

    Returns:
        Path to saved figure.
    """
    out = FIGURES_DIR / "01_target_distribution.png"
    counts = df["is_anomaly"].value_counts().sort_index()
    labels = ["Normal", "Anomaly"]
    colors = ["#4C9BE8", "#E84C4C"]
    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(labels, counts.values, color=colors, edgecolor="white", linewidth=1.5)
    for bar, val in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 50,
                f"{val:,}\n({val/len(df):.1%})", ha="center", va="bottom", fontsize=11)
    ax.set_title("Transaction Class Distribution", fontsize=14, fontweight="bold")
    ax.set_ylabel("Count")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{int(x):,}"))
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    _log("plot_saved", {"figure": out.name})
    return out


def plot_feature_correlations(df: pd.DataFrame) -> Path:
    """Heatmap of numeric feature correlations.

    Args:
        df: Cleaned transaction DataFrame.

    Returns:
        Path to saved figure.
    """
    out = FIGURES_DIR / "02_feature_correlations.png"
    num_cols = ["amount", "log_amount", "num_prev_txn_1h", "distance_from_home_km",
                "hour_of_day", "day_of_week", "is_weekend", "is_night",
                "is_foreign", "is_anomaly"]
    corr = df[num_cols].corr()
    fig, ax = plt.subplots(figsize=(10, 8))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r",
                center=0, vmin=-1, vmax=1, ax=ax, linewidths=0.5)
    ax.set_title("Feature Correlation Matrix", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    _log("plot_saved", {"figure": out.name})
    return out


def plot_missing_values(df: pd.DataFrame) -> Path:
    """Horizontal bar chart of missing value percentages.

    Args:
        df: Cleaned transaction DataFrame.

    Returns:
        Path to saved figure.
    """
    out = FIGURES_DIR / "03_missing_values.png"
    missing = (df.isnull().sum() / len(df) * 100).sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = ["#E84C4C" if v > 0 else "#4C9BE8" for v in missing.values]
    ax.barh(missing.index, missing.values, color=colors)
    ax.set_xlabel("Missing (%)")
    ax.set_title("Missing Values per Column", fontsize=14, fontweight="bold")
    ax.axvline(x=0, color="black", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    _log("plot_saved", {"figure": out.name})
    return out


def plot_amount_distribution(df: pd.DataFrame) -> Path:
    """Side-by-side log-amount distributions for normal vs anomaly.

    Args:
        df: Cleaned transaction DataFrame.

    Returns:
        Path to saved figure.
    """
    out = FIGURES_DIR / "04_amount_distribution.png"
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, label, color, title in zip(
        axes,
        [0, 1],
        ["#4C9BE8", "#E84C4C"],
        ["Normal Transactions", "Anomalous Transactions"],
    ):
        subset = df[df["is_anomaly"] == label]["log_amount"]
        sns.histplot(subset, bins=40, color=color, ax=ax, kde=True, edgecolor="white")
        ax.set_title(f"{title}\nlog(amount+1)", fontsize=12, fontweight="bold")
        ax.set_xlabel("log(amount + 1)")
        ax.set_ylabel("Count")
    fig.suptitle("Amount Distribution: Normal vs Anomaly", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    _log("plot_saved", {"figure": out.name})
    return out


def plot_time_series_trend(df: pd.DataFrame) -> Path:
    """Daily transaction volume trend with anomaly overlay.

    Args:
        df: Cleaned transaction DataFrame.

    Returns:
        Path to saved figure.
    """
    out = FIGURES_DIR / "05_time_series_trend.png"
    df = df.copy()
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date
    daily = df.groupby(["date", "is_anomaly"]).size().unstack(fill_value=0).reset_index()
    daily.columns.name = None
    daily.rename(columns={0: "normal", 1: "anomaly"}, inplace=True)
    fig, ax1 = plt.subplots(figsize=(14, 5))
    ax1.fill_between(daily["date"], daily["normal"], alpha=0.3, color="#4C9BE8", label="Normal")
    ax1.plot(daily["date"], daily["normal"], color="#4C9BE8", linewidth=1.5)
    ax2 = ax1.twinx()
    ax2.bar(daily["date"], daily.get("anomaly", 0), alpha=0.6, color="#E84C4C", label="Anomaly", width=0.8)
    ax1.set_title("Daily Transaction Volume with Anomaly Overlay", fontsize=14, fontweight="bold")
    ax1.set_ylabel("Normal Transactions", color="#4C9BE8")
    ax2.set_ylabel("Anomalous Transactions", color="#E84C4C")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    _log("plot_saved", {"figure": out.name})
    return out


def run() -> None:
    """Execute full EDA: load data, generate 5 charts, log results."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    _log("eda_start", {})
    df = pd.read_parquet(CLEAN_PATH)
    _log("data_loaded", {"rows": len(df), "cols": list(df.columns)})

    figures = [
        plot_target_distribution(df),
        plot_feature_correlations(df),
        plot_missing_values(df),
        plot_amount_distribution(df),
        plot_time_series_trend(df),
    ]
    _log("eda_end", {"figures_saved": [str(f) for f in figures]})
    print(f"EDA complete: {len(figures)} charts saved to {FIGURES_DIR}")


if __name__ == "__main__":
    run()
