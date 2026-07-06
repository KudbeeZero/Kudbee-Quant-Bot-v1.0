#!/usr/bin/env bash
# Delete the remote branches the 2026-07-06 Branch Execution Ledger classified DEAD
# (section D: 66 fully merged + 36 patch-equivalent squash leftovers) or SUPERSEDED
# (section C: 21 branches whose unique value has been harvested into MEMORY/docs/audits
# — see MEMORY §88, N7), owner-approved under CROSSROADS X5. Agent containers cannot
# delete refs (the git proxy 403s `push --delete`), so this is the owner-runnable half
# of that approval.
#
# SAFETY:
#   - DEAD_BRANCHES (section D): RE-VERIFIED against a fresh origin/main immediately
#     before deletion — must be either an ancestor of main or fully patch-equivalent
#     (`git cherry` reports zero unique commits).
#   - SUPERSEDED_BRANCHES (section C): these DO carry unique commits (that's why they
#     needed harvesting, not just a merge check), so the safety net is different: each
#     branch's head SHA is PINNED here at the moment its content was harvested. If the
#     branch has moved since (someone pushed to it), the pin won't match and it's
#     skipped rather than deleted blind.
# Anything that fails its verification is skipped loudly, never deleted. Run from a
# FULL clone (the script unshallows if needed — see MEMORY §84).
#
# Usage:  bash scripts/delete_dead_branches.sh          # dry-run (default)
#         bash scripts/delete_dead_branches.sh --run    # actually delete
set -uo pipefail

RUN=0
[ "${1:-}" = "--run" ] && RUN=1

# Section D of docs/AGENT_ORCHESTRATION_LEDGER.md (2026-07-06), verbatim.
DEAD_BRANCHES=(
  # fully merged (66)
  claude/arm-pay-yourself-exit-ppswno claude/cancel-to-close-bug-tkngpm
  claude/confluence-new-signals-audit-a6gxt6 claude/confluence-r-cycle-backtest-eg45m1
  claude/daily-trade-graph-txyr9a claude/dashboard-segmentation
  claude/execution-backtest-maker-market-d96f9x claude/handoff-audit-3dgde4
  claude/handoff-audit-8latbu claude/handoff-audit-h90pmc claude/handoff-audit-hvuuab
  claude/handoff-audit-tradingview-6sswe1 claude/hello-1lje1b claude/hello-7olm3u
  claude/homepage-admin-dashboard-redesign-3tdnki claude/kudbee-quant-audit-report-nxj1de
  claude/level-cluster-confirm claude/live-trades-5m-pause-a1wuk3
  claude/live-trades-check-plan-5y27i8 claude/market-trading-tools-analysis-l2rnr1
  claude/overnight-algo-research-plan-hyqzf6 claude/render-deploy-prep
  claude/scan-top100-5m claude/session-closeout-test-report claude/site-trade-demo
  claude/sol-short-position-0eytax claude/tr-level-intelligence-qc4i2p
  claude/trade-data-pull-9ympy0 claude/trade-notifications-telegram-iykadc
  claude/trade-reads-animation claude/trade-setup-entry-vfkn7m
  claude/trade-story-explainer claude/trade-story-step-control
  claude/trade-viz-draggable-indicators-yncx2t claude/trades-performance-check-bl18wm
  claude/trailing-stop-backtest-jz0aho claude/vector-candle-logger
  claude/website-design-seo-067ci3 docs/closeout-brand-webhook-research
  docs/closeout-loop-agent docs/deadline-decision-log docs/telegram-setup-runbook
  docs/update-handoff-memory-s47-sA feat/binary-event-filter feat/brand-notify-upgrade
  feat/experiment-5m-long-only feat/forward-validation-toolkit
  feat/loop-engineering-intelligence feat/summary-voice-format feat/telegram-commands
  feat/telegram-event-layer feat/telegram-intelligence feat/telegram-per-book-summary
  feat/trade-event-alerts feat/trailing-stop-5m feat/voice-friendly-summary
  fix/deadline-and-tp1 fix/journal-fill-atomic fix/price-display-scientific-notation
  fix/summary-pending-reconcile fix/today-rolls-at-asia-open fix/tp1-partial-close
  fix/webhook-self-register harden-trade-bot-cron research/max-bars-time-exit-sweep
  research/psych-level-reversal
  # patch-equivalent squash leftovers (36)
  chore/cut-losing-books chore/flatten-stale-timeframe-positions
  chore/mark-800ema-tested-negative claude/dxy-regime-crypto-backtest
  claude/engine-correctness-fixes claude/fix-stale-asset-cache
  claude/mgmt-geometry-clean-rerun claude/n4-ps42u7 claude/og-cover-image
  claude/post-hoc-audit-118-117 claude/premium-setups-section
  claude/revert-vwap-momentum claude/security-review-hardening
  claude/site-overhaul-honest claude/tiered-exit-strategy
  claude/tino-crypto-obs-and-weekly-brief claude/tino-videos-telegram-check-mevktp
  claude/trade-flow-engine claude/website-redesign-journal
  docs/closeout-telegram-suite-sB feat/800-ema-study feat/800-ema-study-backtest
  feat/brinks-box-week-levels feat/daily-pnl-autopsy feat/dynamic-volume-universe
  feat/experiment-c-clean-trend-stack feat/macro-weekly-bias
  feat/management-geometry-backtest feat/max-reminder-frequency
  feat/section41-gap-prereg feat/three-push-deepdive feat/tr-confluence-candidates
  fix/reliable-telegram-scheduling fix/today-rolls-at-ny-open
  research/exit-geometry-sweep research/graphify-evaluation
)

