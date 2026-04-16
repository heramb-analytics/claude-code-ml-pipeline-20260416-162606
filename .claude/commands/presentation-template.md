# Presentation Template — Stage 11
# Claude creates reports/pipeline_presentation.pptx using python-pptx.
# Run: pip3 install python-pptx

## DESIGN SYSTEM
Primary color: #1E3A8A (navy)
Accent color:  #0F766E (teal)
Background: white (#FFFFFF) for content slides
Title font: Arial Bold, 36pt
Heading font: Arial Bold, 24pt
Body font: Arial, 18pt
Slide size: 13.33 x 7.5 inches (widescreen 16:9)

## EVERY SLIDE MUST HAVE:
- Colored title bar (navy) with white title text
- Slide number in bottom-right corner (format: N / 8)
- Left accent bar (4px navy vertical stripe)

## SLIDE STRUCTURE (8 slides)

### Slide 1 — Cover
Background: navy (#1E3A8A) full bleed
Title: project name, Arial Bold 40pt, white, centered
Subtitle: 'Built with Claude Code · {date}', Arial 20pt, light blue
No slide number on cover.

### Slide 2 — Problem Statement
Title bar: navy
Content: 3 bullet points from Stage 0 discovery
Insert EDA chart: reports/figures/01_target_distribution.png (right side, 40% width)

### Slide 3 — EDA Highlights
Title bar: navy
LEFT (45% width): reports/figures/02_feature_correlations.png
RIGHT (45% width): reports/figures/03_missing_values.png
Caption bar at bottom: '{N} rows · {N} features · {anomaly_rate}% anomaly rate'

### Slide 4 — Data Engineering
Title bar: navy
Table: quality checks — Check Name | Result | Rows Affected
Table header: navy, white text. Rows alternate white/light-grey.
Insert chart: reports/figures/04_amount_distribution.png (bottom-right, 35% width)

### Slide 5 — Model Results
Title bar: navy
3 metric cards (large): F1, AUC-ROC, Precision — navy border, teal value text
Algorithm label below cards
Insert chart: reports/figures/05_time_series_trend.png (right, 50% width)

### Slide 6 — App Demo Screenshot
Title bar: navy
Screenshot: reports/screenshots/01_dashboard_home.png — full content area
Caption: 'Live at http://localhost:8000'

### Slide 7 — Test Evidence
Title bar: navy
LEFT: reports/screenshots/03_prediction_result.png (45% width)
RIGHT: reports/screenshots/04_swagger_docs.png (45% width)
Bottom bar: '8 unit tests passed · 6 Playwright E2E tests passed'

### Slide 8 — Pipeline Complete
Background: navy (#1E3A8A) full bleed
Title: 'PIPELINE COMPLETE', white, centered, 40pt
4 summary bullets in white text:
  Model: {algorithm} — {metric}: {value}
  API: http://localhost:8000
  GitHub: {repo_url}
  JIRA: {N} tickets · Confluence: CR space
No slide number.
