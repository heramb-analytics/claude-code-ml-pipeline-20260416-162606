# JIRA Tickets — Transaction Anomaly Detection Pipeline

**Project:** ADP (Anomaly Detection Pipeline)
**Epic:** ADP-8
**Sprint:** Sprint 1 - Anomaly Pipeline (Apr 17 – Apr 30, 2026)

---

## Epic

### ADP-8 — Transaction Anomaly Detection ML Pipeline — End-to-End Delivery
- **Type:** Epic
- **Priority:** Medium
- **Assignee:** heramb
- **URL:** https://herambithape007.atlassian.net/browse/ADP-8

Build a production-quality ML pipeline that ingests raw transaction data, engineers features, trains Isolation Forest + XGBoost anomaly detectors, exposes a FastAPI inference service, and delivers EDA charts, validation reports, unit + e2e tests.

---

## Stories

### ADP-9 — Data generation: synthetic 10K transaction dataset with 5% anomaly rate
- **Type:** Story | **Priority:** High
- **URL:** https://herambithape007.atlassian.net/browse/ADP-9
- Script: `scripts/generate_data.py` → `data/raw/transactions.csv`
- 10,000 rows, 5 fraud attack patterns, seed=42

### ADP-10 — Data ingestion & preprocessing pipeline (src/ingest.py)
- **Type:** Story | **Priority:** High
- **URL:** https://herambithape007.atlassian.net/browse/ADP-10
- `src/ingest.py` → `data/processed/clean.parquet`
- Schema validation, dedup, amount clip, derived columns, JSONL logging

### ADP-11 — Feature engineering: 21 new features for anomaly detection (src/features.py)
- **Type:** Story | **Priority:** High
- **URL:** https://herambithape007.atlassian.net/browse/ADP-11
- `src/features.py` → `features.parquet` + `feature_schema.json`
- Time cyclical, statistical, velocity, categorical features

### ADP-12 — Model training: Isolation Forest + XGBoost anomaly detectors (src/train.py)
- **Type:** Story | **Priority:** High
- **URL:** https://herambithape007.atlassian.net/browse/ADP-12
- Results: XGBoost AUC=1.0, IF AUC=0.986

### ADP-13 — FastAPI inference service with /predict, /health, /metrics (src/api.py)
- **Type:** Story | **Priority:** High
- **URL:** https://herambithape007.atlassian.net/browse/ADP-13
- 5 endpoints, request_id + timestamp on every response

### ADP-14 — Test suite: 39 pytest unit tests + 10 Playwright e2e tests
- **Type:** Story | **Priority:** High
- **URL:** https://herambithape007.atlassian.net/browse/ADP-14
- 39/39 unit tests pass, 10/10 e2e tests pass
