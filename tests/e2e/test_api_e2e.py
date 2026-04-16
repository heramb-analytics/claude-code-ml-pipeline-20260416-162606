"""Playwright end-to-end tests for the transaction anomaly detection API.

Starts a live uvicorn server, exercises all endpoints through a Playwright browser page,
and saves screenshots to reports/screenshots/.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

SCREENSHOTS_DIR = Path("reports/screenshots")
BASE_URL = "http://127.0.0.1:8765"

VALID_TXN = {
    "amount": 120.0,
    "num_prev_txn_1h": 1,
    "distance_from_home_km": 5.0,
    "hour_of_day": 14,
    "day_of_week": 2,
    "card_present": True,
    "is_foreign": 0,
    "merchant_risk_score": 1,
    "customer_txn_count": 10,
    "customer_avg_amount": 100.0,
    "customer_amount_std": 25.0,
    "customer_max_amount": 300.0,
}

ANOMALY_TXN = {
    "amount": 9800.0,
    "num_prev_txn_1h": 14,
    "distance_from_home_km": 4200.0,
    "hour_of_day": 3,
    "day_of_week": 6,
    "card_present": False,
    "is_foreign": 1,
    "merchant_risk_score": 3,
    "customer_txn_count": 2,
    "customer_avg_amount": 45.0,
    "customer_amount_std": 5.0,
    "customer_max_amount": 55.0,
}


@pytest.fixture(scope="session", autouse=True)
def api_server():
    """Spin up a uvicorn server for the duration of the test session."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent / "src")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api:app", "--host", "127.0.0.1", "--port", "8765"],
        cwd=str(Path(__file__).parent.parent.parent),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for server to be ready
    for _ in range(30):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=1)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.5)
    else:
        proc.kill()
        raise RuntimeError("API server did not start in time.")
    yield proc
    proc.kill()


@pytest.fixture()
def browser_page(playwright):
    """Create a Playwright page attached to the running Chromium browser."""
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    yield page
    page.close()
    browser.close()


class TestHealthE2E:
    def test_health_endpoint_via_requests(self) -> None:
        resp = requests.get(f"{BASE_URL}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "xgboost" in data["models_loaded"]

    def test_health_page_screenshot(self, browser_page) -> None:
        browser_page.goto(f"{BASE_URL}/health")
        out = SCREENSHOTS_DIR / "01_health_endpoint.png"
        browser_page.screenshot(path=str(out))
        assert out.exists()

    def test_docs_page_loads(self, browser_page) -> None:
        browser_page.goto(f"{BASE_URL}/docs")
        browser_page.wait_for_load_state("networkidle")
        out = SCREENSHOTS_DIR / "02_swagger_docs.png"
        browser_page.screenshot(path=str(out), full_page=True)
        assert out.exists()
        assert "Transaction Anomaly" in browser_page.title() or browser_page.locator("h2").count() >= 1


class TestPredictE2E:
    def test_normal_transaction_prediction(self) -> None:
        resp = requests.post(f"{BASE_URL}/predict", json=VALID_TXN)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_anomaly"] == 0
        assert 0.0 <= data["anomaly_probability"] <= 1.0
        assert "request_id" in data
        assert "timestamp" in data

    def test_anomaly_transaction_detected(self) -> None:
        resp = requests.post(f"{BASE_URL}/predict", json=ANOMALY_TXN)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_anomaly"] == 1

    def test_predict_screenshot(self, browser_page) -> None:
        browser_page.goto(f"{BASE_URL}/docs#/default/predict_predict_post")
        browser_page.wait_for_load_state("networkidle")
        out = SCREENSHOTS_DIR / "03_predict_endpoint.png"
        browser_page.screenshot(path=str(out), full_page=True)
        assert out.exists()

    def test_batch_prediction(self) -> None:
        resp = requests.post(f"{BASE_URL}/predict/batch", json=[VALID_TXN, ANOMALY_TXN])
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["anomaly_count"] == 1
        assert len(data["predictions"]) == 2


class TestMetricsE2E:
    def test_metrics_endpoint(self) -> None:
        resp = requests.get(f"{BASE_URL}/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "metrics" in data
        assert "xgboost" in data["metrics"]["models"]

    def test_metrics_screenshot(self, browser_page) -> None:
        browser_page.goto(f"{BASE_URL}/metrics")
        out = SCREENSHOTS_DIR / "04_metrics_endpoint.png"
        browser_page.screenshot(path=str(out))
        assert out.exists()

    def test_feature_schema_endpoint(self) -> None:
        resp = requests.get(f"{BASE_URL}/feature-schema")
        assert resp.status_code == 200
        data = resp.json()
        assert "features" in data
        assert len(data["features"]) > 0
