"""Build the pipeline PowerPoint presentation per PRESENTATION PROTOCOL.

- NAVY (#1E3A8A) background for cover and section slides
- White background with colored accent borders for content slides
- Title font: Arial Bold 36pt; Body font: Arial 20pt
- Insert actual chart images from reports/figures/
- Insert actual screenshots from reports/screenshots/
- Slide number footer on every slide
- Saves to: reports/pipeline_presentation.pptx
"""

import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt, Emu

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
NAVY = RGBColor(0x1E, 0x3A, 0x8A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ACCENT = RGBColor(0x22, 0xD3, 0xEE)   # cyan accent
DARK_GREY = RGBColor(0x1F, 0x29, 0x37)
LIGHT_GREY = RGBColor(0xF1, 0xF5, 0xF9)
GREEN = RGBColor(0x16, 0xA3, 0x4A)
RED = RGBColor(0xDC, 0x26, 0x26)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

FIGURES = Path("reports/figures")
SCREENSHOTS = Path("reports/screenshots")
MODELS_DIR = Path("models")
OUT_PATH = Path("reports/pipeline_presentation.pptx")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_metrics() -> dict:
    """Load model metrics from training_summary.json."""
    path = MODELS_DIR / "training_summary.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _add_solid_bg(slide, prs, color: RGBColor) -> None:
    """Fill slide background with a solid color."""
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_text_box(
    slide,
    text: str,
    left: float,
    top: float,
    width: float,
    height: float,
    font_size: int = 20,
    bold: bool = False,
    color: RGBColor = WHITE,
    align=PP_ALIGN.LEFT,
    word_wrap: bool = True,
) -> None:
    """Add a styled text box to a slide.

    Args:
        slide: Slide object.
        text: Text content.
        left, top, width, height: Position/size in inches.
        font_size: Font size in points.
        bold: Whether to bold the text.
        color: Font RGB color.
        align: Paragraph alignment.
        word_wrap: Whether to enable word wrap.
    """
    txb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    txb.word_wrap = word_wrap
    tf = txb.text_frame
    tf.word_wrap = word_wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = "Arial"
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color


def _add_title_bar(slide, title: str, bg_color: RGBColor = NAVY, text_color: RGBColor = WHITE) -> None:
    """Add a full-width title bar at the top of a slide."""
    bar = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        Inches(0), Inches(0), SLIDE_W, Inches(1.1),
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = bg_color
    bar.line.fill.background()
    tf = bar.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = f"  {title}"
    run.font.name = "Arial"
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = text_color


def _add_slide_number(slide, number: int, total: int, dark: bool = False) -> None:
    """Add slide number footer (bottom-right)."""
    color = DARK_GREY if dark else WHITE
    _add_text_box(
        slide, f"{number} / {total}",
        left=11.8, top=7.0, width=1.4, height=0.4,
        font_size=11, color=color, align=PP_ALIGN.RIGHT,
    )


def _add_accent_border(slide) -> None:
    """Add a thin cyan accent line below the title bar on content slides."""
    line = slide.shapes.add_shape(1, Inches(0), Inches(1.1), SLIDE_W, Inches(0.06))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT
    line.line.fill.background()


def _add_image_safe(slide, path: Path, left: float, top: float, width: float) -> bool:
    """Add an image to the slide if the file exists.

    Args:
        slide: Slide object.
        path: Image path.
        left, top, width: Position/size in inches.

    Returns:
        True if image was added, False otherwise.
    """
    if path.exists():
        slide.shapes.add_picture(str(path), Inches(left), Inches(top), width=Inches(width))
        return True
    return False


# ---------------------------------------------------------------------------
# Slide builders
# ---------------------------------------------------------------------------

def slide_cover(prs: Presentation, slide_num: int, total: int) -> None:
    """Slide 1: Cover — NAVY background."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    _add_solid_bg(slide, prs, NAVY)

    # Accent bar
    bar = slide.shapes.add_shape(1, Inches(0), Inches(3.3), Inches(0.25), Inches(2.5))
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT
    bar.line.fill.background()

    _add_text_box(slide, "Transaction Anomaly Detection", 0.5, 1.4, 12.0, 1.0, font_size=36, bold=True)
    _add_text_box(slide, "End-to-End ML Pipeline", 0.5, 2.45, 12.0, 0.7, font_size=28)
    _add_text_box(slide, "Isolation Forest + XGBoost + FastAPI + Playwright", 0.5, 3.35, 10.0, 0.5, font_size=18, color=ACCENT)
    _add_text_box(slide, "April 16, 2026", 0.5, 5.2, 5.0, 0.4, font_size=15, color=RGBColor(0x94, 0xA3, 0xB8))
    _add_text_box(slide, "Built with Claude Code", 0.5, 5.75, 5.0, 0.4, font_size=14, color=RGBColor(0x94, 0xA3, 0xB8))
    _add_slide_number(slide, slide_num, total)


def slide_agenda(prs: Presentation, slide_num: int, total: int) -> None:
    """Slide 2: Agenda — NAVY section slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_solid_bg(slide, prs, NAVY)
    _add_text_box(slide, "Agenda", 0.6, 0.3, 12.0, 0.9, font_size=36, bold=True)

    items = [
        "01  Problem Statement & Dataset",
        "02  Architecture Overview",
        "03  Data Quality — 12 Validation Checks",
        "04  Feature Engineering — 21 New Features",
        "05  Model Results — Isolation Forest & XGBoost",
        "06  FastAPI Inference Service",
        "07  Test Coverage — 49 Tests",
        "08  EDA Insights",
        "09  JIRA & Confluence",
        "10  Summary & Next Steps",
    ]
    y = 1.4
    for item in items:
        _add_text_box(slide, item, 1.5, y, 10.5, 0.45, font_size=17, color=WHITE)
        y += 0.52
    _add_slide_number(slide, slide_num, total)


def slide_problem(prs: Presentation, slide_num: int, total: int) -> None:
    """Slide 3: Problem Statement & Dataset."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_solid_bg(slide, prs, WHITE)
    _add_title_bar(slide, "Problem Statement & Dataset")
    _add_accent_border(slide)

    left_items = [
        ("Problem", "Detect fraudulent transactions in real-time from tabular features without manual rules."),
        ("Dataset", "10,000 synthetic transactions (9,500 normal + 500 anomalous) — 5% anomaly rate, seed=42."),
        ("Fraud Patterns", "5 attack types: large-amount, micro card-testing, card-not-present,\nrapid sequential, foreign unusual."),
    ]
    y = 1.4
    for label, body in left_items:
        _add_text_box(slide, label, 0.4, y, 3.5, 0.35, font_size=14, bold=True, color=NAVY)
        _add_text_box(slide, body, 0.4, y + 0.35, 5.6, 0.8, font_size=15, color=DARK_GREY)
        y += 1.35

    # Target distribution chart
    _add_image_safe(slide, FIGURES / "01_target_distribution.png", 6.5, 1.3, 6.2)
    _add_slide_number(slide, slide_num, total, dark=True)


def slide_architecture(prs: Presentation, slide_num: int, total: int) -> None:
    """Slide 4: Architecture Overview — NAVY section."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_solid_bg(slide, prs, NAVY)
    _add_text_box(slide, "Architecture Overview", 0.6, 0.3, 12.0, 0.9, font_size=36, bold=True)

    stages = [
        ("Stage 1", "scripts/generate_data.py", "10K synthetic transactions"),
        ("Stage 2", "src/ingest.py", "clean.parquet — schema validation, cleaning, derived cols"),
        ("Stage 2A", "eda.py / features.py / validate.py", "5 charts, 21 features, 12 data quality checks"),
        ("Stage 3", "src/train.py", "Isolation Forest + XGBoost — pkl + metrics.json"),
        ("Stage 4", "src/api.py", "FastAPI: /predict /predict/batch /health /metrics"),
        ("Stage 5/6", "tests/unit + tests/e2e", "39 pytest + 10 Playwright tests"),
    ]
    y = 1.45
    for stage, script, desc in stages:
        # Stage pill
        pill = slide.shapes.add_shape(1, Inches(0.4), Inches(y), Inches(1.6), Inches(0.38))
        pill.fill.solid()
        pill.fill.fore_color.rgb = ACCENT
        pill.line.fill.background()
        tf = pill.text_frame
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = stage
        r.font.name = "Arial"
        r.font.size = Pt(13)
        r.font.bold = True
        r.font.color.rgb = DARK_GREY

        _add_text_box(slide, script, 2.2, y, 3.8, 0.38, font_size=13, bold=True, color=ACCENT)
        _add_text_box(slide, desc, 6.2, y, 6.8, 0.38, font_size=13, color=WHITE)
        y += 0.85
    _add_slide_number(slide, slide_num, total)


def slide_validation(prs: Presentation, slide_num: int, total: int) -> None:
    """Slide 5: Data Quality — 12 Validation Checks."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_solid_bg(slide, prs, WHITE)
    _add_title_bar(slide, "Data Quality — 12 Validation Checks (12/12 Pass)")
    _add_accent_border(slide)

    checks = [
        ("Row count ≥ 1,000", "10,000 ✅"),
        ("Required columns present", "13/13 ✅"),
        ("No nulls in critical cols", "0 nulls ✅"),
        ("Amount in (0, 100K]", "All rows ✅"),
        ("Unique transaction IDs", "0 duplicates ✅"),
        ("Timestamps non-null", "All rows ✅"),
        ("Anomaly rate 1%–15%", "5.0% ✅"),
        ("hour_of_day in [0, 23]", "All rows ✅"),
        ("day_of_week in [0, 6]", "All rows ✅"),
        ("num_prev_txn_1h ≥ 0", "All rows ✅"),
        ("merchant_category known", "All rows ✅"),
        ("Normal median $5–$1,000", "$32.56 ✅"),
    ]

    col_w = 6.0
    for i, (check, result) in enumerate(checks):
        col = i % 2
        row = i // 2
        x = 0.3 + col * col_w
        y = 1.35 + row * 1.0

        box = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(5.7), Inches(0.82))
        box.fill.solid()
        box.fill.fore_color.rgb = LIGHT_GREY
        box.line.color.rgb = RGBColor(0xD1, 0xD5, 0xDB)
        box.line.width = Pt(0.5)

        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        r = p.add_run()
        r.text = f"  {check}"
        r.font.name = "Arial"
        r.font.size = Pt(13)
        r.font.color.rgb = DARK_GREY

        _add_text_box(slide, result, x + 3.6, y + 0.05, 2.0, 0.4, font_size=13, bold=True, color=GREEN)

    _add_slide_number(slide, slide_num, total, dark=True)


def slide_features(prs: Presentation, slide_num: int, total: int) -> None:
    """Slide 6: Feature Engineering — 21 New Features."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_solid_bg(slide, prs, WHITE)
    _add_title_bar(slide, "Feature Engineering — 21 New Features")
    _add_accent_border(slide)

    groups = [
        ("Time (6)", ["hour_sin", "hour_cos", "dow_sin", "dow_cos", "is_business_hours", "month"]),
        ("Statistical (3)", ["amount_zscore", "amount_log_ratio", "amount_squared_log"]),
        ("Velocity (5)", ["customer_txn_count", "customer_avg_amount", "customer_amount_std", "customer_max_amount", "amount_vs_customer_avg"]),
        ("Categorical (7)", ["cat_grocery", "cat_gas", "cat_online", "cat_restaurant", "cat_retail", "cat_travel", "merchant_risk_score"]),
    ]
    x_positions = [0.3, 3.5, 6.8, 10.0]
    colors = [NAVY, RGBColor(0x0E, 0x74, 0x90), RGBColor(0x0F, 0x76, 0x6E), RGBColor(0x71, 0x32, 0xBB)]

    for (group, features), x, color in zip(groups, x_positions, colors):
        header = slide.shapes.add_shape(1, Inches(x), Inches(1.35), Inches(3.1), Inches(0.5))
        header.fill.solid()
        header.fill.fore_color.rgb = color
        header.line.fill.background()
        tf = header.text_frame
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = group
        r.font.name = "Arial"
        r.font.size = Pt(14)
        r.font.bold = True
        r.font.color.rgb = WHITE

        y = 2.0
        for feat in features:
            _add_text_box(slide, f"• {feat}", x + 0.1, y, 2.9, 0.4, font_size=13, color=DARK_GREY)
            y += 0.47

    # Correlation chart
    _add_image_safe(slide, FIGURES / "02_feature_correlations.png", 0.3, 4.9, 12.6)
    _add_slide_number(slide, slide_num, total, dark=True)


def slide_model_results(prs: Presentation, slide_num: int, total: int, metrics: dict) -> None:
    """Slide 7: Model Results."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_solid_bg(slide, prs, WHITE)
    _add_title_bar(slide, "Model Results — Isolation Forest + XGBoost")
    _add_accent_border(slide)

    xgb = metrics.get("models", {}).get("xgboost", {})
    iso = metrics.get("models", {}).get("isolation_forest", {})

    def _metric_card(name: str, m: dict, x: float, color: RGBColor) -> None:
        card = slide.shapes.add_shape(1, Inches(x), Inches(1.35), Inches(5.8), Inches(5.7))
        card.fill.solid()
        card.fill.fore_color.rgb = LIGHT_GREY
        card.line.color.rgb = color
        card.line.width = Pt(2)

        header2 = slide.shapes.add_shape(1, Inches(x), Inches(1.35), Inches(5.8), Inches(0.55))
        header2.fill.solid()
        header2.fill.fore_color.rgb = color
        header2.line.fill.background()
        tf2 = header2.text_frame
        p2 = tf2.paragraphs[0]
        p2.alignment = PP_ALIGN.CENTER
        r2 = p2.add_run()
        r2.text = name
        r2.font.name = "Arial"
        r2.font.size = Pt(18)
        r2.font.bold = True
        r2.font.color.rgb = WHITE

        metric_labels = [
            ("F1 Score", "f1"),
            ("ROC-AUC", "roc_auc"),
            ("Precision", "precision"),
            ("Recall", "recall"),
            ("Avg Precision", "average_precision"),
        ]
        my = 2.1
        for label, key in metric_labels:
            val = m.get(key, "N/A")
            val_str = f"{val:.4f}" if isinstance(val, float) else str(val)
            _add_text_box(slide, label, x + 0.2, my, 3.0, 0.4, font_size=14, color=DARK_GREY)
            val_color = GREEN if isinstance(val, float) and val > 0.9 else DARK_GREY
            _add_text_box(slide, val_str, x + 3.3, my, 2.3, 0.4, font_size=16, bold=True, color=val_color, align=PP_ALIGN.RIGHT)
            my += 0.75

    _metric_card("XGBoost (Supervised)", xgb, 0.3, GREEN)
    _metric_card("Isolation Forest (Unsupervised)", iso, 7.0, NAVY)
    _add_slide_number(slide, slide_num, total, dark=True)


def slide_api(prs: Presentation, slide_num: int, total: int) -> None:
    """Slide 8: FastAPI Inference Service."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_solid_bg(slide, prs, NAVY)
    _add_text_box(slide, "FastAPI Inference Service", 0.6, 0.3, 12.0, 0.9, font_size=36, bold=True)

    endpoints = [
        ("GET", "/health", "Liveness probe — returns status + models_loaded"),
        ("GET", "/metrics", "Model evaluation metrics (F1, AUC, precision, recall)"),
        ("GET", "/feature-schema", "List of 21 engineered features with dtypes"),
        ("POST", "/predict", "Single transaction → is_anomaly + anomaly_probability"),
        ("POST", "/predict/batch", "Batch transactions → predictions[] + anomaly_count"),
    ]
    method_colors = {"GET": RGBColor(0x16, 0xA3, 0x4A), "POST": RGBColor(0x22, 0x63, 0xEB)}

    y = 1.5
    for method, path, desc in endpoints:
        pill = slide.shapes.add_shape(1, Inches(0.5), Inches(y), Inches(1.1), Inches(0.42))
        pill.fill.solid()
        pill.fill.fore_color.rgb = method_colors[method]
        pill.line.fill.background()
        tf = pill.text_frame
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = method
        r.font.name = "Arial"
        r.font.size = Pt(13)
        r.font.bold = True
        r.font.color.rgb = WHITE

        _add_text_box(slide, path, 1.8, y, 2.8, 0.42, font_size=15, bold=True, color=ACCENT)
        _add_text_box(slide, desc, 4.8, y, 8.3, 0.42, font_size=14, color=WHITE)
        y += 0.8

    _add_text_box(slide, "Every response includes request_id (UUID4) + timestamp (ISO-8601 UTC)", 0.5, 5.7, 12.3, 0.45, font_size=14, color=ACCENT)
    _add_slide_number(slide, slide_num, total)


def slide_tests(prs: Presentation, slide_num: int, total: int) -> None:
    """Slide 9: Test Coverage."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_solid_bg(slide, prs, WHITE)
    _add_title_bar(slide, "Test Coverage — 49 Tests (39 Unit + 10 E2E)")
    _add_accent_border(slide)

    unit_tests = [
        ("test_api.py", "14", "All endpoints via FastAPI TestClient"),
        ("test_ingest.py", "14", "Schema validation, cleaning, derived columns"),
        ("test_features.py", "10", "Time, statistical, velocity, categorical"),
        ("test_validate.py", "5", "All 12 data quality checks"),
    ]
    _add_text_box(slide, "Unit Tests (pytest)", 0.3, 1.35, 6.0, 0.45, font_size=18, bold=True, color=NAVY)
    y = 1.95
    for fname, count, desc in unit_tests:
        _add_text_box(slide, fname, 0.3, y, 2.8, 0.38, font_size=14, bold=True, color=DARK_GREY)
        _add_text_box(slide, count + " tests", 3.2, y, 1.3, 0.38, font_size=14, bold=True, color=GREEN)
        _add_text_box(slide, desc, 4.6, y, 2.5, 0.38, font_size=13, color=DARK_GREY)
        y += 0.72

    _add_text_box(slide, "E2E Tests (Playwright + Chromium)", 7.1, 1.35, 5.8, 0.45, font_size=18, bold=True, color=NAVY)
    e2e = [
        "Health endpoint via requests",
        "Health page screenshot",
        "Swagger /docs page loads",
        "Normal transaction → is_anomaly=0",
        "Anomaly transaction → is_anomaly=1",
        "Predict endpoint screenshot",
        "Batch prediction (2 items)",
        "Metrics endpoint",
        "Metrics screenshot",
        "Feature schema endpoint",
    ]
    y = 1.95
    for item in e2e:
        _add_text_box(slide, f"✓  {item}", 7.1, y, 6.0, 0.38, font_size=13, color=DARK_GREY)
        y += 0.47

    # Playwright screenshot
    _add_image_safe(slide, SCREENSHOTS / "02_swagger_docs.png", 0.3, 5.1, 6.4)
    _add_image_safe(slide, SCREENSHOTS / "04_metrics_endpoint.png", 6.9, 5.1, 6.0)
    _add_slide_number(slide, slide_num, total, dark=True)


def slide_eda(prs: Presentation, slide_num: int, total: int) -> None:
    """Slide 10: EDA Insights — 5 charts."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_solid_bg(slide, prs, WHITE)
    _add_title_bar(slide, "EDA Insights — 5 Visualisations")
    _add_accent_border(slide)

    chart_files = [
        ("01_target_distribution.png", "Class Distribution"),
        ("04_amount_distribution.png", "Amount: Normal vs Anomaly"),
        ("05_time_series_trend.png", "Time Series Trend"),
    ]
    x_positions = [0.2, 4.55, 8.9]
    for (fname, title), x in zip(chart_files, x_positions):
        _add_image_safe(slide, FIGURES / fname, x, 1.3, 4.1)
        _add_text_box(slide, title, x, 5.5, 4.1, 0.4, font_size=12, color=DARK_GREY, align=PP_ALIGN.CENTER)

    _add_image_safe(slide, FIGURES / "03_missing_values.png", 0.2, 5.8, 6.3)
    _add_slide_number(slide, slide_num, total, dark=True)


def slide_jira_confluence(prs: Presentation, slide_num: int, total: int) -> None:
    """Slide 11: JIRA & Confluence."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_solid_bg(slide, prs, WHITE)
    _add_title_bar(slide, "JIRA & Confluence Integration")
    _add_accent_border(slide)

    tickets = [
        ("ADP-8", "Epic", "Transaction Anomaly Detection ML Pipeline"),
        ("ADP-9", "Story", "Data generation: synthetic 10K dataset"),
        ("ADP-10", "Story", "Data ingestion & preprocessing"),
        ("ADP-11", "Story", "Feature engineering: 21 new features"),
        ("ADP-12", "Story", "Model training: Isolation Forest + XGBoost"),
        ("ADP-13", "Story", "FastAPI inference service"),
        ("ADP-14", "Story", "Test suite: 39 unit + 10 Playwright e2e"),
    ]
    y = 1.45
    for key, itype, summary in tickets:
        type_color = NAVY if itype == "Epic" else RGBColor(0x0E, 0x74, 0x90)
        pill = slide.shapes.add_shape(1, Inches(0.3), Inches(y), Inches(1.1), Inches(0.38))
        pill.fill.solid()
        pill.fill.fore_color.rgb = type_color
        pill.line.fill.background()
        tf = pill.text_frame
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = key
        r.font.name = "Arial"
        r.font.size = Pt(12)
        r.font.bold = True
        r.font.color.rgb = WHITE

        _add_text_box(slide, itype, 1.55, y, 1.3, 0.38, font_size=13, color=type_color)
        _add_text_box(slide, summary, 3.0, y, 6.8, 0.38, font_size=13, color=DARK_GREY)
        y += 0.62

    _add_text_box(slide, "Sprint 1 - Anomaly Pipeline: Apr 17 – Apr 30, 2026", 0.3, 5.95, 8.0, 0.4, font_size=14, bold=True, color=NAVY)
    _add_text_box(slide, "Confluence: Transaction Anomaly Detection Pipeline\nSpace: CR (ML Engineering)", 9.0, 1.5, 4.0, 0.8, font_size=13, color=DARK_GREY)
    _add_image_safe(slide, SCREENSHOTS / "01_health_endpoint.png", 9.0, 2.5, 4.0)
    _add_slide_number(slide, slide_num, total, dark=True)


def slide_summary(prs: Presentation, slide_num: int, total: int) -> None:
    """Slide 12: Summary & Next Steps — NAVY."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_solid_bg(slide, prs, NAVY)
    _add_text_box(slide, "Summary & Next Steps", 0.6, 0.3, 12.0, 0.9, font_size=36, bold=True)

    achieved = [
        "10,000 synthetic transactions generated (5 fraud patterns)",
        "12/12 data quality validation checks passing",
        "21 engineered features (time, statistical, velocity, categorical)",
        "XGBoost: F1=1.0, ROC-AUC=1.0 | Isolation Forest: AUC=0.986",
        "FastAPI: 5 endpoints, request_id + timestamp on every response",
        "39 unit tests + 10 Playwright e2e tests — all passing",
        "JIRA: Epic ADP-8 + 6 stories in Sprint 1",
        "Confluence page published in CR space",
    ]
    _add_text_box(slide, "Achieved", 0.5, 1.3, 5.8, 0.4, font_size=18, bold=True, color=ACCENT)
    y = 1.85
    for item in achieved:
        _add_text_box(slide, f"✓  {item}", 0.5, y, 6.0, 0.42, font_size=13, color=WHITE)
        y += 0.52

    next_steps = [
        "Deploy to Kubernetes with Helm chart",
        "Add SHAP explainability endpoint",
        "Integrate streaming (Kafka) for real-time scoring",
        "A/B testing framework for model versions",
        "Add Autoencoder as third model",
        "Grafana dashboard for anomaly rate monitoring",
    ]
    _add_text_box(slide, "Next Steps", 7.2, 1.3, 5.5, 0.4, font_size=18, bold=True, color=ACCENT)
    y = 1.85
    for item in next_steps:
        _add_text_box(slide, f"→  {item}", 7.2, y, 5.8, 0.42, font_size=13, color=WHITE)
        y += 0.62

    _add_text_box(slide, "Built with Claude Code", 0.5, 6.95, 5.0, 0.4, font_size=13, color=RGBColor(0x94, 0xA3, 0xB8))
    _add_slide_number(slide, slide_num, total)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_presentation() -> Path:
    """Build the full pipeline presentation and save to reports/pipeline_presentation.pptx.

    Returns:
        Path to the saved PPTX file.
    """
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    metrics = _load_metrics()
    total = 12

    slide_cover(prs, 1, total)
    slide_agenda(prs, 2, total)
    slide_problem(prs, 3, total)
    slide_architecture(prs, 4, total)
    slide_validation(prs, 5, total)
    slide_features(prs, 6, total)
    slide_model_results(prs, 7, total, metrics)
    slide_api(prs, 8, total)
    slide_tests(prs, 9, total)
    slide_eda(prs, 10, total)
    slide_jira_confluence(prs, 11, total)
    slide_summary(prs, 12, total)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT_PATH))
    return OUT_PATH


if __name__ == "__main__":
    out = build_presentation()
    print(f"Presentation saved: {out}  ({out.stat().st_size // 1024} KB, 12 slides)")
