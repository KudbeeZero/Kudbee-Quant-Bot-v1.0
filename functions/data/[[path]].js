// Cloudflare Pages Function — block public access to the repo's `data/` tree.
//
// WHY: Pages publishes the repo root (`publish = "."`), which otherwise serves
// `data/journal.json` and friends as static files. The raw journal exposes the
// exact entry/stop/target levels on OPEN positions — the precise stop-hunt /
// front-running vector that `/api/journal` deliberately strips (kudbee_quant/
// api.py). Backtest matrices, heartbeat, and research ledgers are internal too.
// A Pages Function shadows the static asset for its route, so this 404s every
// `/data/*` request at the edge. The website only ever calls `/api/*` (proxied,
// privacy-stripped), so nothing legitimate needs the raw files.
export function onRequest() {
  return new Response("Not found", {
    status: 404,
    headers: { "content-type": "text/plain; charset=utf-8", "x-content-type-options": "nosniff" },
  });
}
