"""Unit tests for src/api.py using FastAPI TestClient."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from api import app

client = TestClient(app)

VALID_TXN = {
    "amount": 150.0,
    "num_prev_txn_1h": 1,
    "distance_from_home_km": 5.0,
    "hour_of_day": 14,
    "day_of_week": 2,
    "card_present": True,
    "is_foreign": 0,
    "merchant_risk_score": 1,
    "customer_txn_count": 10,
    "customer_avg_amount": 120.0,
    "customer_amount_std": 30.0,
    "customer_max_amount": 400.0,
}

ANOMALY_TXN = {
    "amount": 9999.0,
    "num_prev_txn_1h": 15,
    "distance_from_home_km": 4500.0,
    "hour_of_day": 3,
    "day_of_week": 6,
    "card_present": False,
    "is_foreign": 1,
    "merchant_risk_score": 3,
    "customer_txn_count": 2,
    "customer_avg_amount": 40.0,
    "customer_amount_std": 5.0,
    "customer_max_amount": 60.0,
}


class TestHealthEndpoint:
    def test_returns_200(self) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_has_required_fields(self) -> None:
        resp = client.get("/health")
        data = resp.json()
        assert "request_id" in data
        assert "timestamp" in data
        assert data["status"] == "ok"
        assert "models_loaded" in data

    def test_models_loaded(self) -> None:
        resp = client.get("/health")
        loaded = resp.json()["models_loaded"]
        assert "xgboost" in loaded
        assert "isolation_forest" in loaded


class TestMetricsEndpoint:
    def test_returns_200(self) -> None:
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_has_request_id_and_timestamp(self) -> None:
        resp = client.get("/metrics")
        data = resp.json()
        assert "request_id" in data
        assert "timestamp" in data
        assert "metrics" in data


class TestPredictEndpoint:
    def test_valid_transaction_returns_200(self) -> None:
        resp = client.post("/predict", json=VALID_TXN)
        assert resp.status_code == 200

    def test_response_has_required_fields(self) -> None:
        resp = client.post("/predict", json=VALID_TXN)
        data = resp.json()
        assert "request_id" in data
        assert "timestamp" in data
        assert "is_anomaly" in data
        assert "anomaly_probability" in data
        assert "model" in data

    def test_is_anomaly_is_binary(self) -> None:
        resp = client.post("/predict", json=VALID_TXN)
        assert resp.json()["is_anomaly"] in (0, 1)

    def test_probability_in_range(self) -> None:
        resp = client.post("/predict", json=VALID_TXN)
        prob = resp.json()["anomaly_probability"]
        assert 0.0 <= prob <= 1.0

    def test_invalid_amount_rejected(self) -> None:
        bad = {**VALID_TXN, "amount": -10.0}
        resp = client.post("/predict", json=bad)
        assert resp.status_code == 422

    def test_anomaly_transaction_detected(self) -> None:
        resp = client.post("/predict", json=ANOMALY_TXN)
        data = resp.json()
        assert data["is_anomaly"] == 1


class TestBatchPredictEndpoint:
    def test_batch_returns_200(self) -> None:
        resp = client.post("/predict/batch", json=[VALID_TXN, ANOMALY_TXN])
        assert resp.status_code == 200

    def test_batch_response_structure(self) -> None:
        resp = client.post("/predict/batch", json=[VALID_TXN, ANOMALY_TXN])
        data = resp.json()
        assert data["total"] == 2
        assert "predictions" in data
        assert len(data["predictions"]) == 2
        assert "request_id" in data
        assert "timestamp" in data

    def test_empty_batch_returns_400(self) -> None:
        resp = client.post("/predict/batch", json=[])
        assert resp.status_code == 400
