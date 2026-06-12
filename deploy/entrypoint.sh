#!/bin/sh
# Container entrypoint for the hosted Kudbee API (see docs/DEPLOY.md).
#
# The app CODE runs from the image (pip-installed); the journal STATE lives in
# a repo clone on the persistent volume, kept in sync with GitHub by
# deploy/journal_sync.py. KUDBEE_JOURNAL_PATH points the app at that clone.
#
# Required env/secrets: KUDBEE_GIT_TOKEN (fine-grained PAT, contents R/W on
# this repo only), KUDBEE_API_TOKEN (write auth for /api/alert + /api/paper/scan).
set -eu

REPO_DIR="${KUDBEE_REPO_DIR:-/data/repo}"
REPO_SLUG="${KUDBEE_REPO_SLUG:-KudbeeZero/Kudbee-Quant-Bot-v1.0}"
BRANCH="${KUDBEE_REPO_BRANCH:-main}"
SYNC_INTERVAL="${KUDBEE_SYNC_INTERVAL:-60}"
export KUDBEE_JOURNAL_PATH="${KUDBEE_JOURNAL_PATH:-$REPO_DIR/data/journal.json}"

if [ ! -d "$REPO_DIR/.git" ]; then
  echo "[entrypoint] cloning $REPO_SLUG ($BRANCH) into $REPO_DIR"
  git clone --depth 50 --single-branch --branch "$BRANCH" \
    "https://x-access-token:${KUDBEE_GIT_TOKEN}@github.com/${REPO_SLUG}.git" "$REPO_DIR"
fi
# volume may have been populated under a different uid (re-deploys, local tests)
git config --global --add safe.directory "$REPO_DIR"
git -C "$REPO_DIR" config user.name "kudbee-host"
git -C "$REPO_DIR" config user.email "kudbee-host@users.noreply.github.com"

python /app/deploy/journal_sync.py --repo "$REPO_DIR" --branch "$BRANCH" \
  --interval "$SYNC_INTERVAL" &

exec uvicorn kudbee_quant.api:app --host 0.0.0.0 --port "${PORT:-8080}"
