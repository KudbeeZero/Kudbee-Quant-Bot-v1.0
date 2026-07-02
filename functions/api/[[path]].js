// Cloudflare Pages Function — same-origin proxy for /api/* → the FastAPI engine.
//
// WHY THIS EXISTS: the static site calls same-origin `/api/*` on purpose so the
// CSP can stay tight (`connect-src 'self'`). On Netlify that rewrite lives in
// `netlify.toml`. The site is deployed on **Cloudflare Pages**, which does NOT
// read `netlify.toml`, so without this Function every `/api/*` call 404s and the
// dynamic pages (Live Signals, Trade Flow, Lab) go dark. This ports the same
// intent to Pages. Verified live in `docs/wiring-verification-2026-07-02.md`.
//
// The upstream defaults to the Render service and can be overridden per
// environment with the `API_ORIGIN` Pages variable (Settings → Environment
// variables) — no code change needed if the Render subdomain ever changes.
//
// NOTE: this only carries traffic once the Render service is actually deployed
// (until then Render answers `x-render-routing: no-server` and this proxies a 404).

const DEFAULT_ORIGIN = "https://kudbee-quant-api.onrender.com";

export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const origin = (env.API_ORIGIN || DEFAULT_ORIGIN).replace(/\/+$/, "");

  // url.pathname already includes the `/api/...` prefix — forward it verbatim.
  const target = origin + url.pathname + url.search;

  const method = request.method.toUpperCase();
  const init = {
    method,
    headers: request.headers,
    redirect: "manual",
  };
  // Buffer the body for methods that carry one (small JSON payloads) — avoids the
  // streaming-body `duplex` requirement and keeps the proxy simple + robust.
  if (method !== "GET" && method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  const upstream = await fetch(target, init);

  // Pass the response through unchanged (same-origin, so no CORS to add).
  const headers = new Headers(upstream.headers);
  headers.delete("transfer-encoding");
  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers,
  });
}
