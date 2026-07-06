#!/usr/bin/env bash
# One-shot Fly.io bring-up — collapses docs/HOSTING.md's 6 manual steps into a
# single script. Run this from a machine that will have `flyctl` + a browser
# available for the one-time login; nothing here can substitute for that (an
# agent has no path to your Fly.io account, by design).
#
# What this does, in order:
#   1. Checks flyctl is installed and you're logged in (fails with the exact fix
#      if not — never silently proceeds without real Fly auth).
#   2. Creates the app from fly.toml (idempotent: skips if it already exists).
#   3. Sets every required secret — auto-generates the two pure-random ones
#      (KUDBEE_API_TOKEN, KUDBEE_SESSION_SECRET), prompts (hidden input) for the
#      two you must choose yourself (KUDBEE_DASHBOARD_PASSWORD, KUDBEE_GH_TOKEN),
#      unless you've already exported them as env vars.
#   4. Deploys and smoke-tests /api/health.
#   5. Creates a deploy-only Fly token and prints it — THIS is the one step that
#      can't be automated further: paste it as the GitHub repo secret
#      FLY_API_TOKEN yourself at the URL this script prints (a script running on
#      your machine has no path to push a secret into GitHub's UI on its own,
#      short of you also handing it a GitHub PAT with admin:repo-hook scope,
#      which is a bigger credential than this needs).
#
# Usage:
#   curl -L https://fly.io/install.sh | sh   # once, if flyctl isn't installed
#   fly auth login                            # once, opens a browser
#   bash scripts/fly_bootstrap.sh
#
# Safe to re-run: every step below is idempotent (checks before acting).
set -euo pipefail

APP_NAME="${FLY_APP_NAME:-kudbee-quant-api}"
REPO="KudbeeZero/Kudbee-Quant-Bot-v1.0"

command -v fly >/dev/null 2>&1 || command -v flyctl >/dev/null 2>&1 || {
  echo "flyctl not found. Install it first:" >&2
  echo "  curl -L https://fly.io/install.sh | sh" >&2
  echo "  (then restart your shell, or: export PATH=\"\$HOME/.fly/bin:\$PATH\")" >&2
  exit 1
}
FLY=fly; command -v fly >/dev/null 2>&1 || FLY=flyctl

if ! "$FLY" auth whoami >/dev/null 2>&1; then
  echo "Not logged in to Fly. Run this first (opens a browser):" >&2
  echo "  $FLY auth login" >&2
  exit 1
fi
echo "Logged in as: $("$FLY" auth whoami)"

if "$FLY" status --app "$APP_NAME" >/dev/null 2>&1; then
  echo "App '$APP_NAME' already exists — skipping launch."
else
  echo "Creating app '$APP_NAME' from fly.toml (no deploy yet)..."
  "$FLY" launch --no-deploy --copy-config --name "$APP_NAME" --yes
fi

_rand() { python3 -c 'import secrets; print(secrets.token_urlsafe(32))'; }

: "${KUDBEE_API_TOKEN:=$(_rand)}"
: "${KUDBEE_SESSION_SECRET:=$(_rand)}"
: "${KUDBEE_SITE_ORIGIN:=https://kudbeex.xyz}"
: "${KUDBEE_GH_REPO:=$REPO}"

if [ -z "${KUDBEE_DASHBOARD_PASSWORD:-}" ]; then
  read -r -s -p "Dashboard login password (KUDBEE_DASHBOARD_PASSWORD, memorable — hidden input): " KUDBEE_DASHBOARD_PASSWORD
  echo
fi
if [ -z "${KUDBEE_GH_TOKEN:-}" ]; then
  echo "KUDBEE_GH_TOKEN needed: a fine-grained GitHub PAT scoped to ONLY this repo," >&2
  echo "  Contents: Read and write, nothing else. Create one at:" >&2
  echo "  https://github.com/settings/tokens?type=beta" >&2
  read -r -s -p "Paste the token here (hidden input): " KUDBEE_GH_TOKEN
  echo
fi

echo "Setting secrets on '$APP_NAME'..."
"$FLY" secrets set --app "$APP_NAME" \
  KUDBEE_API_TOKEN="$KUDBEE_API_TOKEN" \
  KUDBEE_DASHBOARD_PASSWORD="$KUDBEE_DASHBOARD_PASSWORD" \
  KUDBEE_SESSION_SECRET="$KUDBEE_SESSION_SECRET" \
  KUDBEE_SITE_ORIGIN="$KUDBEE_SITE_ORIGIN" \
  KUDBEE_GH_TOKEN="$KUDBEE_GH_TOKEN" \
  KUDBEE_GH_REPO="$KUDBEE_GH_REPO"

echo "Deploying..."
"$FLY" deploy --app "$APP_NAME"

echo "Smoke-testing /api/health..."
HEALTH_URL="https://${APP_NAME}.fly.dev/api/health"
if curl -sS -f "$HEALTH_URL" >/dev/null; then
  echo "OK: $HEALTH_URL is live."
else
  echo "WARNING: $HEALTH_URL did not respond as expected — check 'fly logs --app $APP_NAME'." >&2
fi

echo
echo "Creating a deploy-only token for the hourly freshness redeploy (fly-deploy.yml)..."
DEPLOY_TOKEN="$("$FLY" tokens create deploy --app "$APP_NAME" 2>/dev/null | tail -1)"
echo
echo "=================================================================="
echo "ONE MANUAL STEP LEFT — this script cannot do this part for you:"
echo "  1. Copy this token:"
echo "     $DEPLOY_TOKEN"
echo "  2. Paste it here as a new repo secret named FLY_API_TOKEN:"
echo "     https://github.com/${REPO}/settings/secrets/actions/new"
echo "Once that's saved, fly-deploy.yml stops no-op'ing and the API stays"
echo "current on every push + hourly, automatically."
echo "=================================================================="
echo
if [ "$APP_NAME" != "kudbee-quant-api" ]; then
  echo "NOTE: app name is '$APP_NAME' (not the default). Also set the Cloudflare"
  echo "Pages env var API_ORIGIN=https://${APP_NAME}.fly.dev so the /api/* proxy"
  echo "(functions/api/[[path]].js) points at the right place."
fi
echo "Also remember (still manual, docs/HOSTING.md step 6 / CROSSROADS X2 step 6):"
echo "  KUDBEE_API_TOKEN printed/set above must ALSO be added as the repo secret"
echo "  KUDBEE_API_TOKEN so telegram-register.yml can self-register the webhook:"
echo "  https://github.com/${REPO}/settings/secrets/actions/new"
echo "  value: $KUDBEE_API_TOKEN"
