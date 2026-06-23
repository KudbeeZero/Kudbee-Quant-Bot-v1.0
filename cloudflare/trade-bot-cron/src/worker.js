/**
 * Kudbee trade-bot cron — a RELIABLE external trigger for the paper-trade workflow(s).
 *
 * GitHub Actions' own `schedule:` cron is best-effort and silently drops/delays many
 * runs, so Telegram alerts go missing. Cloudflare Cron Triggers are reliable, so this
 * Worker fires the GitHub workflow(s) every hour via the REST API (`workflow_dispatch`),
 * guaranteeing the scan + Telegram pings actually run.
 *
 * Two reliability features beyond a bare trigger:
 *  1. DISPATCH-FAILURE ALERT — if GitHub does not return 204 (e.g. the GH_TOKEN expired
 *     or lost its Actions permission → 401/403), the Worker sends a Telegram message so
 *     the failure SCREAMS instead of going silent (the exact failure mode this exists to
 *     prevent). Gated on TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID; a silent no-op if unset.
 *     NOTE: this catches dispatch failures only. It canNOT report the Worker itself never
 *     firing (Cloudflare outage, billing, dead isolate) — a dead-man's-switch (an external
 *     "ping me if you DON'T hear from the cron") is the stronger pattern, deliberately
 *     deferred here.
 *  2. MULTI-WORKFLOW BACKSTOP — dispatches every workflow in WORKFLOW_FILES (comma-list),
 *     so e.g. the read-only `paper-status.yml` reminder also gets a reliable nudge and not
 *     just `paper-trade.yml`. Back-compat: falls back to WORKFLOW_FILE, then paper-trade.yml.
 *
 * Setup: see ../README.md (add the GH_TOKEN secret, optionally TELEGRAM_*, then `wrangler deploy`).
 */

// Workflows to dispatch each tick. WORKFLOW_FILES (comma-separated) wins; WORKFLOW_FILE
// is kept for back-compat; default is the validated paper-trade workflow.
function workflowsOf(env) {
  const raw = env.WORKFLOW_FILES || env.WORKFLOW_FILE || "paper-trade.yml";
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

async function dispatchOne(env, workflow) {
  const owner = env.GH_OWNER;
  const repo = env.GH_REPO;
  const ref = env.GH_REF || "main";
  const url = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GH_TOKEN}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "kudbee-trade-bot-cron",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify({ ref }),
  });
  // GitHub returns 204 No Content on a successful dispatch.
  const ok = res.status === 204;
  return {
    workflow,
    ok,
    status: res.status,
    detail: ok
      ? `OK: dispatched ${workflow}@${ref}`
      : `ERROR ${workflow} ${res.status}: ${await res.text()}`,
  };
}

// Best-effort Telegram alert on dispatch failure. Silent no-op when creds are unset;
// wrapped so a notification problem can NEVER break (or fail) the dispatch path. The GH
// token is never included in the message.
async function notifyFailure(env, failures) {
  const token = env.TELEGRAM_BOT_TOKEN;
  const chat = env.TELEGRAM_CHAT_ID;
  if (!token || !chat || failures.length === 0) return;
  const lines = failures.map((f) => `• ${f.detail}`).join("\n");
  const text =
    `🚨 kudbee-trade-bot-cron: workflow dispatch FAILED\n${lines}\n\n` +
    `The trigger could not fire — paper-trade / Telegram pings may go silent. ` +
    `Check the Worker's GH_TOKEN (expired or wrong permissions?) and the workflow's ` +
    `Actions: Read+write access. 401 = bad/stale token, 403 = missing permission.`;
  try {
    await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chat, text, disable_web_page_preview: true }),
    });
  } catch (_err) {
    // Swallow: an alert failure must not affect the dispatch result.
  }
}

async function dispatch(env) {
  if (!env.GH_TOKEN) return "ERROR: GH_TOKEN secret not set";
  const results = [];
  for (const workflow of workflowsOf(env)) {
    try {
      results.push(await dispatchOne(env, workflow));
    } catch (err) {
      results.push({ workflow, ok: false, status: 0, detail: `ERROR dispatching ${workflow}: ${err}` });
    }
  }
  const failures = results.filter((r) => !r.ok);
  // Awaited here (not fire-and-forget) so the scheduled handler's waitUntil() keeps the
  // isolate alive until the alert has actually been sent.
  if (failures.length) await notifyFailure(env, failures);
  return results.map((r) => r.detail).join("\n");
}

export default {
  // Fired by the Cron Trigger(s) in wrangler.toml.
  async scheduled(event, env, ctx) {
    ctx.waitUntil(dispatch(env));
  },
  // Hitting the Worker URL manually triggers a run too (handy health-check).
  async fetch(request, env) {
    const msg = await dispatch(env);
    // 200 only if EVERY workflow dispatched OK; 500 if any failed.
    const allOk = msg.split("\n").every((line) => line.startsWith("OK"));
    return new Response(msg + "\n", { status: allOk ? 200 : 500 });
  },
};