# Section C of docs/AGENT_ORCHESTRATION_LEDGER.md (2026-07-06) — "branch head_sha"
# pairs, pinned at harvest time. `git cherry` can't be used to verify these (they
# have real unique commits by definition); the pin substitutes.
SUPERSEDED_BRANCHES=(
  "claude/fix-partial-bar d353ee3c" "claude/website-seo-finish 582981f4"
  "claude/section41-gap-run dc426171" "claude/kudbee-quant-audit-v1-is91p2 a1780fc1"
  "claude/agent-orchestration-ledger 57650c25" "feat/website-premium-polish 60838055"
  "feat/management-shadow-scorer b59e86f9" "feat/management-geometry-study 2c2b0d6f"
  "feat/telegram-deadline-alert 3078bdc5" "feat/brand-telegram-messages affd7e9e"
  "feat/tr-mlevel-system 80c49e43" "feat/mtf-15m-30m-backtest 5610db74"
  "claude/fable-5-release-review-mow58s 4746e66e"
  "claude/handoff-audit-fee-scoring-p0yg4n 9ae6f581" "claude/handoff-audit-xtn2bz 26eef3fc"
  "claude/vah-trap-reversal-study 753e5462" "claude/handoff-audit-rk3gn7 0669fb37"
  "research/psych-level-reversal-1h 069d4ef1" "claude/kudbeex-blank-page-q6pdql 85dbc98d"
  "claude/handoff-audit-8aps4t 05e2d54b" "claude/pr-14-handoff-audit-gpo9ab d0a4d358"
)

if [ "$(git rev-parse --is-shallow-repository)" = "true" ]; then
  echo "Shallow clone detected — unshallowing first (MEMORY §84)…"
  git fetch --unshallow origin main
fi
git fetch origin --prune

deleted=0 skipped=0 gone=0
for b in "${DEAD_BRANCHES[@]}"; do
  if ! git show-ref --verify --quiet "refs/remotes/origin/$b"; then
    echo "GONE (already deleted): $b"; gone=$((gone+1)); continue
  fi
  if git merge-base --is-ancestor "origin/$b" origin/main 2>/dev/null; then
    verdict="merged"
  elif [ "$(git cherry origin/main "origin/$b" | grep -c '^+')" = "0" ]; then
    verdict="patch-equivalent"
  else
    echo "SKIP (no longer verified dead — do NOT delete): $b" >&2
    skipped=$((skipped+1)); continue
  fi
  if [ "$RUN" = "1" ]; then
    git push origin --delete "$b" && { echo "DELETED ($verdict): $b"; deleted=$((deleted+1)); } \
      || { echo "FAILED to delete: $b" >&2; skipped=$((skipped+1)); }
  else
    echo "would delete ($verdict): $b"; deleted=$((deleted+1))
  fi
done

for pair in "${SUPERSEDED_BRANCHES[@]}"; do
  b="${pair%% *}"; pinned_sha="${pair##* }"
  if ! git show-ref --verify --quiet "refs/remotes/origin/$b"; then
    echo "GONE (already deleted): $b"; gone=$((gone+1)); continue
  fi
  current_sha="$(git rev-parse "origin/$b" | cut -c1-8)"
  if [ "$current_sha" != "$pinned_sha" ]; then
    echo "SKIP (moved since harvest — pinned $pinned_sha, now $current_sha): $b" >&2
    skipped=$((skipped+1)); continue
  fi
  if [ "$RUN" = "1" ]; then
    git push origin --delete "$b" && { echo "DELETED (superseded, harvested): $b"; deleted=$((deleted+1)); } \
      || { echo "FAILED to delete: $b" >&2; skipped=$((skipped+1)); }
  else
    echo "would delete (superseded, harvested): $b"; deleted=$((deleted+1))
  fi
done

echo
[ "$RUN" = "1" ] || echo "DRY-RUN — re-run with --run to delete."
echo "deleted:$deleted skipped:$skipped already-gone:$gone"
