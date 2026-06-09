/* Kudbee Lab — self-contained SVG charts (no external libs; CSP-safe).
   Renders the REAL backtest data in window.KUDBEE_LAB into interactive charts. */
(function () {
  "use strict";
  var D = window.KUDBEE_LAB;
  if (!D) return;
  var NS = "http://www.w3.org/2000/svg";
  var C = { honey: "#F5A623", honeyLt: "#FFD45E", mint: "#2DD4BF", red: "#F45B69",
            blue: "#5B8DEF", text: "#EAF0FA", muted: "#9AA6BC", grid: "rgba(255,255,255,.08)" };

  function el(tag, attrs) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  }
  function svg(w, h) {
    // Responsive: viewBox + width:100% + height:auto scales the chart
    // PROPORTIONALLY to the container (no fixed-height letterboxing on phones).
    var s = el("svg", { viewBox: "0 0 " + w + " " + h, width: "100%",
      preserveAspectRatio: "xMidYMid meet", role: "img",
      style: "width:100%;height:auto;max-width:100%;display:block" });
    return s;
  }
  function txt(x, y, s, opts) {
    opts = opts || {};
    var t = el("text", { x: x, y: y, fill: opts.fill || C.muted,
      "font-size": opts.size || 12, "font-family": "JetBrains Mono, monospace",
      "text-anchor": opts.anchor || "start" });
    t.textContent = s;
    return t;
  }

  /* ---- Equity line chart (log scale; the 300-trade $100 sizing story) ---- */
  function equityChart(host) {
    var eq = D.equity, W = 720, H = 380, padL = 56, padR = 130, padT = 20, padB = 34;
    var s = svg(W, H);
    var names = Object.keys(eq.curves);
    var maxLen = 0, maxV = 1, minV = 1e9;
    names.forEach(function (n) {
      var c = eq.curves[n].curve; maxLen = Math.max(maxLen, c.length);
      c.forEach(function (v) { maxV = Math.max(maxV, v); minV = Math.min(minV, Math.max(v, 1)); });
    });
    var loMin = Math.max(1, Math.min(minV, 1)); // floor at $1 for log
    var lo = Math.log10(loMin), hi = Math.log10(maxV * 1.15);
    function X(i, len) { return padL + (W - padL - padR) * (i / (len - 1)); }
    function Y(v) { return padT + (H - padT - padB) * (1 - (Math.log10(Math.max(v, 1)) - lo) / (hi - lo)); }
    // gridlines at $1,10,100,1k,10k
    [1, 10, 100, 1000, 10000].forEach(function (g) {
      if (g < loMin || g > maxV * 1.15) return;
      var y = Y(g);
      s.appendChild(el("line", { x1: padL, y1: y, x2: W - padR, y2: y, stroke: C.grid }));
      s.appendChild(txt(padL - 8, y + 3, "$" + (g >= 1000 ? g / 1000 + "k" : g), { anchor: "end" }));
    });
    // $100 start reference
    var y100 = Y(100);
    s.appendChild(el("line", { x1: padL, y1: y100, x2: W - padR, y2: y100,
      stroke: C.muted, "stroke-dasharray": "2 4", "stroke-width": 1 }));
    var palette = { "10x full notional": C.red, "10% risk / trade": C.honey,
      "2% risk / trade": C.mint, "1% risk / trade": C.blue };
    var legendY = padT + 6;
    names.forEach(function (n) {
      var c = eq.curves[n].curve, col = palette[n] || C.text, d = "";
      c.forEach(function (v, i) { d += (i ? "L" : "M") + X(i, c.length).toFixed(1) + " " + Y(v).toFixed(1) + " "; });
      s.appendChild(el("path", { d: d, fill: "none", stroke: col, "stroke-width": 2,
        "stroke-linejoin": "round", opacity: eq.curves[n].ruined ? 0.85 : 1 }));
      // end marker + label
      var info = eq.curves[n];
      var lx = W - padR + 8;
      s.appendChild(el("circle", { cx: X(c.length - 1, c.length), cy: Y(c[c.length - 1]),
        r: 3, fill: col }));
      s.appendChild(txt(lx, legendY, n, { fill: col, size: 11.5 }));
      s.appendChild(txt(lx, legendY + 14, (info.ruined ? "BLOWN  " : "$" + info.final.toLocaleString()) +
        "  " + (info.ret >= 0 ? "+" : "") + info.ret + "%", { fill: info.ruined ? C.red : C.text, size: 11 }));
      legendY += 38;
    });
    s.appendChild(txt(padL, H - 8, "trade # (most recent 300)", { fill: C.muted }));
    host.appendChild(s);
  }

  /* ---- Survival curve: P(reach X R) — TP1 vs TP2 ---- */
  function survivalChart(host) {
    var W = 720, H = 340, padL = 46, padR = 24, padT = 18, padB = 40;
    var s = svg(W, H);
    var series = [["crypto", D.survival.crypto, C.honey], ["stocks", D.survival.stocks, C.mint]];
    var xs = D.survival.crypto.pts.map(function (p) { return p[0]; });
    var xmin = xs[0], xmax = xs[xs.length - 1];
    function X(r) { return padL + (W - padL - padR) * ((r - xmin) / (xmax - xmin)); }
    function Y(p) { return padT + (H - padT - padB) * (1 - p / 100); }
    [0, 25, 50, 75, 100].forEach(function (g) {
      var y = Y(g);
      s.appendChild(el("line", { x1: padL, y1: y, x2: W - padR, y2: y, stroke: C.grid }));
      s.appendChild(txt(padL - 8, y + 3, g + "%", { anchor: "end" }));
    });
    xs.forEach(function (r) { s.appendChild(txt(X(r), H - 16, r + "R", { anchor: "middle" })); });
    // highlight TP1 (1.5R) and TP2 (3R)
    [[1.5, "TP1"], [3, "TP2"]].forEach(function (m) {
      s.appendChild(el("line", { x1: X(m[0]), y1: padT, x2: X(m[0]), y2: H - padB,
        stroke: C.muted, "stroke-dasharray": "2 4" }));
      s.appendChild(txt(X(m[0]), padT - 4, m[1], { anchor: "middle", fill: C.muted, size: 10 }));
    });
    series.forEach(function (ser) {
      var pts = ser[1].pts, col = ser[2], d = "";
      pts.forEach(function (p, i) { d += (i ? "L" : "M") + X(p[0]).toFixed(1) + " " + Y(p[1]).toFixed(1) + " "; });
      s.appendChild(el("path", { d: d, fill: "none", stroke: col, "stroke-width": 2.5, "stroke-linejoin": "round" }));
      pts.forEach(function (p) { s.appendChild(el("circle", { cx: X(p[0]), cy: Y(p[1]), r: 2.6, fill: col })); });
    });
    // legend
    series.forEach(function (ser, i) {
      var lx = W - padR - 120, ly = padT + 6 + i * 16;
      s.appendChild(el("rect", { x: lx, y: ly - 8, width: 10, height: 10, fill: ser[2], rx: 2 }));
      s.appendChild(txt(lx + 16, ly, ser[0] + " (n=" + ser[1].n + ")", { fill: C.text, size: 11 }));
    });
    host.appendChild(s);
  }

  /* ---- Expectancy by fee: grouped bars ---- */
  function feeChart(host) {
    var W = 720, H = 320, padL = 52, padR = 20, padT = 20, padB = 46;
    var s = svg(W, H);
    var fees = Object.keys(D.expfee.crypto);
    var groups = [["crypto", C.honey], ["stocks", C.mint]];
    var vals = [];
    fees.forEach(function (f) { groups.forEach(function (g) { vals.push(D.expfee[g[0]][f]); }); });
    var vmax = Math.max(0.25, Math.max.apply(null, vals));
    var vmin = Math.min(0, Math.min.apply(null, vals));
    function Y(v) { return padT + (H - padT - padB) * (1 - (v - vmin) / (vmax - vmin)); }
    var zeroY = Y(0);
    s.appendChild(el("line", { x1: padL, y1: zeroY, x2: W - padR, y2: zeroY, stroke: C.border2 || "rgba(255,255,255,.2)" }));
    [vmin, 0, 0.1, 0.2].forEach(function (g) {
      if (g < vmin - 1e-9 || g > vmax + 1e-9) return;
      var y = Y(g);
      s.appendChild(txt(padL - 8, y + 3, (g > 0 ? "+" : "") + g.toFixed(2) + "R", { anchor: "end" }));
    });
    var gw = (W - padL - padR) / fees.length;
    fees.forEach(function (f, i) {
      var x0 = padL + i * gw;
      s.appendChild(txt(x0 + gw / 2, H - 22, f, { anchor: "middle", fill: C.text, size: 11 }));
      groups.forEach(function (g, j) {
        var v = D.expfee[g[0]][f], bw = gw * 0.30, bx = x0 + gw * 0.18 + j * (bw + 6);
        var yTop = Math.min(Y(v), zeroY), hgt = Math.abs(Y(v) - zeroY);
        s.appendChild(el("rect", { x: bx, y: yTop, width: bw, height: Math.max(1, hgt),
          fill: v < 0 ? C.red : g[1], rx: 3, opacity: v < 0 ? 0.85 : 1 }));
        s.appendChild(txt(bx + bw / 2, yTop - 4, (v > 0 ? "+" : "") + v.toFixed(2),
          { anchor: "middle", fill: v < 0 ? C.red : C.text, size: 9.5 }));
      });
    });
    s.appendChild(txt(padL, H - 6, "round-trip fee  →  taker (0.20%) nearly kills the edge",
      { fill: C.muted, size: 10.5 }));
    // legend
    groups.forEach(function (g, i) {
      var lx = padL + 4 + i * 90, ly = padT + 4;
      s.appendChild(el("rect", { x: lx, y: ly - 8, width: 10, height: 10, fill: g[1], rx: 2 }));
      s.appendChild(txt(lx + 15, ly, g[0], { fill: C.text, size: 11 }));
    });
    host.appendChild(s);
  }

  /* ---- Generic multi-curve line chart (used by long/short + forward) ---- */
  function lineCurves(host, curves, opts) {
    opts = opts || {};
    var W = 720, H = 320, padL = 56, padR = 120, padT = 18, padB = 34;
    var s = svg(W, H);
    var allv = [], maxLen = 0;
    curves.forEach(function (c) { maxLen = Math.max(maxLen, c.data.length); c.data.forEach(function (v) { allv.push(v); }); });
    var vmax = Math.max.apply(null, allv), vmin = Math.min.apply(null, allv);
    var base = opts.baseline !== undefined ? opts.baseline : 0;
    if (opts.log) {
      var lo = Math.log10(Math.max(1, vmin)), hi = Math.log10(vmax * 1.12);
    } else {
      var pad = (vmax - vmin) * 0.1 || 1; vmax += pad; vmin -= pad;
    }
    function X(i, len) { return padL + (W - padL - padR) * (i / Math.max(1, len - 1)); }
    function Y(v) {
      if (opts.log) return padT + (H - padT - padB) * (1 - (Math.log10(Math.max(v, 1)) - lo) / (hi - lo));
      return padT + (H - padT - padB) * (1 - (v - vmin) / (vmax - vmin));
    }
    var grid = opts.log ? [1, 10, 100, 1000, 10000].filter(function (g) { return g >= Math.max(1, vmin) && g <= vmax * 1.12; })
                        : [vmin, base, (vmin + vmax) / 2, vmax];
    grid.forEach(function (g) {
      var y = Y(g);
      s.appendChild(el("line", { x1: padL, y1: y, x2: W - padR, y2: y, stroke: C.grid }));
      var lbl = opts.log ? "$" + (g >= 1000 ? g / 1000 + "k" : g) : (opts.money ? "$" + Math.round(g) : (g > 0 ? "+" : "") + g.toFixed(1) + "R");
      s.appendChild(txt(padL - 8, y + 3, lbl, { anchor: "end" }));
    });
    if (!opts.log) { var yb = Y(base); s.appendChild(el("line", { x1: padL, y1: yb, x2: W - padR, y2: yb, stroke: C.muted, "stroke-dasharray": "2 4" })); }
    var ly = padT + 6;
    curves.forEach(function (c) {
      var d = "";
      c.data.forEach(function (v, i) { d += (i ? "L" : "M") + X(i, c.data.length).toFixed(1) + " " + Y(v).toFixed(1) + " "; });
      s.appendChild(el("path", { d: d, fill: "none", stroke: c.color, "stroke-width": 2.2, "stroke-linejoin": "round" }));
      s.appendChild(el("circle", { cx: X(c.data.length - 1, c.data.length), cy: Y(c.data[c.data.length - 1]), r: 3, fill: c.color }));
      s.appendChild(txt(W - padR + 8, ly, c.name, { fill: c.color, size: 11.5 }));
      if (c.sub) s.appendChild(txt(W - padR + 8, ly + 13, c.sub, { fill: C.text, size: 10.5 }));
      ly += c.sub ? 32 : 18;
    });
    if (opts.xLabel) s.appendChild(txt(padL, H - 8, opts.xLabel, { fill: C.muted }));
    host.appendChild(s);
  }

  function longShortChart(host) {
    var ls = D.longshort, cv = ls.curves;
    lineCurves(host, [
      { name: "BOTH", data: cv.both, color: C.honey, sub: "$" + Math.round(cv.both[cv.both.length - 1]) },
      { name: "SHORT", data: cv.short, color: C.red, sub: "$" + Math.round(cv.short[cv.short.length - 1]) },
      { name: "LONG", data: cv.long, color: C.mint, sub: "$" + Math.round(cv.long[cv.long.length - 1]) }
    ], { log: true, xLabel: "trades (chronological, $100 @ 1% risk)" });
  }

  /* ---- Venue fee widget: interpolate expectancy from the measured fee curve ---- */
  function expAtFee(group, rt) {
    var pts = [[0, D.expfee[group]["0%"]], [0.0002, D.expfee[group]["0.02%"]],
               [0.0004, D.expfee[group]["0.04%"]], [0.0020, D.expfee[group]["0.20%"]]];
    for (var i = 0; i < pts.length - 1; i++) {
      if (rt <= pts[i + 1][0]) {
        var t = (rt - pts[i][0]) / (pts[i + 1][0] - pts[i][0]);
        return pts[i][1] + t * (pts[i + 1][1] - pts[i][1]);
      }
    }
    return pts[pts.length - 1][1];
  }
  function venueWidget() {
    var sel = document.getElementById("venue-sel"), out = document.getElementById("venue-out");
    if (!sel || !out || !D.venues) return;
    sel.innerHTML = D.venues.map(function (v, i) {
      return '<option value="' + i + '">' + v.name + " — " + (v.rt * 100).toFixed(3) + "% rt</option>";
    }).join("");
    function render() {
      var v = D.venues[parseInt(sel.value, 10) || 0];
      var ec = expAtFee("crypto", v.rt), es = expAtFee("stocks", v.rt);
      function box(lbl, val) {
        var cls = val > 0.05 ? "co--good" : (val > 0 ? "co--warn" : "co--bad");
        return calcBox(lbl, (val > 0 ? "+" : "") + val.toFixed(3) + "R", cls);
      }
      out.innerHTML = box("crypto expectancy / trade", ec) + box("stocks expectancy / trade", es) +
        calcBox("round-trip maker cost", (v.rt * 100).toFixed(3) + "%", v.rt <= 0.0005 ? "co--good" : "co--warn");
    }
    sel.addEventListener("change", render); render();
  }

  /* ---- Live forward track record (resolved trades) + bot vs human ---- */
  function loadForward() {
    var status = document.getElementById("fwd-status"), host = document.getElementById("chart-forward");
    if (!host) return;
    var API = (window.KUDBEE_API_BASE || "") + "/api";
    fetch(API + "/journal").then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (j) {
      var bs = (j.by_source || {});
      function srcTxt(o) { return (o && o.n) ? ((o.expectancy_r >= 0 ? "+" : "") + o.expectancy_r.toFixed(3) + "R (n=" + o.n + ")") : "no data yet"; }
      setText("src-bot", srcTxt(bs.bot)); setText("src-human", srcTxt(bs.human));
      var ser = j.resolved_series || [];
      if (ser.length < 2) { status.textContent = "Only " + ser.length + " resolved trade(s) so far — the curve fills in as trades close."; host.innerHTML = ""; return; }
      var eq = [0], cum = 0;
      ser.forEach(function (t) { cum += t.r; eq.push(cum); });
      host.innerHTML = "";
      lineCurves(host, [{ name: "cumulative R", data: eq, color: C.honey, sub: (cum >= 0 ? "+" : "") + cum.toFixed(1) + "R" }],
        { baseline: 0, xLabel: "resolved trade #" });
      status.textContent = "Live · " + ser.length + " resolved trades · updated " + new Date().toLocaleTimeString();
    }).catch(function () {
      status.textContent = "Engine offline — your live forward record appears when the API is running. The backtests above are the prior; this becomes the posterior.";
      host.innerHTML = "";
    });
  }

  function fill(id, fn) { var h = document.getElementById(id); if (h) try { fn(h); } catch (e) { h.textContent = "chart error"; } }
  function setText(id, v) { var e = document.getElementById(id); if (e) e.textContent = v; }

  /* ---- Position-size / risk calculator (pure client-side; always works) ---- */
  function calcBox(label, value, cls) {
    return '<div class="co ' + (cls || "") + '"><div class="co__v">' + value +
      '</div><div class="co__l">' + label + '</div></div>';
  }
  function runCalc() {
    var out = document.getElementById("calc-out");
    if (!out) return;
    var acct = parseFloat((document.getElementById("c-acct") || {}).value) || 0;
    var risk = parseFloat((document.getElementById("c-risk") || {}).value) || 0;
    var stop = parseFloat((document.getElementById("c-stop") || {}).value) || 0;
    if (acct <= 0 || risk <= 0 || stop <= 0) { out.innerHTML = "<p class='co__l'>Enter positive numbers.</p>"; return; }
    var dollarRisk = acct * (risk / 100);
    var notional = dollarRisk / (stop / 100);
    var lev = notional / acct;
    var levCls = lev <= 1.01 ? "co--good" : (lev <= 1.5 ? "co--warn" : "co--bad");
    var riskCls = risk <= 1.01 ? "co--good" : (risk <= 2.01 ? "co--warn" : "co--bad");
    var levTxt = lev <= 1.01 ? " (no leverage)" : "";
    out.innerHTML =
      calcBox("dollars at risk if stopped", "$" + dollarRisk.toLocaleString(undefined, { maximumFractionDigits: 2 }), riskCls) +
      calcBox("position size (notional)", "$" + notional.toLocaleString(undefined, { maximumFractionDigits: 0 }), "") +
      calcBox("leverage needed" + levTxt, lev.toFixed(2) + "×", levCls) +
      calcBox("a 3R winner makes", "$" + (dollarRisk * 3).toLocaleString(undefined, { maximumFractionDigits: 2 }), "co--good");
  }

  /* ---- Live book exposure (same-origin API; graceful fallback) ---- */
  function loadExposure() {
    var status = document.getElementById("exp-status");
    var host = document.getElementById("exp-table");
    if (!host) return;
    var API = (window.KUDBEE_API_BASE || "") + "/api";
    fetch(API + "/journal").then(function (r) {
      if (!r.ok) throw new Error(r.status); return r.json();
    }).then(function (j) {
      var ex = j.exposure || [];
      if (!ex.length) { status.textContent = "No open risk right now — flat book."; host.innerHTML = ""; return; }
      var cap = 2; // % gross cap per coin (matches the engine default)
      var rows = ex.map(function (e) {
        var pctW = Math.min(100, (e.gross_risk_pct / (cap * 1.5)) * 100);
        var col = e.gross_risk_pct > cap ? C.red : (e.gross_risk_pct >= cap ? C.honey : C.mint);
        var dir = e.net_direction > 0 ? "net long" : (e.net_direction < 0 ? "net short" : "flat");
        return '<div class="exp-row"><span class="exp-sym">' + e.symbol + '</span>' +
          '<span class="exp-bar"><i style="width:' + pctW.toFixed(0) + '%;background:' + col + '"></i></span>' +
          '<span class="exp-amt">' + e.gross_risk_pct.toFixed(0) + '% <span style="color:#6A7488">' + dir + '</span></span></div>';
      }).join("");
      host.innerHTML = rows;
      status.textContent = "Live · " + (j.total_gross_risk_pct || 0) + "% whole-book gross risk · cap " +
        cap + "%/coin · updated " + new Date().toLocaleTimeString();
    }).catch(function (e) {
      status.textContent = "Engine offline — exposure shows when the API is running " +
        "(uvicorn kudbee_quant.api:app). Your two-sided risk guard still runs in the bot.";
      host.innerHTML = "";
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    fill("chart-equity", equityChart);
    fill("chart-survival", survivalChart);
    fill("chart-fee", feeChart);
    fill("chart-longshort", longShortChart);
    if (D.longshort) {
      var ls = D.longshort;
      setText("ls-long", "+" + ls.long.exp + "R");
      setText("ls-short", "+" + ls.short.exp + "R");
      setText("ls-both", "+" + ls.both.exp + "R");
    }
    venueWidget();
    loadForward();
    var sm = D.equity.sample;
    setText("stat-exp", (sm.exp >= 0 ? "+" : "") + sm.exp + "R");
    setText("stat-win", sm.win + "%");
    setText("stat-stop", sm.stop + "%");
    setText("stat-n", sm.n);
    setText("stat-pattern", "+" + D.pattern.mean + "R");
    setText("stat-pattern-pos", D.pattern.pos + "%");
    setText("stat-assets", D.assets.crypto + " crypto + " + D.assets.stocks + " stocks");
    setText("gen-date", D.generated);
    // Interactive position-size calculator.
    ["c-acct", "c-risk", "c-stop"].forEach(function (id) {
      var e = document.getElementById(id);
      if (e) e.addEventListener("input", runCalc);
    });
    runCalc();
    // Live book exposure (graceful fallback if the engine API is offline).
    loadExposure();
  });
})();
