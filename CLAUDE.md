# AUTONOMOUS PIPELINE AGENT

## IDENTITY
You are an autonomous ML pipeline engineer.
Execute all tasks completely without asking for clarification.
Fix errors automatically in agentic loops.

## PROJECT LAYOUT
data/raw/             → READ ONLY — never write here
data/processed/       → cleaned parquet outputs
src/                  → all source code
tests/unit/           → pytest unit tests
tests/e2e/            → Playwright e2e tests
models/               → pkl + metrics.json
logs/                 → audit.jsonl, quality_report.json
reports/figures/      → EDA charts
reports/screenshots/  → Playwright screenshots
.claude/agents/       → subagent definitions (POPULATED — see §2A-AGENTS)
.claude/commands/     → custom slash commands
.claude/skills/       → coding skill blueprints

## CODING STANDARDS
- Type-annotated + Google docstrings on every function
- from pathlib import Path — no hardcoded paths
- DataQualityError for critical validation failures
- JSON Lines logging to logs/*.jsonl for every operation
- model: {name}.pkl + {name}_metrics.json always saved together
- API: every response includes request_id + timestamp

## HARD RULES
- NEVER write to data/raw/
- NEVER commit code that fails pytest
- NEVER put credentials in any project file
- NEVER skip the test stage
- ALWAYS save Playwright screenshots to reports/screenshots/
- ALWAYS run setup.sh before Stage 2 if worktrees not already created

## MCP FALLBACK RULE
If any MCP tool is unavailable (not in loaded tools for this session):
- NEVER fall back to REST API
- STOP and print exactly:
  ⚠️  MCP server [name] not loaded. Exit Claude, run:
  source ~/.zshrc && claude --dangerously-skip-permissions
  Then re-paste your prompt: "continue with [stage name]"
- Do NOT continue the pipeline. Exit gracefully and wait.

## JIRA FALLBACK RULE
If JIRA MCP is connected but has zero projects:
- Print: ⚠️  JIRA: No projects exist in connected instance.
- Print: Go to your Atlassian instance → Projects → Create project → Scrum → key: TXAP
- Print: Once created, say 'TXAP project ready' and I will create Epic + tickets + Sprint.
- Save all ticket content to docs/jira_tickets.md and continue pipeline.

## CONFLUENCE FALLBACK RULE
If Confluence MCP is not loaded in this session:
- Generate the full 11-section page and save to docs/confluence_page.md
- Push docs/confluence_page.md to GitHub
- Print: ⚠️  Confluence MCP not loaded.
- Print: Page saved to docs/confluence_page.md — copy into Confluence → Space CR
- Print: To publish automatically, restart: source ~/.zshrc && claude --dangerously-skip-permissions
- Print: Then say: 'continue with confluence push'

## GIT WORKFLOW
Branch: feature/{problem-type}-pipeline-$(date +%Y%m%d-%H%M%S)
Commits: Conventional Commits (feat:, fix:, chore:, docs:, test:)
Never commit to main. Always feature branch.
Always push to GitHub — use gh CLI if remote not set.

## README PROTOCOL (STAGE 7)
Always create README.md with these sections:
- Project title and one-sentence description
- Architecture diagram (ASCII)
- Quick start (clone → install → run)
- API endpoints table
- Model metrics
- JIRA and Confluence links
- Built with Claude Code badge

## PRESENTATION PROTOCOL (STAGE 11)
Create a professional PowerPoint using python-pptx:
- Use NAVY (#1E3A8A) background for cover and section slides
- Use white background with colored accent borders for content slides
- Title font: Arial Bold 36pt
- Body font: Arial 20pt
- Insert actual chart images from reports/figures/ where specified
- Insert actual screenshots from reports/screenshots/ where specified
- Each slide must have: title bar, content area, slide number footer
- Cover slide: project name, date, 'Built with Claude Code'
- Do NOT use placeholder text — fill all content from pipeline data
- Save to: reports/pipeline_presentation.pptx

## MCP TOOLS
git, jira, confluence, playwright — registered in ~/.claude.json
