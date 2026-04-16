#!/bin/bash
# preflight_check.sh — verifies JIRA, Confluence, GitHub connectivity
# Run before starting the pipeline: bash scripts/preflight_check.sh

PASS=0
FAIL=0

print_pass() { echo "  ✅  $1"; PASS=$((PASS+1)); }
print_fail() { echo "  ❌  $1"; echo "      Fix: $2"; FAIL=$((FAIL+1)); }

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PRE-FLIGHT CHECK — JIRA / Confluence / GitHub / MCP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 1. Env vars ─────────────────────────────────────────────────────
echo "[1] Environment variables"
[ -n "$JIRA_URL" ]         && print_pass "JIRA_URL set"         || print_fail "JIRA_URL missing"         "Add to ~/.zshrc and run source ~/.zshrc"
[ -n "$JIRA_USER" ]        && print_pass "JIRA_USER set"        || print_fail "JIRA_USER missing"        "Add export JIRA_USER=... to ~/.zshrc"
[ -n "$JIRA_TOKEN" ]       && print_pass "JIRA_TOKEN set"       || print_fail "JIRA_TOKEN missing"       "Generate at id.atlassian.com/manage-profile/security/api-tokens"
[ -n "$CONFLUENCE_URL" ]   && print_pass "CONFLUENCE_URL set"   || print_fail "CONFLUENCE_URL missing"   "Add to ~/.zshrc: export CONFLUENCE_URL=https://yoursite.atlassian.net/wiki"
[ -n "$CONFLUENCE_USER" ]  && print_pass "CONFLUENCE_USER set"  || print_fail "CONFLUENCE_USER missing"  "Add export CONFLUENCE_USER=your@email.com to ~/.zshrc"
[ -n "$CONFLUENCE_TOKEN" ] && print_pass "CONFLUENCE_TOKEN set" || print_fail "CONFLUENCE_TOKEN missing" "Use same token as JIRA_TOKEN for cloud Atlassian"
[ -n "$GITHUB_TOKEN" ]     && print_pass "GITHUB_TOKEN set"     || print_fail "GITHUB_TOKEN missing"     "Generate at github.com/settings/tokens with repo+workflow scopes"
[ -n "$GITHUB_USERNAME" ]  && print_pass "GITHUB_USERNAME set"  || print_fail "GITHUB_USERNAME missing"  "Add export GITHUB_USERNAME=your-username to ~/.zshrc"
echo ""

# ── 2. GitHub API ────────────────────────────────────────────────────
echo "[2] GitHub API"
GH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user 2>/dev/null)
[ "$GH_STATUS" = "200" ] && print_pass "GitHub API reachable (HTTP 200)" || print_fail "GitHub API failed (HTTP $GH_STATUS)" "Check GITHUB_TOKEN is valid and not expired"
echo ""

# ── 3. JIRA API ──────────────────────────────────────────────────────
echo "[3] JIRA API"
if [ -n "$JIRA_URL" ] && [ -n "$JIRA_TOKEN" ]; then
  JIRA_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -u "$JIRA_USER:$JIRA_TOKEN" "$JIRA_URL/rest/api/2/myself" 2>/dev/null)
  [ "$JIRA_STATUS" = "200" ] && print_pass "JIRA API reachable (HTTP 200)" || print_fail "JIRA API failed (HTTP $JIRA_STATUS)" "Check JIRA_TOKEN at id.atlassian.com/manage-profile/security/api-tokens"
  JIRA_PROJECTS=$(curl -s -u "$JIRA_USER:$JIRA_TOKEN" "$JIRA_URL/rest/api/2/project" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))" 2>/dev/null)
  if [ "$JIRA_PROJECTS" = "0" ] || [ -z "$JIRA_PROJECTS" ]; then
    print_fail "JIRA: zero projects exist" "Go to $JIRA_URL → Projects → Create project → Scrum → key: TXAP"
  else
    print_pass "JIRA has $JIRA_PROJECTS project(s) — ready"
  fi
else
  print_fail "JIRA check skipped" "Set JIRA_URL, JIRA_USER, JIRA_TOKEN in ~/.zshrc"
fi
echo ""

# ── 4. Confluence API ────────────────────────────────────────────────
echo "[4] Confluence API"
if [ -n "$CONFLUENCE_URL" ] && [ -n "$CONFLUENCE_TOKEN" ]; then
  CONF_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -u "$CONFLUENCE_USER:$CONFLUENCE_TOKEN" "$CONFLUENCE_URL/rest/api/space" 2>/dev/null)
  [ "$CONF_STATUS" = "200" ] && print_pass "Confluence API reachable (HTTP 200)" || print_fail "Confluence API failed (HTTP $CONF_STATUS)" "Check CONFLUENCE_TOKEN — use same token as JIRA for cloud Atlassian"
  # Check CR space exists
  CR_CHECK=$(curl -s -u "$CONFLUENCE_USER:$CONFLUENCE_TOKEN" "$CONFLUENCE_URL/rest/api/space/CR" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('key','NOT_FOUND'))" 2>/dev/null)
  [ "$CR_CHECK" = "CR" ] && print_pass "Confluence CR space exists" || print_fail "Confluence CR space not found" "Create space CR at $CONFLUENCE_URL → Spaces → Create Space → key: CR"
else
  print_fail "Confluence check skipped" "Set CONFLUENCE_URL, CONFLUENCE_USER, CONFLUENCE_TOKEN in ~/.zshrc"
fi
echo ""

# ── 5. MCP servers ───────────────────────────────────────────────────
echo "[5] MCP servers registered"
MCP_LIST=$(claude mcp list 2>/dev/null)
echo "$MCP_LIST" | grep -q "git"        && print_pass "git MCP registered"        || print_fail "git MCP not registered"        "Run: claude mcp add git -s user -- uvx mcp-server-git"
echo "$MCP_LIST" | grep -q "jira"       && print_pass "jira MCP registered"       || print_fail "jira MCP not registered"       "See §1G for full command"
echo "$MCP_LIST" | grep -q "confluence" && print_pass "confluence MCP registered" || print_fail "confluence MCP not registered" "See §1G for full command"
echo "$MCP_LIST" | grep -q "playwright" && print_pass "playwright MCP registered" || print_fail "playwright MCP not registered" "Run: claude mcp add playwright -s user -- npx @playwright/mcp@latest"
echo ""

# ── 6. Git state ─────────────────────────────────────────────────────
echo "[6] Git state"
[ -d ".git" ] && print_pass ".git folder exists" || print_fail ".git folder missing" "Run: git init && git checkout -b main && git add . && git commit -m 'init'"
git log --oneline 2>/dev/null | grep -q "." && print_pass "git has at least 1 commit" || print_fail "No commits yet" "Run: git add . && git commit -m 'chore: initial scaffold'"
echo ""

# ── Summary ──────────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL=$((PASS+FAIL))
if [ "$FAIL" = "0" ]; then
  echo "  ✅  ALL $TOTAL CHECKS PASSED — safe to start pipeline"
else
  echo "  ⚠️   $PASS/$TOTAL passed · $FAIL failed — fix issues above before starting pipeline"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
