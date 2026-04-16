# Transaction Anomaly Detection Pipeline

An end-to-end ML pipeline that ingests raw transaction data, engineers features, trains Isolation Forest + XGBoost anomaly detectors, and exposes a FastAPI inference service.

[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blue?logo=anthropic)](https://claude.ai/code)

---

## Architecture

```
data/raw/transactions.csv          (READ ONLY — 10K rows, 5% anomaly rate)
          │
          ▼
  src/ingest.py                    Stage 2: clean → data/processed/clean.parquet
          │
     ┌────┴────────────────────┐
     ▼                         ▼                         ▼
src/eda.py                 src/features.py           src/validate.py
5 EDA charts               21 new features            12 data quality checks
reports/figures/           features.parquet           logs/validation_report.json
          │                    │
          └────────┬───────────┘
                   ▼
            src/train.py                             Stage 3: model training
    ┌─────────────┴──────────────────┐
    ▼                                ▼
Isolation Forest               XGBoost Classifier
(unsupervised)                 (supervised, scale_pos_weight)
F1=0.64  AUC=0.986             F1=1.0   AUC=1.0
models/isolation_forest.pkl    models/xgboost.pkl
          │                         │
          └────────────┬────────────┘
                       ▼
                  src/api.py                         Stage 4: FastAPI serving
         ┌─────────────┼──────────────────┐
    GET /health   POST /predict    GET /metrics
    GET /feature-schema   POST /predict/batch
```

---

## Quick Start

```bash
# 1. Clone and enter directory
git clone <repo-url>
cd claude-pipeline-20260416-162405

# 2. Install dependencies
pip install pandas numpy scikit-learn xgboost fastapi uvicorn pytest \
    playwright pytest-playwright matplotlib seaborn scipy requests httpx pyarrow
python3 -m playwright install chromium

# 3. Generate synthetic data
python3 scripts/generate_data.py

# 4. Run the full pipeline
python3 src/ingest.py
python3 src/eda.py
python3 src/features.py
python3 src/validate.py
python3 src/train.py

# 5. Start the API server
uvicorn src.api:app --host 0.0.0.0 --port 8000

# 6. Run all tests
python3 -m pytest tests/unit/ tests/e2e/ -v
```

---

## API Endpoints

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| `GET` | `/health` | Liveness probe — returns status + models loaded | `{"status":"ok","models_loaded":[...]}` |
| `GET` | `/metrics` | Model evaluation metrics (F1, AUC, precision, recall) | `{"metrics":{"xgboost":{...},"isolation_forest":{...}}}` |
| `GET` | `/feature-schema` | Engineered feature list with dtypes and descriptions | `{"features":[...]}` |
| `POST` | `/predict` | Single transaction anomaly prediction | `{"is_anomaly":0,"anomaly_probability":0.012}` |
| `POST` | `/predict/batch` | Batch predictions for multiple transactions | `{"total":100,"anomaly_count":5,"predictions":[...]}` |

Every response includes `request_id` (UUID4) and `timestamp` (ISO-8601 UTC).

### Example: Predict a single transaction

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 9999.0,
    "num_prev_txn_1h": 14,
    "distance_from_home_km": 4200.0,
    "hour_of_day": 3,
    "day_of_week": 6,
    "card_present": false,
    "is_foreign": 1,
    "merchant_risk_score": 3,
    "customer_txn_count": 2,
    "customer_avg_amount": 45.0,
    "customer_amount_std": 5.0,
    "customer_max_amount": 55.0
  }'
```

---

## Model Metrics

| Model | F1 Score | ROC-AUC | Precision | Recall | Avg Precision |
|-------|----------|---------|-----------|--------|----------------|
| **XGBoost** | **1.000** | **1.000** | **1.000** | **1.000** | **1.000** |
| Isolation Forest | 0.636 | 0.986 | 0.558 | 0.740 | 0.847 |

- Dataset: 10,000 transactions, 5% anomaly rate
- Train/test split: 80/20, stratified
- XGBoost uses `scale_pos_weight` to handle class imbalance (19:1)

---

## Project Structure

```
.
├── data/
│   ├── raw/transactions.csv          ← READ ONLY source data
│   └── processed/
│       ├── clean.parquet             ← Cleaned 10K rows
│       ├── features.parquet          ← 21 engineered features
│       └── feature_schema.json       ← Feature metadata
├── src/
│   ├── ingest.py                     ← Stage 2: ingestion & cleaning
│   ├── eda.py                        ← Stage 2A: 5 EDA charts
│   ├── features.py                   ← Stage 2A: feature engineering
│   ├── validate.py                   ← Stage 2A: 12 data quality checks
│   ├── train.py                      ← Stage 3: model training
│   └── api.py                        ← Stage 4: FastAPI service
├── models/
│   ├── isolation_forest.pkl + _metrics.json
│   ├── xgboost.pkl + _metrics.json
│   └── training_summary.json
├── tests/
│   ├── unit/                         ← 39 pytest tests
│   └── e2e/                          ← 10 Playwright tests
├── reports/
│   ├── figures/                      ← 5 EDA charts (PNG)
│   └── screenshots/                  ← 4 Playwright screenshots
├── logs/
│   ├── ingest.jsonl
│   ├── eda.jsonl
│   ├── features.jsonl
│   ├── validation_report.json
│   └── train.jsonl
├── scripts/
│   └── generate_data.py              ← Synthetic data generator
└── docs/
    ├── jira_tickets.md
    └── confluence_page.md
```

---

## JIRA

- **Project:** [ADP — Anomaly Detection Pipeline](https://herambithape007.atlassian.net/jira/software/projects/ADP)
- **Epic:** [ADP-8 — Transaction Anomaly Detection ML Pipeline](https://herambithape007.atlassian.net/browse/ADP-8)
- **Sprint:** Sprint 1 - Anomaly Pipeline (Apr 17 – Apr 30, 2026)
- **Stories:** ADP-9, ADP-10, ADP-11, ADP-12, ADP-13, ADP-14

## Confluence

- **Space:** CR
- **Page:** Transaction Anomaly Detection Pipeline — Technical Design & Results
- See `docs/confluence_page.md` for the full page content

---

[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blue?logo=anthropic)](https://claude.ai/code)
