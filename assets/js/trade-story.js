/* =========================================================
   Kudbee Quant — Trade Story widget
   A cinematic, choreographed candlestick "trade read" that loops
   in ~60s. Vanilla JS, no deps, no build step. Single IIFE.

   - Candles + levels + trade bracket render on a DPR-aware <canvas>
     (aria-hidden, decorative).
   - Agent bubbles / notes are absolutely-positioned DOM, layered above.
   - prefers-reduced-motion: reduce -> one static composed frame, no loop.

   ILLUSTRATIVE ONLY. The scenario and agent notes depict how the system
   *reads* a setup — they are not live data, signals, or a track record.

   Auto-inits on DOMContentLoaded against #trade-story / .trade-story.
   ========================================================= */
(function () {
  "use strict";

  /* ---------- The scenario: a W double-bottom w/ liquidity sweep ----------
     Prices are illustrative round numbers around a 64k psych low / 65k high.
     vol class: 'norm' | 'vector' | 'climax'  (drives PVSRA coloring + glow). */

  var PSYCH_LOW = 64000;
  var PSYCH_HIGH = 65000;
  var DAILY_OPEN = 64760;

  // Each candle: {o,h,l,c, vol} where vol marks the special vector/climax bars.
  // Story beats are keyed to candle indexes below (SWEEP, RECLAIM, etc).
  var CANDLES = [
    // 0..3  drift down from the open toward the psych low
    { o: 64760, h: 64810, l: 64640, c: 64690, vol: "norm" },
    { o: 64690, h: 64720, l: 64500, c: 64545, vol: "norm" },
    { o: 64545, h: 64600, l: 64360, c: 64400, vol: "norm" },
    { o: 64400, h: 64440, l: 64210, c: 64255, vol: "norm" },
    // 4  approach the low
    { o: 64255, h: 64300, l: 64120, c: 64160, vol: "norm" },
    // 5  SWEEP: high-volume DOWN candle spikes BELOW 64k, closes back above -> reclaim wick
    { o: 64160, h: 64210, l: 63760, c: 64050, vol: "climax" },
    // 6  RECLAIM: bull vector candle, demand steps in
    { o: 64050, h: 64470, l: 64020, c: 64430, vol: "vector" },
    // 7..9 bounce up to the neckline
    { o: 64430, h: 64640, l: 64380, c: 64600, vol: "norm" },
    { o: 64600, h: 64760, l: 64540, c: 64720, vol: "norm" },
    { o: 64720, h: 64820, l: 64660, c: 64700, vol: "norm" }, // NECKLINE ~64800
    // 10..12 pull back to a HIGHER low (right foot, holds above 64k)
    { o: 64700, h: 64720, l: 64450, c: 64490, vol: "norm" },
    { o: 64490, h: 64520, l: 64300, c: 64340, vol: "norm" },
    { o: 64340, h: 64380, l: 64250, c: 64370, vol: "norm" }, // RIGHTFOOT low ~64250 > 64k
    // 13 small base build
    { o: 64370, h: 64560, l: 64350, c: 64540, vol: "norm" },
    // 14 BREAKOUT: high-volume bull vector through the neckline
    { o: 64540, h: 64990, l: 64520, c: 64950, vol: "vector" },
    // 15..17 run to target
    { o: 64950, h: 65180, l: 64900, c: 65120, vol: "norm" },
    { o: 65120, h: 65380, l: 65080, c: 65330, vol: "norm" },
    { o: 65330, h: 65560, l: 65290, c: 65520, vol: "norm" }, // TARGET ~65500
  ];

  var IDX = {
    SWEEP: 5,
    RECLAIM: 6,
    NECKLINE: 9,
    RIGHTFOOT: 12,
    BREAKOUT: 14,
    TARGET: 17,
  };

  // Trade bracket (illustrative): entry on the retest, stop below the sweep low,
  // target = 3R measured up from entry.
  var ENTRY = 64540;          // retest / breakout candle open area
  var STOP = 63720;           // just below the sweep low (63760)
  var RISK = ENTRY - STOP;    // 820
  var TARGET = ENTRY + 3 * RISK; // ~67000 -> clamped visually to the run high

  // Agents, in narrative order. anchor = candle index they pin to.
  var AGENTS = [
    {
      key: "liquidity", cls: "ts-bubble--liquidity", emoji: "🔍",
      name: "Liquidity", tag: "sweep",
      note: "Swept the <strong>64k</strong> psych low — stops taken, no follow-through.",
      anchor: IDX.SWEEP, side: "below",
    },
    {
      key: "pvsra", cls: "ts-bubble--pvsra", emoji: "🕯️",
      name: "PVSRA", tag: "vector",
      note: "<strong>Bull vector</strong> candle on the reclaim — demand stepped in.",
      anchor: IDX.RECLAIM, side: "above",
    },
    {
      key: "structure", cls: "ts-bubble--structure", emoji: "📐",
      name: "Structure", tag: "pattern",
      note: "Higher low holding → <strong>double-bottom (W)</strong> confirming.",
      anchor: IDX.RIGHTFOOT, side: "below",
    },
    {
      key: "reviewer", cls: "ts-bubble--reviewer", emoji: "✅",
      name: "Reviewer", tag: "review",
      note: "Reviewed <strong>3 reads</strong> · confluence 60% · setup confirmed.",
      anchor: IDX.RIGHTFOOT, side: "above",
    },
    {
      key: "risk", cls: "ts-bubble--risk", emoji: "🎯",
      name: "Risk", tag: "plan",
      note: "<strong>Long on retest</strong> · stop &lt; sweep · 3R target.",
      anchor: IDX.BREAKOUT, side: "above",
    },
  ];

  /* ---------- color helpers (PVSRA-ish) ---------- */
  function candleColors(c) {
    var up = c.c >= c.o;
    if (c.vol === "climax") {
      return up
        ? { body: "#28c4ff", wick: "#7fdcff", glow: "rgba(40,196,255,.55)" }   // cyan/blue
        : { body: "#c46bff", wick: "#d9a3ff", glow: "rgba(196,107,255,.55)" }; // violet/magenta
    }
    if (c.vol === "vector") {
      return up
        ? { body: "#3ddc84", wick: "#7af0ab", glow: "rgba(61,220,132,.55)" }   // bright lime
        : { body: "#ff5d5d", wick: "#ff9a9a", glow: "rgba(255,93,93,.55)" };   // bright red
    }
    return up
      ? { body: "#3a7d63", wick: "#5fa987", glow: null }   // muted green
      : { body: "#9e4750", wick: "#c46b74", glow: null };  // muted red
  }

  /* ---------- main per-mount setup ---------- */
  function init(mount) {
    if (mount.__tsBooted) return;
    mount.__tsBooted = true;

    var reduce = window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // ----- build DOM scaffold -----
    mount.classList.add("trade-story");
    mount.innerHTML = "";

    var head = el("div", "ts-head");
    head.innerHTML =
      '<span class="ts-head__title"><span class="ts-head__dot"></span>' +
      "How Kudbee reads a trade</span>" +
      '<span class="ts-head__badge">W · liquidity sweep</span>';
    mount.appendChild(head);

    var stage = el("div", "ts-stage");
    var canvas = el("canvas", "ts-canvas");
    canvas.setAttribute("aria-hidden", "true");
    var layer = el("div", "ts-layer");
    stage.appendChild(canvas);
    stage.appendChild(layer);
    mount.appendChild(stage);

    var foot = el("div", "ts-foot");
    foot.innerHTML =
      '<span class="ts-foot__icon" aria-hidden="true">ⓘ</span>' +
      '<span class="ts-caption"><strong>Illustrative scenario</strong> — ' +
      "not live data, not a track record. The agents depict how the system " +
      "reads a setup, not real signals.</span>";
    mount.appendChild(foot);

    // Screen-reader description of the whole scenario.
    var sr = el("p", "ts-sr");
    sr.textContent =
      "Illustrative candlestick scenario. Price drifts down from the daily " +
      "open toward a 64,000 psychological low, then spikes below it on a " +
      "high-volume down candle (a liquidity sweep) and closes back above — a " +
      "bullish reclaim and the left foot of a W double bottom. It bounces to a " +
      "neckline near 64,800, pulls back to a higher low that holds above " +
      "64,000 (the right foot), then breaks out on a high-volume bull candle " +
      "and runs toward target. Five agents annotate the read: Liquidity flags " +
      "the swept stops, PVSRA flags the bull vector reclaim, Structure confirms " +
      "the double bottom, a Reviewer re-checks the earlier candles, and Risk " +
      "plans a long on the retest with a stop below the sweep and a 3R target. " +
      "Illustrative only — not a trading signal or performance claim.";
    mount.appendChild(sr);

    var ctx = canvas.getContext("2d");

    // geometry, recomputed on resize
    var W = 0, H = 0, dpr = 1;
    var plot = { x: 0, y: 0, w: 0, h: 0 };
    var pmin = 0, pmax = 0;          // price range mapped to plot
    var step = 0, bodyW = 0;         // x spacing / candle body width
    var nVisible = CANDLES.length;   // condense on narrow screens

    function measure() {
      var rect = stage.getBoundingClientRect();
      W = Math.max(1, Math.round(rect.width));
      H = Math.max(1, Math.round(rect.height));
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(W * dpr);
      canvas.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      // On very narrow screens, show fewer candles (drop the long run tail)
      // so candles stay readable and bubbles don't clip.
      nVisible = W < 560 ? 15 : CANDLES.length;

      var padL = W < 560 ? 14 : 22;
      var padR = W < 560 ? 58 : 78;   // room for the right-edge price labels
      var padT = W < 560 ? 40 : 54;   // headroom for "above" bubbles
      var padB = W < 560 ? 30 : 38;
      plot.x = padL; plot.y = padT;
      plot.w = W - padL - padR;
      plot.h = H - padT - padB;

      // price range over visible candles, with a little padding
      var lo = Infinity, hi = -Infinity;
      for (var i = 0; i < nVisible; i++) {
        if (CANDLES[i].l < lo) lo = CANDLES[i].l;
        if (CANDLES[i].h > hi) hi = CANDLES[i].h;
      }
      lo = Math.min(lo, STOP);            // ensure the stop is on-screen
      var pad = (hi - lo) * 0.08;
      pmin = lo - pad; pmax = hi + pad;

      step = plot.w / nVisible;
      bodyW = Math.max(3, Math.min(step * 0.58, 22));
    }

    function xCenter(i) { return plot.x + step * (i + 0.5); }
    function yPrice(p) {
      return plot.y + plot.h * (1 - (p - pmin) / (pmax - pmin));
    }

    /* ---------- drawing primitives ---------- */
    function clear() { ctx.clearRect(0, 0, W, H); }

    function drawGrid() {
      ctx.save();
      ctx.strokeStyle = "rgba(255,255,255,.035)";
      ctx.lineWidth = 1;
      var rows = 4;
      for (var r = 0; r <= rows; r++) {
        var y = plot.y + (plot.h * r) / rows;
        ctx.beginPath();
        ctx.moveTo(plot.x, Math.round(y) + 0.5);
        ctx.lineTo(plot.x + plot.w, Math.round(y) + 0.5);
        ctx.stroke();
      }
      ctx.restore();
    }

    function levelLine(price, label, color, dash, faint) {
      var y = yPrice(price);
      if (y < plot.y - 2 || y > plot.y + plot.h + 2) return;
      ctx.save();
      ctx.strokeStyle = color;
      ctx.globalAlpha = faint ? 0.5 : 0.9;
      ctx.lineWidth = 1;
      ctx.setLineDash(dash || []);
      ctx.beginPath();
      ctx.moveTo(plot.x, Math.round(y) + 0.5);
      ctx.lineTo(plot.x + plot.w, Math.round(y) + 0.5);
      ctx.stroke();
      ctx.setLineDash([]);
      // label chip at right edge
      ctx.globalAlpha = 1;
      var fs = W < 560 ? 9 : 10.5;
      ctx.font = "500 " + fs + "px 'JetBrains Mono', ui-monospace, monospace";
      var txt = label;
      var tw = ctx.measureText(txt).width;
      var bx = plot.x + plot.w + 6;
      var bh = fs + 8;
      ctx.fillStyle = "rgba(13,19,32,.85)";
      roundRect(bx, y - bh / 2, tw + 10, bh, 4);
      ctx.fill();
      ctx.fillStyle = color;
      ctx.textBaseline = "middle";
      ctx.fillText(txt, bx + 5, y + 0.5);
      ctx.restore();
    }

    function roundRect(x, y, w, h, r) {
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.arcTo(x + w, y, x + w, y + h, r);
      ctx.arcTo(x + w, y + h, x, y + h, r);
      ctx.arcTo(x, y + h, x, y, r);
      ctx.arcTo(x, y, x + w, y, r);
      ctx.closePath();
    }

    // grow = 0..1 reveal progress for the latest candle (subtle grow/wick)
    function drawCandle(i, grow) {
      var c = CANDLES[i];
      var col = candleColors(c);
      var cx = xCenter(i);
      var up = c.c >= c.o;

      var yO = yPrice(c.o), yC = yPrice(c.c);
      var yH = yPrice(c.h), yL = yPrice(c.l);
      var bodyTop = Math.min(yO, yC);
      var bodyBot = Math.max(yO, yC);
      var fullH = Math.max(1.5, bodyBot - bodyTop);

      // grow animation: scale body+wick from the open price outward
      var g = grow == null ? 1 : easeOut(grow);
      var yOpen = yPrice(c.o);
      bodyTop = yOpen + (bodyTop - yOpen) * g;
      bodyBot = yOpen + (bodyBot - yOpen) * g;
      yH = yOpen + (yH - yOpen) * g;
      yL = yOpen + (yL - yOpen) * g;

      ctx.save();
      if (col.glow) {
        ctx.shadowColor = col.glow;
        ctx.shadowBlur = 14;
      }
      // wick
      ctx.strokeStyle = col.wick;
      ctx.lineWidth = Math.max(1, bodyW * 0.14);
      ctx.beginPath();
      ctx.moveTo(Math.round(cx) + 0.5, yH);
      ctx.lineTo(Math.round(cx) + 0.5, yL);
      ctx.stroke();
      // body
      ctx.fillStyle = col.body;
      var h = Math.max(1.5, bodyBot - bodyTop);
      roundRect(cx - bodyW / 2, bodyTop, bodyW, h, Math.min(3, bodyW * 0.22));
      ctx.fill();
      ctx.restore();
      void up; void fullH;
    }

    // Trade bracket: entry line, shaded stop zone (red) + target zone (green).
    function drawBracket(progress) {
      var p = clamp(progress, 0, 1);
      if (p <= 0) return;
      var x0 = xCenter(IDX.BREAKOUT) - step * 0.5;
      var x1 = plot.x + plot.w;
      var w = (x1 - x0) * p;

      var yE = yPrice(ENTRY);
      var yS = yPrice(STOP);
      var yTraw = yPrice(TARGET);
      var yT = Math.max(plot.y, yTraw); // clamp into view

      ctx.save();
      // stop zone (entry -> stop), red
      ctx.fillStyle = "rgba(255,93,93,.10)";
      ctx.fillRect(x0, yE, w, yS - yE);
      // target zone (entry -> target), green
      ctx.fillStyle = "rgba(61,220,132,.10)";
      ctx.fillRect(x0, yT, w, yE - yT);

      // boundary lines
      ctx.setLineDash([4, 4]);
      ctx.lineWidth = 1;
      lineSeg(x0, yS, x0 + w, yS, "rgba(255,93,93,.7)");   // stop
      lineSeg(x0, yT, x0 + w, yT, "rgba(61,220,132,.7)");  // target
      ctx.setLineDash([]);
      lineSeg(x0, yE, x0 + w, yE, "rgba(245,166,35,.85)"); // entry (solid honey)
      ctx.restore();

      // labels (fade in near the end)
      if (p > 0.55) {
        var fs = W < 560 ? 8.5 : 10;
        ctx.save();
        ctx.font = "500 " + fs + "px 'JetBrains Mono', ui-monospace, monospace";
        ctx.textBaseline = "middle";
        bracketLabel("ENTRY", x0 + 6, yE, "#FFD45E");
        bracketLabel("STOP", x0 + 6, yS, "#ff8a8a");
        bracketLabel("3R TARGET", x0 + 6, yT, "#7af0ab");
        ctx.restore();
      }
    }
    function bracketLabel(t, x, y, color) {
      ctx.fillStyle = color;
      ctx.fillText(t, x, y - 7);
    }
    function lineSeg(x0, y0, x1, y1, color) {
      ctx.strokeStyle = color;
      ctx.beginPath();
      ctx.moveTo(x0, y0);
      ctx.lineTo(x1, y1);
      ctx.stroke();
    }

    // Reviewer scan highlight sweeping back across earlier candles.
    function drawScan(pos) {
      // pos 0..1 across candles 0..RIGHTFOOT
      var lastI = IDX.RIGHTFOOT;
      var sx = plot.x;
      var ex = xCenter(lastI) + step * 0.5;
      var x = ex - (ex - sx) * pos; // sweeps right -> left ("goes back")
      var bandW = step * 1.6;
      ctx.save();
      var grad = ctx.createLinearGradient(x - bandW, 0, x + bandW, 0);
      grad.addColorStop(0, "rgba(255,212,94,0)");
      grad.addColorStop(0.5, "rgba(255,212,94,.16)");
      grad.addColorStop(1, "rgba(255,212,94,0)");
      ctx.fillStyle = grad;
      ctx.fillRect(x - bandW, plot.y, bandW * 2, plot.h);
      // bright leading edge
      ctx.strokeStyle = "rgba(255,212,94,.55)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(x, plot.y);
      ctx.lineTo(x, plot.y + plot.h);
      ctx.stroke();
      ctx.restore();
    }

    function drawLevels() {
      levelLine(DAILY_OPEN, "Daily Open  " + fmt(DAILY_OPEN), "#9AA6BC", [6, 5], false);
      levelLine(PSYCH_HIGH, "Psych High  " + fmt(PSYCH_HIGH), "#6A7488", [], true);
      levelLine(PSYCH_LOW, "Psych Low  " + fmt(PSYCH_LOW), "#F5A623", [2, 3], false);
    }

    /* ---------- compose a frame ----------
       revealCount: how many candles are fully drawn.
       growing: fractional reveal of the next candle (0..1) or null.
       bracketP, scanP: progress of bracket / reviewer scan overlays. */
    function compose(state) {
      clear();
      drawGrid();
      drawLevels();
      var full = state.revealCount;
      for (var i = 0; i < full; i++) drawCandle(i, 1);
      if (state.growing != null && full < CANDLES.length) {
        drawCandle(full, state.growing);
      }
      if (state.bracketP > 0) drawBracket(state.bracketP);
      if (state.scanP != null) drawScan(state.scanP);
    }

    /* ---------- bubbles (DOM) ---------- */
    var bubbleEls = {};   // key -> element
    var resultEl = null;

    function buildBubble(a) {
      var b = el("div", "ts-bubble " + a.cls);
      b.setAttribute("role", "note");
      b.innerHTML =
        '<span class="ts-bubble__pin"></span>' +
        '<span class="ts-bubble__line"></span>' +
        '<div class="ts-bubble__head">' +
          '<span class="ts-bubble__avatar" aria-hidden="true">' + a.emoji + "</span>" +
          '<span class="ts-bubble__name">' + a.name + "</span>" +
          '<span class="ts-bubble__tag">' + a.tag + "</span>" +
        "</div>" +
        '<div class="ts-bubble__note ts-bubble__think">' +
          '<span class="ts-think"><span></span><span></span><span></span></span>' +
        "</div>";
      layer.appendChild(b);
      bubbleEls[a.key] = b;
      return b;
    }

    // Position a bubble near its anchor candle, then point the connector
    // at the candle. side = 'above' | 'below'.
    function placeBubble(a, b) {
      var i = Math.min(a.anchor, nVisible - 1);
      var c = CANDLES[i];
      var cx = xCenter(i);
      var anchorY = a.side === "above"
        ? yPrice(c.h) - 10
        : yPrice(c.l) + 10;

      var bw = b.offsetWidth || 190;
      var bh = b.offsetHeight || 80;

      // horizontal: keep inside the stage, biased to the candle but clamped.
      var left = cx - bw / 2;
      left = clamp(left, 8, W - bw - 8);

      var top = a.side === "above"
        ? anchorY - bh - 14
        : anchorY + 14;
      top = clamp(top, 6, H - bh - 6);

      b.style.left = left + "px";
      b.style.top = top + "px";

      // connector: from bubble edge toward (cx, anchorY)
      var pin = b.querySelector(".ts-bubble__pin");
      var line = b.querySelector(".ts-bubble__line");
      // anchor point relative to bubble box
      var ax = cx - left;
      var ay = anchorY - top;
      // origin = nearest point on bubble (mid of the side facing the candle)
      var ox = clamp(ax, 12, bw - 12);
      var oy = a.side === "above" ? bh : 0;
      var dx = ax - ox, dy = ay - oy;
      var len = Math.sqrt(dx * dx + dy * dy);
      var ang = Math.atan2(dy, dx) * 180 / Math.PI;
      line.style.left = ox + "px";
      line.style.top = oy + "px";
      line.style.width = len + "px";
      line.style.transform = "rotate(" + ang + "deg)";
      pin.style.left = (ax - 4.5) + "px";
      pin.style.top = (ay - 4.5) + "px";
    }

    function stampNote(a) {
      var b = bubbleEls[a.key];
      if (!b) return;
      var noteWrap = b.querySelector(".ts-bubble__note");
      noteWrap.innerHTML = a.note;
      noteWrap.classList.remove("ts-bubble__think");
    }

    function repositionAll() {
      AGENTS.forEach(function (a) {
        var b = bubbleEls[a.key];
        if (b) placeBubble(a, b);
      });
      if (resultEl) placeResult();
    }

    function buildResult() {
      resultEl = el("div", "ts-result");
      resultEl.innerHTML =
        '<span class="ts-result__r">+3R</span>' +
        '<span class="ts-result__ill">illustrative</span>';
      layer.appendChild(resultEl);
    }
    function placeResult() {
      if (!resultEl) return;
      var i = Math.min(IDX.TARGET, nVisible - 1);
      var x = xCenter(i);
      var y = yPrice(CANDLES[i].h) - 6;
      var rw = resultEl.offsetWidth || 96;
      var rh = resultEl.offsetHeight || 30;
      resultEl.style.left = clamp(x - rw / 2, 8, W - rw - 8) + "px";
      resultEl.style.top = clamp(y - rh - 8, 6, H - rh - 6) + "px";
    }

    /* ===================================================================
       REDUCED MOTION: render one static, fully-composed frame and stop.
       =================================================================== */
    function renderStatic() {
      measure();
      compose({ revealCount: CANDLES.length, growing: null, bracketP: 1, scanP: null });
      AGENTS.forEach(function (a) {
        var b = buildBubble(a);
        stampNote(a);
        placeBubble(a, b);
        b.classList.add("is-in");
      });
      buildResult();
      placeResult();
      resultEl.classList.add("is-in");
      // keep static frame correct on resize, but never animate
      onResize(function () {
        measure();
        compose({ revealCount: CANDLES.length, growing: null, bracketP: 1, scanP: null });
        repositionAll();
      });
    }

    /* ===================================================================
       ANIMATED TIMELINE — paced ~60s, then fades and loops.
       Built as a list of timed steps driven by requestAnimationFrame.
       =================================================================== */
    var raf = 0;
    var running = false;

    function runLoop() {
      // timeline state
      var state = { revealCount: 0, growing: null, bracketP: 0, scanP: null };
      var t0 = performance.now();

      // --- choreography schedule (ms) ---
      // candles print one-by-one ~0.9s each; agents thinking->note at beats.
      var CANDLE_MS = 920;
      var sched = [];      // {at, fn} timed callbacks
      var anims = [];      // {start, dur, fn(p)} tweens

      function at(ms, fn) { sched.push({ at: ms, fn: fn, done: false }); }
      function tween(start, dur, fn, after) {
        anims.push({ start: start, dur: dur, fn: fn, after: after, started: false, done: false });
      }

      // Reveal candles sequentially with a grow tween for each.
      var clock = 600; // small intro beat
      for (var i = 0; i < CANDLES.length; i++) {
        (function (idx, startAt) {
          tween(startAt, CANDLE_MS * 0.7, function (p) {
            state.growing = p;
          }, function () {
            state.revealCount = idx + 1;
            state.growing = null;
          });
        })(i, clock);
        clock += CANDLE_MS;
      }
      var revealEnd = clock; // ~ 600 + 18*920 ≈ 17.2s

      // Agent beats — each: show bubble (thinking), then stamp note.
      // Timed so the bubble appears as/just after its anchor candle prints.
      function tCandle(i) { return 600 + (i + 1) * CANDLE_MS; }

      scheduleAgent("liquidity", tCandle(IDX.SWEEP) + 150);
      scheduleAgent("pvsra", tCandle(IDX.RECLAIM) + 200);
      scheduleAgent("structure", tCandle(IDX.RIGHTFOOT) + 150);

      // Reviewer: appears, runs a back-scan across earlier candles, then stamps.
      var revAt = tCandle(IDX.RIGHTFOOT) + 1300;
      at(revAt, function () { showBubble(byKey("reviewer")); });
      tween(revAt + 500, 2200, function (p) {
        state.scanP = p;
      }, function () {
        state.scanP = null;
        stampNote(byKey("reviewer"));
      });

      // Risk + bracket at the breakout, then run to target.
      var riskAt = tCandle(IDX.BREAKOUT) + 250;
      at(riskAt, function () { showBubble(byKey("risk")); });
      at(riskAt + 1400, function () { stampNote(byKey("risk")); });
      tween(riskAt + 200, 2600, function (p) { state.bracketP = p; });

      // Result tag once price reaches target.
      var resultAt = tCandle(IDX.TARGET) + 400;
      at(resultAt, function () {
        if (!resultEl) buildResult();
        placeResult();
        resultEl.classList.add("is-in");
      });

      // Hold, then fade everything and loop.
      var holdEnd = Math.max(revealEnd, resultAt) + 3600;
      var fadeMs = 1100;
      at(holdEnd, function () {
        Object.keys(bubbleEls).forEach(function (k) {
          bubbleEls[k].classList.add("is-out");
        });
        if (resultEl) resultEl.classList.remove("is-in");
      });

      var LOOP_END = holdEnd + fadeMs;

      function showBubble(a) {
        var b = bubbleEls[a.key] || buildBubble(a);
        placeBubble(a, b);
        // force reflow so the entrance transition plays
        void b.offsetWidth;
        b.classList.add("is-in");
      }
      function scheduleAgent(key, showAt) {
        var a = byKey(key);
        at(showAt, function () { showBubble(a); });
        at(showAt + 1900, function () { stampNote(a); });
      }

      // ----- the frame pump -----
      function frame(now) {
        if (!running) return;
        var t = now - t0;

        // tweens
        for (var k = 0; k < anims.length; k++) {
          var an = anims[k];
          if (an.done) continue;
          if (t >= an.start) {
            var p = an.dur <= 0 ? 1 : (t - an.start) / an.dur;
            if (p >= 1) {
              an.fn(1);
              if (an.after) an.after();
              an.done = true;
            } else {
              an.fn(p);
            }
          }
        }
        // discrete callbacks
        for (var s = 0; s < sched.length; s++) {
          if (!sched[s].done && t >= sched[s].at) {
            sched[s].done = true;
            sched[s].fn();
          }
        }

        compose(state);

        if (t >= LOOP_END) {
          // reset for the next loop
          resetForLoop();
          t0 = now;
          for (var a1 = 0; a1 < anims.length; a1++) { anims[a1].done = false; }
          for (var c1 = 0; c1 < sched.length; c1++) { sched[c1].done = false; }
          state.revealCount = 0; state.growing = null;
          state.bracketP = 0; state.scanP = null;
        }
        raf = requestAnimationFrame(frame);
      }
      raf = requestAnimationFrame(frame);
    }

    function resetForLoop() {
      // remove bubbles + result so the next loop rebuilds cleanly
      Object.keys(bubbleEls).forEach(function (k) {
        var b = bubbleEls[k];
        if (b && b.parentNode) b.parentNode.removeChild(b);
      });
      bubbleEls = {};
      if (resultEl && resultEl.parentNode) resultEl.parentNode.removeChild(resultEl);
      resultEl = null;
    }

    function byKey(key) {
      for (var i = 0; i < AGENTS.length; i++) if (AGENTS[i].key === key) return AGENTS[i];
      return null;
    }

    /* ---------- resize handling ---------- */
    var resizeCb = null;
    function onResize(cb) { resizeCb = cb; }
    var ro = null;
    function bindResize() {
      var pending = false;
      function handle() {
        if (pending) return;
        pending = true;
        requestAnimationFrame(function () {
          pending = false;
          measure();
          repositionAll();
          if (resizeCb) resizeCb();
        });
      }
      if (window.ResizeObserver) {
        ro = new ResizeObserver(handle);
        ro.observe(stage);
      } else {
        window.addEventListener("resize", handle);
      }
    }

    /* ---------- boot ---------- */
    if (reduce) {
      renderStatic();
      bindResize();
      return;
    }

    measure();
    bindResize();
    running = true;
    runLoop();

    // pause when fully offscreen to save battery; resume when visible.
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (entries) {
        var vis = entries[0] && entries[0].isIntersecting;
        if (vis && !running) {
          running = true;
          runLoop();
        } else if (!vis && running) {
          running = false;
          if (raf) cancelAnimationFrame(raf);
        }
      }, { threshold: 0.05 });
      io.observe(mount);
    }
  }

  /* ---------- tiny utils ---------- */
  function el(tag, cls) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    return e;
  }
  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
  function easeOut(t) { return 1 - Math.pow(1 - t, 3); }
  function fmt(n) {
    return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
  }

  /* ---------- auto-init ---------- */
  function boot() {
    var mounts = document.querySelectorAll("#trade-story, .trade-story");
    for (var i = 0; i < mounts.length; i++) init(mounts[i]);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
