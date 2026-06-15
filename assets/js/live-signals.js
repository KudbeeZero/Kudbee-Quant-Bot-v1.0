/* Live Signals — calls the Kudbee Quant backend API (same-origin /api,
   proxied by Netlify to the FastAPI engine). CSP-compliant (external file,
   same-origin fetch). Honest: shows the engine's directional read, not advice. */
(function () {
  "use strict";
  var WATCHLIST = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"];
  var API = (window.KUDBEE_API_BASE || "") + "/api";

  function fmt(n) { return (n === null || n === undefined) ? "—" : Number(n).toLocaleString(undefined, { maximumFractionDigits: 4 }); }
  function pct(n) { return (n * 100).toFixed(0) + "%"; }

  function card(s) {
    var el = document.createElement("div");
    el.className = "signal-card";
    var dir = s.side === "long" ? "up" : (s.side === "short" ? "down" : "flat");
    var b = s.bracket;
    el.innerHTML =
      '<div class="signal-card__head">' +
        '<span class="signal-card__sym">' + s.symbol + '</span>' +
        '<span class="signal-card__price">' + fmt(s.price) + '</span>' +
      '</div>' +
      '<div class="signal-card__row"><span>Confluence</span><strong>' + pct(s.confluence_pct) +
        ' (' + s.strength + '/' + s.n_factors + ')</strong></div>' +
      '<div class="signal-card__row"><span>Direction</span><strong class="dir dir--' + dir + '">' +
        s.side.toUpperCase() + '</strong></div>' +
      '<div class="signal-card__row"><span>Actionable (≥50%)</span><strong>' +
        (s.actionable ? "YES" : "no") + '</strong></div>' +
      (b ? '<div class="signal-card__bracket">' +
        '<div><span>Limit entry</span><strong>' + fmt(b.entry_limit) + '</strong></div>' +
        '<div><span>Stop</span><strong>' + fmt(b.stop) + '</strong></div>' +
        '<div><span>Target (' + b.target_r + 'R)</span><strong>' + fmt(b.target) + '</strong></div>' +
        '</div>' : '<div class="signal-card__row signal-card__muted">No setup at ≥50% confluence right now.</div>');
    return el;
  }

  function load() {
    var grid = document.getElementById("signals-grid");
    var status = document.getElementById("signals-status");
    if (!grid) return;
    grid.innerHTML = "";
    status.textContent = "Loading live signals…";
    Promise.all(WATCHLIST.map(function (sym) {
      return fetch(API + "/signal/" + sym).then(function (r) {
        if (!r.ok) throw new Error(sym + ": " + r.status);
        return r.json();
      });
    })).then(function (results) {
      results.forEach(function (s) { grid.appendChild(card(s)); });
      status.textContent = "Updated " + new Date().toLocaleTimeString() +
        " · 1h · validated config (3R, 0.25-ATR limit retrace, maker).";
    }).catch(function (e) {
      status.textContent = "Live signals are offline right now — the engine isn't reachable. Please check back soon.";
      if (window.console && console.warn) {
        console.warn("Kudbee live-signals: backend error (" + e.message +
          "). Run the engine locally with: uvicorn kudbee_quant.api:app");
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    load();
    var btn = document.getElementById("signals-refresh");
    if (btn) btn.addEventListener("click", load);
  });
})();
