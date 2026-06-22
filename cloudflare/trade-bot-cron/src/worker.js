/**
 * Kudbee trade-bot cron — a RELIABLE external trigger for the paper-trade workflow.
 *
 * GitHub Actions' own `schedule:` cron is best-effort and silently drops/delays many
 * runs, so Telegram alerts go missing. Cloudflare Cron Triggers are reliable, so this
 * Worker fires the GitHub workflow every hour via the REST API (`workflow_dispatch`),
 * guaranteeing the scan + Telegram pings actually run.
 *
 * Setup: see ../README.md (add the GH_TOKEN secret, then `wrangler deploy`).
 */

async function dispatch(env) {
  const owner = env.GH_OWNER;
  const repo = env.GH_REPO;
  const workflow = env.WORKFLOW_FILE || "paper-trade.yml";
  const ref = env.GH_REF || "main";
  if (!env.GH_TOKEN) return "ERROR: GH_TOKEN secret not set";

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
  return res.status === 204
    ? `OK: dispatched ${workflow}@${ref}`
    : `ERROR ${res.status}: ${await res.text()}`;
}

export default {
  // Fired by the Cron Trigger(s) in wrangler.toml.
  async scheduled(event, env, ctx) {
    ctx.waitUntil(dispatch(env));
  },
  // Hitting the Worker URL manually triggers a run too (handy health-check).
  async fetch(request, env) {
    const msg = await dispatch(env);
    return new Response(msg + "\n", { status: msg.startsWith("OK") ? 200 : 500 });
  },
};
