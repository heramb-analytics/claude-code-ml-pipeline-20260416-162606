#!/bin/bash
# setup.sh — pre-pipeline setup, called automatically by Claude before Stage 2

echo "=== PRE-PIPELINE SETUP ==="

# 1. Ensure git is initialised
if [ ! -d ".git" ]; then
  git init && git checkout -b main
  git add . && git commit -m "chore: auto-init by setup.sh"
  echo "  ✅ git initialised"
else
  echo "  ✅ git already initialised"
fi

# 2. Ensure GitHub remote exists
if ! git remote | grep -q origin; then
  if command -v gh &>/dev/null; then
    REPO_NAME=$(basename $(pwd))
    gh repo create "$REPO_NAME" --public --source=. --push --yes 2>/dev/null || true
    echo "  ✅ GitHub repo created: $REPO_NAME"
  else
    echo "  ⚠️  No GitHub remote and gh CLI not found."
  fi
else
  echo "  ✅ GitHub remote already set"
fi

# 3. Ensure Python packages installed
python3 -c "import pandas, sklearn, fastapi, xgboost, playwright" 2>/dev/null || {
  pip3 install -q pandas numpy scikit-learn xgboost fastapi uvicorn pytest \
    playwright pytest-playwright APScheduler matplotlib seaborn scipy requests httpx pyarrow
  python3 -m playwright install chromium
}
echo "  ✅ Python packages OK"

# 4. Create git worktrees for Stage 2 parallel processing
DT=$(date +%Y%m%d-%H%M%S)
git worktree add ../wt-features-$DT -b feature/features-agent-$DT 2>/dev/null || true
git worktree add ../wt-eda-$DT     -b feature/eda-agent-$DT     2>/dev/null || true
git worktree add ../wt-val-$DT     -b feature/validation-agent-$DT 2>/dev/null || true
echo "  ✅ Worktrees created"

# 5. Ensure output folders exist
mkdir -p reports/screenshots reports/figures logs docs
echo "  ✅ Output folders ready"

echo "=== SETUP COMPLETE ==="
