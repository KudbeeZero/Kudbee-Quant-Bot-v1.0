/* Trade Flow — node-graph confluence visualizer.
   Live flow / UNVALIDATED sandbox / journal-trade replay, all from the same
   renderer. Vanilla JS, no libs, CSP-compliant (external file, same-origin
   fetch). Drag uses Pointer Events so mouse and touch share one path.
   Honest by construction: the sandbox is display-only and labelled; replay
   shows the API's recompute caveat verbatim. */
(function () {
  "use strict";

  var API = (window.KUDBEE_API_BASE || "") + "/api";

  var WATCHLIST = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
    "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "yahoo:GC=F", "yahoo:SI=F", "yahoo:HG=F", "yahoo:PL=F", "yahoo:PA=F",
    "yahoo:^GSPC", "yahoo:^NDX", "yahoo:^DJI",
    "yahoo:CL=F", "yahoo:BZ=F", "yahoo:NG=F",
    "yahoo:ZW=F", "yahoo:ZC=F", "yahoo:ZS=F", "yahoo:ZN=F", "yahoo:ZB=F",
    "yahoo:SB=F", "yahoo:KC=F", "yahoo:CC=F",
    "yahoo:EURUSD=X", "yahoo:GBPUSD=X",
  ];

  var FACTORS = [
    { key: "v_emastack", label: "EMA Stack 50/800" },
    { key: "v_emafast", label: "EMA Momentum 13/50" },
    { key: "v_cloud", label: "EMA Cloud 13–50" },
    { key: "v_vwap", label: "Session VWAP" },
    { key: "v_dopen", label: "Daily Open" },
    { key: "v_pivot", label: "Floor Pivot" },
    { key: "v_pd", label: "Premium / Discount" },
    { key: "v_sweep", label: "Liquidity Sweep" },
    { key: "v_vector", label: "PVSRA Vector" },
    { key: "v_fvg", label: "Fair Value Gap" },
  ];

  var state = {
    tab: "live",                 // live | sandbox | replay
    symbol: "BTCUSDT",
    interval: "1h",
    bars: [],                    // trace rows (oldest -> newest)
    barIndex: -1,                // -1 = newest
    bracket: null,               // live bracket from /api/trace
    minPct: 0.5,                 // gate threshold shown on the gate node
    gate: null,                  // sandbox gate echo
    disabled: {},                // sandbox: key -> true
    events: {},                  // replay: barIndex(str) -> [labels]
    trade: null,                 // replay: trade meta
    caveat: "",
    playing: null,               // replay play timer
  };

  var $ = function (id) { return document.getElementById(id); };
  var canvas, edgesSvg, positions = {}, dragging = null;

  function fmt(n) {
    return (n === null || n === undefined) ? "—"
      : Number(n).toLocaleString(undefined, { maximumFractionDigits: 4 });
  }
  function pct(x) { return Math.round(x * 100) + "%"; }

  // --- layout -----------------------------------------------------------------

  function defaultLayout() {
    var w = canvas.clientWidth, h = canvas.clientHeight;
    var narrow = w < 760;
    var nodeW = 190, colGap = narrow ? 6 : 24;
    var col1 = narrow ? 10 : Math.max(200, w * 0.2);
    var col2 = col1 + nodeW + colGap;
    var rowH = narrow ? 118 : 128, top = 18;
    positions = { sym: { x: 10, y: h / 2 - 40 } };
    if (narrow) positions.sym = { x: 10, y: 6 };
    for (var i = 0; i < FACTORS.length; i++) {
      var col = i < 5 ? col1 : col2;
      positions[FACTORS[i].key] = { x: col, y: top + (i % 5) * rowH + (narrow ? 90 : 0) };
    }
    positions.gate = { x: Math.min(col2 + nodeW + colGap, w - 380), y: h / 2 - 130 };
    positions.trade = { x: Math.min(col2 + nodeW + colGap + 185, w - 185), y: h / 2 - 20 };
    if (narrow) {
      positions.gate = { x: 10, y: top + 5 * rowH + 100 };
      positions.trade = { x: 200, y: top + 5 * rowH + 100 };
    }
  }

  // --- node DOM ----------------------------------------------------------------

  function nodeEl(id, cls) {
    var el = document.createElement("div");
    el.className = "tf-node " + (cls || "");
    el.dataset.node = id;
    canvas.appendChild(el);
    return el;
  }

  function buildGraph() {
    canvas.querySelectorAll(".tf-node").forEach(function (n) { n.remove(); });
    defaultLayout();
    nodeEl("sym", "tf-node--sym");
    FACTORS.forEach(function (f) { nodeEl(f.key); });
    nodeEl("gate", "tf-node--gate");
    nodeEl("trade", "tf-node--trade");
    canvas.querySelectorAll(".tf-node").forEach(function (n) { place(n); });
  }

  function place(el) {
    var p = positions[el.dataset.node];
    if (p) { el.style.left = p.x + "px"; el.style.top = p.y + "px"; }
  }

  // --- edges --------------------------------------------------------------------

  function edgePath(a, b) {
    var ax = a.x + a.w, ay = a.y + a.h / 2, bx = b.x, by = b.y + b.h / 2;
    var dx = Math.max(40, (bx - ax) / 2);
    return "M" + ax + "," + ay + " C" + (ax + dx) + "," + ay + " " + (bx - dx) + "," + by + " " + bx + "," + by;
  }

  function box(id) {
    var el = canvas.querySelector('[data-node="' + id + '"]');
    if (!el) return null;
    return { x: el.offsetLeft, y: el.offsetTop, w: el.offsetWidth, h: el.offsetHeight };
  }

  function drawEdges() {
    var bar = currentBar();
    var sym = box("sym"), gate = box("gate"), trade = box("trade");
    if (!sym || !gate || !trade) return;
    var html = "";
    FACTORS.forEach(function (f) {
      var fb = box(f.key);
      if (!fb) return;
      var v = voteOf(bar, f.key);
      var off = state.tab === "sandbox" && state.disabled[f.key];
      var color = off ? "#3a3566" : v === null || v === 0 ? "#4a4486"
        : agrees(v, bar) ? "#3ddc84" : "#ff5d5d";
      html += '<path d="' + edgePath(sym, fb) + '" fill="none" stroke="#393273" stroke-width="1.5"/>';
      if (!off) {
        html += '<path d="' + edgePath(fb, gate) + '" fill="none" stroke="' + color +
          '" stroke-width="1.5" opacity="' + (v === 0 || v === null ? 0.35 : 0.9) + '"/>';
      }
    });
    var passed = gatePassed(bar);
    html += '<path d="' + edgePath(gate, trade) + '" fill="none" stroke="' +
      (passed ? "#F5A623" : "#3a3566") + '" stroke-width="2"/>';
    edgesSvg.innerHTML = html;
  }

  // --- render -------------------------------------------------------------------

  function currentBar() {
    if (!state.bars.length) return null;
    var i = state.barIndex < 0 ? state.bars.length - 1 : state.barIndex;
    return state.bars[Math.min(i, state.bars.length - 1)];
  }

  function voteOf(bar, key) {
    if (!bar) return null;
    for (var i = 0; i < bar.factors.length; i++) {
      if (bar.factors[i].key === key) return bar.factors[i].vote;
    }
    return null;   // disabled in sandbox -> not in response
  }

  function detailOf(bar, key) {
    if (!bar) return "";
    for (var i = 0; i < bar.factors.length; i++) {
      if (bar.factors[i].key === key) return bar.factors[i].detail;
    }
    return "dropped from the stack (sandbox)";
  }

  function agrees(v, bar) {
    if (!bar || !v) return false;
    var ref = state.tab === "replay" && state.trade ? state.trade.direction : bar.direction;
    if (!ref) ref = 1;
    return v * ref > 0;
  }

  function gatePassed(bar) {
    if (!bar) return false;
    return bar.confluence_pct >= state.minPct && bar.direction !== 0;
  }

  function sparkline(key) {
    // Votes up to the displayed bar: watch a factor get better/worse over time.
    var end = state.barIndex < 0 ? state.bars.length : state.barIndex + 1;
    var votes = state.bars.slice(Math.max(0, end - 16), end).map(function (b) {
      return voteOf(b, key);
    });
    var cell = 10, w = votes.length * cell, h = 8;
    var html = '<svg class="tf-node__spark" width="' + w + '" height="' + h + '" aria-hidden="true">';
    votes.forEach(function (v, i) {
      var fill = v === null ? "#262150" : v > 0 ? "#3ddc84" : v < 0 ? "#ff5d5d" : "#4a4486";
      html += '<rect x="' + i * cell + '" y="0" width="' + (cell - 2) + '" height="' + h +
        '" rx="2" fill="' + fill + '"/>';
    });
    return html + "</svg>";
  }

  function glyph(v) { return v === null ? "—" : v > 0 ? "▲" : v < 0 ? "▼" : "·"; }

  function render() {
    var bar = currentBar();
    var symEl = canvas.querySelector('[data-node="sym"]');
    if (symEl) {
      symEl.innerHTML = '<div class="tf-node__head"><span class="tf-node__label">' +
        state.symbol + '</span></div><div class="tf-node__detail">' + state.interval +
        (bar ? ' · close ' + fmt(bar.close) + '<br/>' + String(bar.timestamp).slice(0, 16) : "") +
        '</div>';
    }
    FACTORS.forEach(function (f) {
      var el = canvas.querySelector('[data-node="' + f.key + '"]');
      if (!el) return;
      var v = voteOf(bar, f.key);
      var off = state.tab === "sandbox" && state.disabled[f.key];
      el.className = "tf-node " + (off ? "tf-node--off"
        : v === null || v === 0 ? "tf-node--neutral"
          : agrees(v, bar) ? "tf-node--agree" : "tf-node--oppose");
      el.innerHTML = '<div class="tf-node__head"><span class="tf-node__label">' + f.label +
        '</span><span class="tf-node__vote">' + (off ? "off" : glyph(v)) + '</span></div>' +
        '<div class="tf-node__detail">' + (off ? "dragged out of the stack — not scored" : detailOf(bar, f.key)) + '</div>' +
        (off ? "" : sparkline(f.key));
    });
    var gateEl = canvas.querySelector('[data-node="gate"]');
    if (gateEl) {
      var passed = gatePassed(bar);
      gateEl.className = "tf-node tf-node--gate" + (passed ? " tf-node--gate-pass" : "");
      gateEl.innerHTML = '<div class="tf-node__head"><span class="tf-node__label">Confluence gate</span>' +
        '<span class="tf-node__vote">' + (bar ? pct(bar.confluence_pct) : "—") + '</span></div>' +
        '<div class="tf-node__rows">' +
        '<div><span>net</span><strong>' + (bar ? (bar.net_score > 0 ? "+" : "") + bar.net_score : "—") +
        ' / ' + (bar ? bar.n_factors : "—") + '</strong></div>' +
        '<div><span>threshold</span><strong>≥' + pct(state.minPct) + '</strong></div>' +
        '<div><span>state</span><strong>' + (passed ? "PASS" : "no setup") + '</strong></div></div>' +
        (state.tab === "sandbox" ? '<div class="tf-node__detail">UNVALIDATED sandbox gate</div>' : "");
    }
    renderTradeNode(bar);
    drawEdges();
  }

  function renderTradeNode(bar) {
    var el = canvas.querySelector('[data-node="trade"]');
    if (!el) return;
    var html = '<div class="tf-node__head"><span class="tf-node__label">Trade</span></div>';
    if (state.tab === "replay" && state.trade) {
      var t = state.trade;
      var side = t.direction > 0 ? "LONG" : "SHORT";
      html += '<div class="tf-node__rows">' +
        '<div><span>' + side + '</span><strong>' + t.status.toUpperCase() +
        (t.outcome_r !== null && t.outcome_r !== undefined ? " " + (t.outcome_r > 0 ? "+" : "") + t.outcome_r + "R" : "") + '</strong></div>' +
        '<div><span>entry</span><strong>' + fmt(t.entry) + '</strong></div>' +
        '<div><span>stop</span><strong>' + fmt(t.stop) + '</strong></div>' +
        '<div><span>target</span><strong>' + fmt(t.target) + ' (' + t.target_r + 'R)</strong></div></div>';
      var evs = state.events[String(state.barIndex < 0 ? state.bars.length - 1 : state.barIndex)];
      if (evs) html += '<span class="tf-event">' + evs.join(" · ") + '</span>';
    } else if (state.tab === "sandbox") {
      html += '<div class="tf-node__detail">' + (gatePassed(bar)
        ? "sandbox gate passes — for study only; this never places or journals a trade"
        : "no sandbox setup at the chosen gate") + '</div>';
    } else if (state.bracket) {
      html += '<div class="tf-node__rows">' +
        '<div><span>limit entry</span><strong>' + fmt(state.bracket.entry_limit) + '</strong></div>' +
        '<div><span>stop</span><strong>' + fmt(state.bracket.stop) + '</strong></div>' +
        '<div><span>target</span><strong>' + fmt(state.bracket.target) + ' (' + state.bracket.target_r + 'R)</strong></div></div>';
    } else {
      html += '<div class="tf-node__detail">no setup at ≥' + pct(state.minPct) + ' confluence right now</div>';
    }
    el.innerHTML = html;
  }

  // --- drag (Pointer Events: mouse + touch in one path) --------------------------

  function bindDrag() {
    canvas.addEventListener("pointerdown", function (e) {
      var el = e.target.closest(".tf-node");
      if (!el) return;
      dragging = { el: el, dx: e.clientX - el.offsetLeft, dy: e.clientY - el.offsetTop, moved: false };
      el.setPointerCapture(e.pointerId);
    });
    canvas.addEventListener("pointermove", function (e) {
      if (!dragging) return;
      var x = e.clientX - dragging.dx, y = e.clientY - dragging.dy;
      x = Math.max(0, Math.min(x, canvas.clientWidth - dragging.el.offsetWidth));
      y = Math.max(0, Math.min(y, canvas.clientHeight - dragging.el.offsetHeight));
      dragging.el.style.left = x + "px";
      dragging.el.style.top = y + "px";
      dragging.moved = true;
      positions[dragging.el.dataset.node] = { x: x, y: y };
      window.requestAnimationFrame(drawEdges);
    });
    canvas.addEventListener("pointerup", function () {
      if (!dragging) return;
      var el = dragging.el, moved = dragging.moved;
      dragging = null;
      if (!moved || state.tab !== "sandbox") return;
      var key = el.dataset.node;
      if (!FACTORS.some(function (f) { return f.key === key; })) return;
      var shelf = $("tf-shelf");
      var inShelf = el.offsetTop + el.offsetHeight / 2 > shelf.offsetTop;
      if (inShelf && !state.disabled[key]) {
        state.disabled[key] = true;
        scheduleSandbox();
      } else if (!inShelf && state.disabled[key]) {
        delete state.disabled[key];
        scheduleSandbox();
      }
      render();
    });
  }

  // --- API ------------------------------------------------------------------------

  function status(msg) { $("tf-status").textContent = msg; }

  function apiError(e) {
    status("Backend unavailable (" + e.message + "). Start it with: uvicorn kudbee_quant.api:app");
  }

  function loadLive() {
    status("Loading " + state.symbol + " " + state.interval + "…");
    fetch(API + "/trace/" + encodeURIComponent(state.symbol) + "?interval=" + state.interval + "&bars=64")
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) {
        state.bars = d.bars; state.barIndex = -1;
        state.bracket = d.bracket; state.minPct = d.config.min_pct;
        state.trade = null; state.events = {};
        render();
        status("Updated " + new Date().toLocaleTimeString() + " · " + state.symbol +
          " " + state.interval + " · validated gate ≥" + pct(state.minPct) + ".");
        $("tf-detail").textContent = d.disclaimer;
      })
      .catch(apiError);
  }

  var sandboxTimer = null;
  function scheduleSandbox() {
    if (sandboxTimer) clearTimeout(sandboxTimer);
    sandboxTimer = setTimeout(loadSandbox, 250);
  }

  function sandboxBody() {
    var enabled = FACTORS.map(function (f) { return f.key; })
      .filter(function (k) { return !state.disabled[k]; });
    var ema = {
      ema_13: Number($("tf-ema13").value) || 13,
      ema_50: Number($("tf-ema50").value) || 50,
      ema_800: Number($("tf-ema800").value) || 800,
    };
    Object.keys(ema).forEach(function (k) {
      ema[k] = Math.max(2, Math.min(2000, Math.round(ema[k])));
    });
    return { symbol: state.symbol, interval: state.interval, bars: 64,
             ema: ema, factors: enabled, min_pct: state.minPct };
  }

  function loadSandbox() {
    status("Recomputing sandbox…");
    fetch(API + "/sandbox/trace", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(sandboxBody()),
    })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (b) {
          throw new Error(b.detail ? JSON.stringify(b.detail) : r.status);
        });
        return r.json();
      })
      .then(function (d) {
        state.bars = d.bars; state.barIndex = -1;
        state.gate = d.gate; state.bracket = null;
        state.trade = null; state.events = {};
        render();
        status("Sandbox recomputed " + new Date().toLocaleTimeString() +
          " — UNVALIDATED, display only.");
        $("tf-detail").textContent = d.sandbox_note + " EMA spans: 13→" +
          d.params.ema.ema_13 + ", 50→" + d.params.ema.ema_50 + ", 800→" +
          d.params.ema.ema_800 + " · " + d.params.factors.length + "/10 factors in the stack.";
      })
      .catch(apiError);
  }

  function loadTrades() {
    var sel = $("tf-trade");
    sel.innerHTML = '<option value="">— pick a journal trade —</option>';
    fetch(API + "/journal")
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) {
        var opts = [];
        (d.open || []).forEach(function (t) {
          opts.push({ id: t.id, label: t.id + " · " + t.symbol + " · " + t.status + " · " + (t.setup || "") });
        });
        (d.resolved_series || []).slice().reverse().forEach(function (t) {
          if (!t.id) return;
          opts.push({ id: t.id, label: t.id + " · " + (t.symbol || "?") + " · " +
            (t.r > 0 ? "+" : "") + t.r + "R · " + String(t.t).slice(0, 10) });
        });
        opts.forEach(function (o) {
          var opt = document.createElement("option");
          opt.value = o.id; opt.textContent = o.label;
          sel.appendChild(opt);
        });
        status(opts.length ? "Pick a trade to replay its confluence flow bar by bar."
          : "No replayable trades in the journal yet.");
      })
      .catch(apiError);
  }

  function loadReplay(id) {
    status("Replaying " + id + "…");
    fetch(API + "/replay/" + encodeURIComponent(id))
      .then(function (r) {
        if (!r.ok) return r.json().then(function (b) {
          throw new Error(b.detail || r.status);
        });
        return r.json();
      })
      .then(function (d) {
        state.bars = d.bars; state.trade = d.trade; state.events = d.events;
        state.symbol = d.trade.symbol; state.interval = d.trade.timeframe;
        state.bracket = null; state.barIndex = 0;
        var scrub = $("tf-scrub");
        scrub.max = String(d.bars.length - 1);
        scrub.value = "0";
        render(); updateBarLabel();
        status("Replay loaded: " + d.trade.id + " " + d.trade.symbol + " — scrub or press play.");
        $("tf-detail").textContent = "Honest read: " + d.caveat;
      })
      .catch(apiError);
  }

  function updateBarLabel() {
    var bar = currentBar();
    if (!bar) { $("tf-bar-label").textContent = ""; return; }
    var i = state.barIndex < 0 ? state.bars.length - 1 : state.barIndex;
    var evs = state.events[String(i)];
    $("tf-bar-label").textContent = String(bar.timestamp).slice(0, 16) +
      (bar.pre ? " (pre)" : "") + " · " + (i + 1) + "/" + state.bars.length +
      (evs ? " ◄ " + evs.join(", ") : "");
  }

  function stopPlay() {
    if (state.playing) { clearInterval(state.playing); state.playing = null; $("tf-play").textContent = "▶"; }
  }

  // --- starfield --------------------------------------------------------------------

  function startStars() {
    var c = $("tf-stars"), ctx = c.getContext("2d");
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    var stars = [];
    function resize() {
      c.width = window.innerWidth; c.height = window.innerHeight;
      stars = [];
      for (var i = 0; i < 110; i++) {
        stars.push({ x: Math.random() * c.width, y: Math.random() * c.height,
          r: Math.random() * 1.6 + 0.3, vx: (Math.random() - 0.5) * 0.15,
          vy: (Math.random() - 0.5) * 0.15, a: Math.random() * 0.5 + 0.15 });
      }
    }
    resize();
    window.addEventListener("resize", resize);
    (function tick() {
      if (!document.hidden) {
        ctx.clearRect(0, 0, c.width, c.height);
        stars.forEach(function (s) {
          s.x = (s.x + s.vx + c.width) % c.width;
          s.y = (s.y + s.vy + c.height) % c.height;
          ctx.beginPath();
          ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
          ctx.fillStyle = "rgba(159, 144, 255," + s.a + ")";
          ctx.fill();
        });
      }
      window.requestAnimationFrame(tick);
    })();
  }

  // --- tabs + controls ------------------------------------------------------------

  function setTab(tab) {
    stopPlay();
    state.tab = tab;
    state.disabled = {};
    document.querySelectorAll(".tf-tab").forEach(function (b) {
      b.classList.toggle("is-active", b.dataset.tab === tab);
    });
    $("tf-banner").hidden = tab !== "sandbox";
    $("tf-sandbox-controls").hidden = tab !== "sandbox";
    $("tf-replay-controls").hidden = tab !== "replay";
    $("tf-shelf").hidden = tab !== "sandbox";
    $("tf-symbol").disabled = tab === "replay";
    $("tf-interval").disabled = tab === "replay";
    buildGraph();
    if (tab === "replay") { state.bars = []; state.trade = null; render(); loadTrades(); }
    else if (tab === "sandbox") { state.minPct = Number($("tf-minpct").value) / 100; loadSandbox(); }
    else { loadLive(); }
  }

  function bindControls() {
    var symSel = $("tf-symbol");
    WATCHLIST.forEach(function (s) {
      var o = document.createElement("option");
      o.value = s; o.textContent = s;
      symSel.appendChild(o);
    });
    symSel.value = state.symbol;
    symSel.addEventListener("change", function () {
      state.symbol = symSel.value;
      state.tab === "sandbox" ? scheduleSandbox() : loadLive();
    });
    $("tf-interval").addEventListener("change", function () {
      state.interval = $("tf-interval").value;
      state.tab === "sandbox" ? scheduleSandbox() : loadLive();
    });
    $("tf-refresh").addEventListener("click", function () {
      if (state.tab === "replay") { loadTrades(); return; }
      state.tab === "sandbox" ? loadSandbox() : loadLive();
    });
    ["tf-ema13", "tf-ema50", "tf-ema800"].forEach(function (id) {
      $(id).addEventListener("input", scheduleSandbox);
    });
    $("tf-minpct").addEventListener("input", function () {
      state.minPct = Number($("tf-minpct").value) / 100;
      $("tf-minpct-val").textContent = $("tf-minpct").value + "%";
      render();
      scheduleSandbox();
    });
    $("tf-trade").addEventListener("change", function () {
      stopPlay();
      if ($("tf-trade").value) loadReplay($("tf-trade").value);
    });
    $("tf-scrub").addEventListener("input", function () {
      stopPlay();
      state.barIndex = Number($("tf-scrub").value);
      render(); updateBarLabel();
    });
    $("tf-play").addEventListener("click", function () {
      if (state.playing) { stopPlay(); return; }
      if (!state.bars.length) return;
      $("tf-play").textContent = "❚❚";
      state.playing = setInterval(function () {
        var i = (state.barIndex < 0 ? 0 : state.barIndex) + 1;
        if (i >= state.bars.length) { stopPlay(); return; }
        state.barIndex = i;
        $("tf-scrub").value = String(i);
        render(); updateBarLabel();
      }, 330);
    });
    document.querySelectorAll(".tf-tab").forEach(function (b) {
      b.addEventListener("click", function () { setTab(b.dataset.tab); });
    });
    window.addEventListener("resize", function () {
      window.requestAnimationFrame(drawEdges);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    canvas = $("tf-canvas");
    edgesSvg = $("tf-edges");
    bindControls();
    bindDrag();
    startStars();
    buildGraph();
    loadLive();
  });
})();
