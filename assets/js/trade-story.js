/* =========================================================
   Kudbee Quant — Trade Story widget (expanded, multi-setup)
   A cinematic, choreographed candlestick "trade read" that walks
   through SEVERAL real setups, one at a time, while a streaming
   "reasoning log" narrates the read candle-by-candle — time of day,
   the swept level, the vector, the structure, the backtest lens.

   Vanilla JS, no deps, no build step. Single IIFE.
   - Candles + levels + trade bracket render on a DPR-aware <canvas>
     (aria-hidden, decorative).
   - Agent bubbles + the reasoning rail are DOM, layered/aside.
   - Clickable setup chips jump between scenarios; otherwise they cycle.
   - prefers-reduced-motion: reduce -> one static composed frame, no loop.

   ILLUSTRATIVE ONLY. The scenarios and notes depict how the system
   *reads* a setup — they are not live data, signals, or a track record.
   Every concept shown maps to a real part of the engine (PVSRA volume
   classes, sessions / market-maker cycle, daily open / PDH-PDL / round
   levels, liquidity sweeps, double-bottom structure, confluence gate).

   Auto-inits on DOMContentLoaded against #trade-story / .trade-story.
   ========================================================= */
(function () {
  "use strict";

  /* ===================================================================
     SCENARIOS — each is fully self-describing data. Prices are
     illustrative round numbers. vol: 'norm' | 'vector' | 'climax'
     (drives PVSRA coloring + glow). thinking[].at pins a reasoning line
     to a candle index; agents[].anchor pins a bubble to a candle.
     bracket.dir: +1 long / -1 short (bracket is direction-aware).
     =================================================================== */
  var SCENARIOS = [
    /* ---------- 1) W double-bottom with a liquidity sweep (LONG) ---------- */
    {
      id: "w-sweep",
      name: "W · liquidity sweep",
      badge: "W · liquidity sweep",
      candles: [
        { o: 64760, h: 64810, l: 64640, c: 64690, vol: "norm" },
        { o: 64690, h: 64720, l: 64500, c: 64545, vol: "norm" },
        { o: 64545, h: 64600, l: 64360, c: 64400, vol: "norm" },
        { o: 64400, h: 64440, l: 64210, c: 64255, vol: "norm" },
        { o: 64255, h: 64300, l: 64120, c: 64160, vol: "norm" },
        { o: 64160, h: 64210, l: 63760, c: 64050, vol: "climax" }, // 5 SWEEP
        { o: 64050, h: 64470, l: 64020, c: 64430, vol: "vector" }, // 6 RECLAIM
        { o: 64430, h: 64640, l: 64380, c: 64600, vol: "norm" },
        { o: 64600, h: 64760, l: 64540, c: 64720, vol: "norm" },
        { o: 64720, h: 64820, l: 64660, c: 64700, vol: "norm" },   // 9 NECKLINE
        { o: 64700, h: 64720, l: 64450, c: 64490, vol: "norm" },
        { o: 64490, h: 64520, l: 64300, c: 64340, vol: "norm" },
        { o: 64340, h: 64380, l: 64250, c: 64370, vol: "norm" },   // 12 RIGHTFOOT
        { o: 64370, h: 64560, l: 64350, c: 64540, vol: "norm" },
        { o: 64540, h: 64990, l: 64520, c: 64950, vol: "vector" }, // 14 BREAKOUT
        { o: 64950, h: 65180, l: 64900, c: 65120, vol: "norm" },
        { o: 65120, h: 65380, l: 65080, c: 65330, vol: "norm" },
        { o: 65330, h: 65560, l: 65290, c: 65520, vol: "norm" },   // 17 TARGET
      ],
      idx: { SWEEP: 5, RECLAIM: 6, NECKLINE: 9, RIGHTFOOT: 12, BREAKOUT: 14, TARGET: 17 },
      levels: [
        { price: 64760, label: "Daily Open", color: "#9AA6BC", dash: [6, 5], faint: false },
        { price: 65000, label: "Psych High", color: "#6A7488", dash: [], faint: true },
        { price: 64000, label: "Psych Low", color: "#F5A623", dash: [2, 3], faint: false },
      ],
      bracket: { entry: 64540, stop: 63720, dir: 1, rMult: 3, startIdx: 14 },
      result: { r: "+3R" },
      agents: [
        { key: "liquidity", cls: "ts-bubble--liquidity", emoji: "🔍", name: "Liquidity", tag: "sweep",
          note: "Swept the <strong>64k</strong> psych low — stops taken, no follow-through.",
          anchor: 5, side: "below" },
        { key: "pvsra", cls: "ts-bubble--pvsra", emoji: "🕯️", name: "PVSRA", tag: "vector",
          note: "<strong>Bull vector</strong> candle on the reclaim — demand stepped in.",
          anchor: 6, side: "above" },
        { key: "structure", cls: "ts-bubble--structure", emoji: "📐", name: "Structure", tag: "pattern",
          note: "Higher low holding → <strong>double-bottom (W)</strong> confirming.",
          anchor: 12, side: "below" },
        { key: "reviewer", cls: "ts-bubble--reviewer", emoji: "✅", name: "Reviewer", tag: "review",
          note: "Reviewed <strong>3 reads</strong> · confluence 60% · setup confirmed.",
          anchor: 12, side: "above", kind: "reviewer", scanTo: 12 },
        { key: "risk", cls: "ts-bubble--risk", emoji: "🎯", name: "Risk", tag: "plan",
          note: "<strong>Long on retest</strong> · stop &lt; sweep · 3R target.",
          anchor: 14, side: "above", kind: "risk" },
      ],
      thinking: [
        { at: 0, time: "NY 00:00", concept: "open", text: "New session. Marking the <strong>daily open</strong> at 64,760 — the day's fair-value pivot." },
        { at: 3, time: "NY 02:30", concept: "drift", text: "Four red norm candles fading off the open — sellers in control, no volume climax yet." },
        { at: 4, time: "London 06:40", concept: "level", text: "Pressing the <strong>64,000</strong> psych low (and prior-day low). Resting stops sit just beneath it." },
        { at: 5, time: "London 07:05", concept: "sweep", text: "Climax down candle spikes to <strong>63,760</strong> — below 64k — then closes back above. <strong>Liquidity swept</strong>, no follow-through." },
        { at: 6, time: "London 07:20", concept: "vector", text: "<strong>Bull vector</strong>: volume ≥2× average on the reclaim. Demand stepped in where supply should have won." },
        { at: 9, time: "London 08:10", concept: "structure", text: "Bounce stalls at the <strong>neckline</strong> ~64,800. A close above it confirms the W." },
        { at: 12, time: "NY 13:00", concept: "structure", text: "Right foot prints a <strong>higher low</strong> (64,250) holding above 64k. Double-bottom symmetry intact." },
        { at: 12, time: "NY 13:05", concept: "confluence", text: "Reviewer re-scans candles 0–12: sweep + vector + higher-low + PDL = <strong>60% confluence</strong>, above the 50% gate." },
        { at: 14, time: "NY 13:40", concept: "backtest", text: "Neckline breaks on a bull vector. Backtest lens: sweep→reclaim→break is a <strong>measured hypothesis, not a promise</strong>." },
        { at: 14, time: "NY 13:42", concept: "risk", text: "Plan: long the retest 64,540, stop 63,720 (below the sweep), <strong>3R</strong> target. Risk = 820 pts." },
        { at: 17, time: "NY 15:10", concept: "result", text: "Target tagged at <strong>+3R</strong>. Illustrative outcome — not a live fill." },
      ],
    },

    /* ---------- 2) Fade a swept psych-high back into the daily open (SHORT) ---------- */
    {
      id: "fade-high",
      name: "Fade · psych-high",
      badge: "fade · psych-high → daily open",
      candles: [
        { o: 64600, h: 64700, l: 64560, c: 64680, vol: "norm" },
        { o: 64680, h: 64780, l: 64650, c: 64760, vol: "norm" },
        { o: 64760, h: 64870, l: 64740, c: 64850, vol: "norm" },
        { o: 64850, h: 64960, l: 64830, c: 64940, vol: "norm" },   // 3 approach 65k
        { o: 64940, h: 65240, l: 64930, c: 64970, vol: "climax" }, // 4 SWEEP above 65k
        { o: 64970, h: 65010, l: 64640, c: 64690, vol: "vector" }, // 5 bear-vector rejection
        { o: 64690, h: 64720, l: 64520, c: 64560, vol: "norm" },
        { o: 64560, h: 64600, l: 64470, c: 64540, vol: "norm" },   // 7 first low / support
        { o: 64540, h: 64760, l: 64520, c: 64740, vol: "norm" },   // 8 pullback up
        { o: 64740, h: 64840, l: 64700, c: 64720, vol: "norm" },   // 9 LOWER HIGH
        { o: 64720, h: 64740, l: 64560, c: 64580, vol: "norm" },
        { o: 64580, h: 64620, l: 64500, c: 64520, vol: "norm" },   // 11 retest support
        { o: 64520, h: 64540, l: 64180, c: 64220, vol: "vector" }, // 12 BREAKDOWN thru daily open
        { o: 64220, h: 64260, l: 64020, c: 64080, vol: "norm" },
        { o: 64080, h: 64120, l: 63900, c: 63960, vol: "norm" },
        { o: 63960, h: 64000, l: 63780, c: 63820, vol: "norm" },
        { o: 63820, h: 63860, l: 63520, c: 63560, vol: "norm" },   // 16 TARGET
      ],
      idx: { SWEEP: 4, RECLAIM: 5, LOWERHIGH: 9, BREAKOUT: 12, TARGET: 16 },
      levels: [
        { price: 65000, label: "Psych High", color: "#F5A623", dash: [2, 3], faint: false },
        { price: 64600, label: "Daily Open", color: "#9AA6BC", dash: [6, 5], faint: false },
        { price: 64000, label: "Psych Low", color: "#6A7488", dash: [], faint: true },
      ],
      bracket: { entry: 64520, stop: 64860, dir: -1, rMult: 3, startIdx: 12 },
      result: { r: "+3R" },
      agents: [
        { key: "liquidity", cls: "ts-bubble--liquidity", emoji: "🔍", name: "Liquidity", tag: "sweep",
          note: "Swept <strong>65,000</strong> + breakout stops above — spiked through, instantly rejected.",
          anchor: 4, side: "above" },
        { key: "pvsra", cls: "ts-bubble--pvsra", emoji: "🕯️", name: "PVSRA", tag: "vector",
          note: "<strong>Bear vector</strong> on the rejection — large sellers fading the spike.",
          anchor: 5, side: "above" },
        { key: "structure", cls: "ts-bubble--structure", emoji: "📐", name: "Structure", tag: "pattern",
          note: "<strong>Lower high</strong> under 65k → failed breakout / double-top fade.",
          anchor: 9, side: "above" },
        { key: "reviewer", cls: "ts-bubble--reviewer", emoji: "✅", name: "Reviewer", tag: "review",
          note: "Reviewed <strong>3 reads</strong> · confluence 58% · fade confirmed.",
          anchor: 9, side: "below", kind: "reviewer", scanTo: 9 },
        { key: "risk", cls: "ts-bubble--risk", emoji: "🎯", name: "Risk", tag: "plan",
          note: "<strong>Short the retest</strong> · stop &gt; lower high · 3R into the daily open.",
          anchor: 12, side: "below", kind: "risk" },
      ],
      thinking: [
        { at: 0, time: "NY 13:00", concept: "open", text: "New day opens at <strong>64,600</strong>. Bulls pressing higher off the open." },
        { at: 3, time: "NY 13:40", concept: "level", text: "Rally stalling into <strong>65,000</strong> — a psychological round number where breakouts often trap." },
        { at: 4, time: "NY 14:10", concept: "sweep", text: "Climax candle spikes to <strong>65,240</strong> — above 65k — then closes back under. Breakout buyers' stops harvested." },
        { at: 5, time: "NY 14:15", concept: "vector", text: "<strong>Bear vector</strong>: volume ≥2× average rejecting the spike. This is <strong>the fade</strong> — mean-reversion of the climax." },
        { at: 9, time: "NY 15:00", concept: "structure", text: "Bounce makes a <strong>lower high</strong> (64,840), capped under 65k. Sellers in control." },
        { at: 9, time: "NY 15:05", concept: "confluence", text: "Reviewer scans 0–9: swept-high + bear vector + lower-high + daily-open overhead = <strong>58%</strong>. Past the gate." },
        { at: 12, time: "NY 15:50", concept: "backtest", text: "Break below the <strong>daily open</strong>. Backtest lens: 'fade a swept round number' is a measured hypothesis, not a guarantee." },
        { at: 12, time: "NY 15:52", concept: "risk", text: "Plan: short 64,520, stop 64,860 (above the lower high), <strong>3R</strong> into 63,500." },
        { at: 16, time: "NY 17:20", concept: "result", text: "Target tagged at <strong>+3R</strong>. Illustrative — not a live fill." },
      ],
    },

    /* ---------- 3) Asian-range sweep, London reversal (LONG) ---------- */
    {
      id: "asian-london",
      name: "Asian sweep · London",
      badge: "session · Asian sweep → London reversal",
      candles: [
        { o: 64650, h: 64780, l: 64600, c: 64720, vol: "norm" },
        { o: 64720, h: 64860, l: 64680, c: 64800, vol: "norm" },   // 1 near Asian high
        { o: 64800, h: 64880, l: 64640, c: 64680, vol: "norm" },
        { o: 64680, h: 64720, l: 64420, c: 64470, vol: "norm" },
        { o: 64470, h: 64560, l: 64360, c: 64520, vol: "norm" },
        { o: 64520, h: 64600, l: 64380, c: 64410, vol: "norm" },   // 5 drift to Asian low
        { o: 64410, h: 64440, l: 64080, c: 64330, vol: "climax" }, // 6 SWEEP below Asian low (London)
        { o: 64330, h: 64720, l: 64300, c: 64690, vol: "vector" }, // 7 bull-vector reclaim
        { o: 64690, h: 64780, l: 64650, c: 64760, vol: "norm" },   // 8 reclaim daily open
        { o: 64760, h: 64900, l: 64720, c: 64870, vol: "norm" },   // 9 retest Asian high
        { o: 64870, h: 64900, l: 64680, c: 64720, vol: "norm" },   // 10 HIGHER LOW
        { o: 64720, h: 64960, l: 64700, c: 64940, vol: "vector" }, // 11 BREAKOUT Asian high
        { o: 64940, h: 65120, l: 64900, c: 65080, vol: "norm" },
        { o: 65080, h: 65260, l: 65040, c: 65220, vol: "norm" },   // 13 TARGET
        { o: 65220, h: 65420, l: 65180, c: 65380, vol: "norm" },
      ],
      idx: { SWEEP: 6, RECLAIM: 7, NECKLINE: 9, RIGHTFOOT: 10, BREAKOUT: 11, TARGET: 13 },
      levels: [
        { price: 64900, label: "Asian High", color: "#2DD4BF", dash: [6, 5], faint: false },
        { price: 64650, label: "Daily Open", color: "#9AA6BC", dash: [6, 5], faint: true },
        { price: 64300, label: "Asian Low", color: "#F5A623", dash: [2, 3], faint: false },
      ],
      bracket: { entry: 64330, stop: 64040, dir: 1, rMult: 3, startIdx: 7 },
      result: { r: "+3R" },
      agents: [
        { key: "liquidity", cls: "ts-bubble--liquidity", emoji: "🔍", name: "Liquidity", tag: "sweep",
          note: "London swept the <strong>Asian-range low</strong> (64,300) — overnight stops taken, fast reclaim.",
          anchor: 6, side: "below" },
        { key: "pvsra", cls: "ts-bubble--pvsra", emoji: "🕯️", name: "PVSRA", tag: "vector",
          note: "<strong>Bull vector</strong> reclaim — demand at the range low as London opens.",
          anchor: 7, side: "above" },
        { key: "structure", cls: "ts-bubble--structure", emoji: "📐", name: "Structure", tag: "pattern",
          note: "Reclaim + <strong>higher low</strong> → range-low sweep reversal.",
          anchor: 10, side: "below" },
        { key: "reviewer", cls: "ts-bubble--reviewer", emoji: "✅", name: "Reviewer", tag: "review",
          note: "Reviewed <strong>3 reads</strong> · confluence 62% · session timing aligned.",
          anchor: 10, side: "above", kind: "reviewer", scanTo: 10 },
        { key: "risk", cls: "ts-bubble--risk", emoji: "🎯", name: "Risk", tag: "plan",
          note: "<strong>Long the reclaim</strong> · stop &lt; sweep · 3R back through the range.",
          anchor: 11, side: "above", kind: "risk" },
      ],
      thinking: [
        { at: 1, time: "Asian 23:40", concept: "session", text: "Quiet <strong>Asian range</strong> building between 64,300 and 64,900. Marking both edges as liquidity pools." },
        { at: 5, time: "pre-London 06:50", concept: "level", text: "Price drifting to the <strong>Asian low</strong>. Stops stacked just beneath 64,300." },
        { at: 6, time: "London 07:05", concept: "sweep", text: "London open. Climax spike to <strong>64,080</strong> — below the Asian low — then snaps back. Overnight liquidity swept." },
        { at: 7, time: "London 07:20", concept: "vector", text: "<strong>Bull vector</strong> reclaim: the killzone reversal — the manipulation leg before the real move." },
        { at: 8, time: "London 07:35", concept: "open", text: "Reclaims the <strong>daily open</strong> (64,650) — the read flips constructive." },
        { at: 10, time: "London 08:20", concept: "structure", text: "<strong>Higher low</strong> at 64,680 holds. Range-low sweep-and-reverse confirmed." },
        { at: 10, time: "London 08:25", concept: "confluence", text: "Reviewer weighs the Asian range + sweep + session timing: <strong>62% confluence</strong>. Gate passed." },
        { at: 11, time: "London 08:40", concept: "backtest", text: "Breaks the Asian high on a vector. Backtest lens: session-sweep reversals are <strong>time-of-day dependent</strong> — paper-tested, not promised." },
        { at: 7, time: "London 07:25", concept: "risk", text: "Plan: long the reclaim 64,330, stop 64,040 (below the sweep), <strong>3R</strong> target." },
        { at: 13, time: "London 10:00", concept: "result", text: "Target tagged at <strong>+3R</strong>. Illustrative — not a live fill." },
      ],
    },
  ];

  /* ---------- color helpers (PVSRA-ish) ---------- */
  function candleColors(c) {
    var up = c.c >= c.o;
    if (c.vol === "climax") {
      return up
        ? { body: "#28c4ff", wick: "#7fdcff", glow: "rgba(40,196,255,.55)" }
        : { body: "#c46bff", wick: "#d9a3ff", glow: "rgba(196,107,255,.55)" };
    }
    if (c.vol === "vector") {
      return up
        ? { body: "#3ddc84", wick: "#7af0ab", glow: "rgba(61,220,132,.55)" }
        : { body: "#ff5d5d", wick: "#ff9a9a", glow: "rgba(255,93,93,.55)" };
    }
    return up
      ? { body: "#3a7d63", wick: "#5fa987", glow: null }
      : { body: "#9e4750", wick: "#c46b74", glow: null };
  }

  /* ---------- main per-mount setup ---------- */
  function init(mount) {
    if (mount.__tsBooted) return;
    mount.__tsBooted = true;

    var reduce = window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    var scenIndex = 0;
    var SC = SCENARIOS[scenIndex];

    // ----- build DOM scaffold -----
    mount.classList.add("trade-story");
    mount.innerHTML = "";

    var head = el("div", "ts-head");
    head.innerHTML =
      '<span class="ts-head__title"><span class="ts-head__dot"></span>' +
      "How Kudbee reads a trade</span>" +
      '<span class="ts-head__badge"></span>';
    mount.appendChild(head);
    var badgeEl = head.querySelector(".ts-head__badge");

    // setup chips (clickable — jump between scenarios)
    var chips = el("div", "ts-setups");
    var chipEls = [];
    SCENARIOS.forEach(function (s, i) {
      var chip = el("button", "ts-chip");
      chip.type = "button";
      chip.textContent = s.name;
      chip.setAttribute("aria-label", "Show setup: " + s.name);
      chip.addEventListener("click", function () { switchTo(i); });
      chips.appendChild(chip);
      chipEls.push(chip);
    });
    mount.appendChild(chips);

    var main = el("div", "ts-main");
    var stage = el("div", "ts-stage");
    var canvas = el("canvas", "ts-canvas");
    canvas.setAttribute("aria-hidden", "true");
    var layer = el("div", "ts-layer");
    stage.appendChild(canvas);
    stage.appendChild(layer);
    main.appendChild(stage);

    // reasoning rail (the candle-by-candle "thinking" log)
    var rail = el("aside", "ts-rail");
    rail.setAttribute("aria-hidden", "true");
    rail.innerHTML =
      '<div class="ts-rail__head"><span class="ts-rail__dot"></span>' +
      "reasoning<span class=\"ts-rail__cursor\"></span></div>" +
      '<div class="ts-rail__feed"></div>';
    var feed = rail.querySelector(".ts-rail__feed");
    main.appendChild(rail);
    mount.appendChild(main);

    var foot = el("div", "ts-foot");
    foot.innerHTML =
      '<span class="ts-foot__icon" aria-hidden="true">ⓘ</span>' +
      '<span class="ts-caption"><strong>Illustrative scenario</strong> — ' +
      "not live data, not a track record. The agents depict how the system " +
      "reads a setup, not real signals.</span>";
    mount.appendChild(foot);

    var sr = el("p", "ts-sr");
    mount.appendChild(sr);

    var ctx = canvas.getContext("2d");

    // geometry, recomputed on resize
    var W = 0, H = 0, dpr = 1;
    var plot = { x: 0, y: 0, w: 0, h: 0 };
    var pmin = 0, pmax = 0;
    var step = 0, bodyW = 0;
    var nVisible = SC.candles.length;

    function measure() {
      var rect = stage.getBoundingClientRect();
      W = Math.max(1, Math.round(rect.width));
      H = Math.max(1, Math.round(rect.height));
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(W * dpr);
      canvas.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      nVisible = W < 560 ? Math.min(SC.candles.length, 15) : SC.candles.length;

      var padL = W < 560 ? 14 : 22;
      var padR = W < 560 ? 58 : 78;
      var padT = W < 560 ? 40 : 54;
      var padB = W < 560 ? 30 : 38;
      plot.x = padL; plot.y = padT;
      plot.w = W - padL - padR;
      plot.h = H - padT - padB;

      var lo = Infinity, hi = -Infinity;
      for (var i = 0; i < nVisible; i++) {
        if (SC.candles[i].l < lo) lo = SC.candles[i].l;
        if (SC.candles[i].h > hi) hi = SC.candles[i].h;
      }
      lo = Math.min(lo, SC.bracket.stop);   // keep the stop on-screen
      hi = Math.max(hi, SC.bracket.stop);
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

    function drawCandle(i, grow) {
      var c = SC.candles[i];
      var col = candleColors(c);
      var cx = xCenter(i);

      var yO = yPrice(c.o), yC = yPrice(c.c);
      var yH = yPrice(c.h), yL = yPrice(c.l);
      var bodyTop = Math.min(yO, yC);
      var bodyBot = Math.max(yO, yC);

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
      ctx.strokeStyle = col.wick;
      ctx.lineWidth = Math.max(1, bodyW * 0.14);
      ctx.beginPath();
      ctx.moveTo(Math.round(cx) + 0.5, yH);
      ctx.lineTo(Math.round(cx) + 0.5, yL);
      ctx.stroke();
      ctx.fillStyle = col.body;
      var h = Math.max(1.5, bodyBot - bodyTop);
      roundRect(cx - bodyW / 2, bodyTop, bodyW, h, Math.min(3, bodyW * 0.22));
      ctx.fill();
      ctx.restore();
    }

    // Direction-aware trade bracket: entry line, stop zone (red) + target zone (green).
    function drawBracket(progress) {
      var p = clamp(progress, 0, 1);
      if (p <= 0) return;
      var br = SC.bracket;
      var risk = Math.abs(br.entry - br.stop);
      var target = br.entry + br.dir * br.rMult * risk;

      var x0 = xCenter(br.startIdx) - step * 0.5;
      var x1 = plot.x + plot.w;
      var w = (x1 - x0) * p;

      var yE = yPrice(br.entry);
      var yS = yPrice(br.stop);
      var yTraw = yPrice(target);
      var yT = clamp(yTraw, plot.y, plot.y + plot.h); // keep target label in view

      ctx.save();
      // stop zone (entry -> stop), red — fillRect tolerates negative height (short)
      ctx.fillStyle = "rgba(255,93,93,.10)";
      ctx.fillRect(x0, yE, w, yS - yE);
      // target zone (entry -> target), green
      ctx.fillStyle = "rgba(61,220,132,.10)";
      ctx.fillRect(x0, yT, w, yE - yT);

      ctx.setLineDash([4, 4]);
      ctx.lineWidth = 1;
      lineSeg(x0, yS, x0 + w, yS, "rgba(255,93,93,.7)");
      lineSeg(x0, yT, x0 + w, yT, "rgba(61,220,132,.7)");
      ctx.setLineDash([]);
      lineSeg(x0, yE, x0 + w, yE, "rgba(245,166,35,.85)");
      ctx.restore();

      if (p > 0.55) {
        var fs = W < 560 ? 8.5 : 10;
        ctx.save();
        ctx.font = "500 " + fs + "px 'JetBrains Mono', ui-monospace, monospace";
        ctx.textBaseline = "middle";
        bracketLabel("ENTRY", x0 + 6, yE, "#FFD45E");
        bracketLabel("STOP", x0 + 6, yS, "#ff8a8a");
        bracketLabel(br.rMult + "R TARGET", x0 + 6, yT, "#7af0ab");
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
    function drawScan(pos, lastI) {
      var sx = plot.x;
      var ex = xCenter(lastI) + step * 0.5;
      var x = ex - (ex - sx) * pos;
      var bandW = step * 1.6;
      ctx.save();
      var grad = ctx.createLinearGradient(x - bandW, 0, x + bandW, 0);
      grad.addColorStop(0, "rgba(255,212,94,0)");
      grad.addColorStop(0.5, "rgba(255,212,94,.16)");
      grad.addColorStop(1, "rgba(255,212,94,0)");
      ctx.fillStyle = grad;
      ctx.fillRect(x - bandW, plot.y, bandW * 2, plot.h);
      ctx.strokeStyle = "rgba(255,212,94,.55)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(x, plot.y);
      ctx.lineTo(x, plot.y + plot.h);
      ctx.stroke();
      ctx.restore();
    }

    function drawLevels() {
      SC.levels.forEach(function (lv) {
        levelLine(lv.price, lv.label + "  " + fmt(lv.price), lv.color, lv.dash, lv.faint);
      });
    }

    function compose(state) {
      clear();
      drawGrid();
      drawLevels();
      var full = state.revealCount;
      for (var i = 0; i < full; i++) drawCandle(i, 1);
      if (state.growing != null && full < SC.candles.length) {
        drawCandle(full, state.growing);
      }
      if (state.bracketP > 0) drawBracket(state.bracketP);
      if (state.scanP != null) drawScan(state.scanP, state.scanTo);
    }

    /* ---------- bubbles (DOM) ---------- */
    var bubbleEls = {};
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

    function placeBubble(a, b) {
      var i = Math.min(a.anchor, nVisible - 1);
      var c = SC.candles[i];
      var cx = xCenter(i);
      var anchorY = a.side === "above" ? yPrice(c.h) - 10 : yPrice(c.l) + 10;

      var bw = b.offsetWidth || 190;
      var bh = b.offsetHeight || 80;

      var left = cx - bw / 2;
      left = clamp(left, 8, W - bw - 8);

      var top = a.side === "above" ? anchorY - bh - 14 : anchorY + 14;
      top = clamp(top, 6, H - bh - 6);

      b.style.left = left + "px";
      b.style.top = top + "px";

      var pin = b.querySelector(".ts-bubble__pin");
      var line = b.querySelector(".ts-bubble__line");
      var ax = cx - left;
      var ay = anchorY - top;
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
      SC.agents.forEach(function (a) {
        var b = bubbleEls[a.key];
        if (b) placeBubble(a, b);
      });
      if (resultEl) placeResult();
    }

    function buildResult() {
      resultEl = el("div", "ts-result");
      resultEl.innerHTML =
        '<span class="ts-result__r">' + SC.result.r + "</span>" +
        '<span class="ts-result__ill">illustrative</span>';
      layer.appendChild(resultEl);
    }
    function placeResult() {
      if (!resultEl) return;
      var i = Math.min(SC.idx.TARGET, nVisible - 1);
      var x = xCenter(i);
      var y = yPrice(SC.candles[i].h) - 6;
      var rw = resultEl.offsetWidth || 96;
      var rh = resultEl.offsetHeight || 30;
      resultEl.style.left = clamp(x - rw / 2, 8, W - rw - 8) + "px";
      resultEl.style.top = clamp(y - rh - 8, 6, H - rh - 6) + "px";
    }

    /* ---------- reasoning rail ---------- */
    function clearFeed() { feed.innerHTML = ""; }
    function emitThought(tk) {
      var row = el("div", "ts-think-row");
      row.innerHTML =
        '<div class="ts-think-row__meta">' +
          '<span class="ts-think-row__time">' + tk.time + "</span>" +
          '<span class="ts-think-row__tag ts-tag--' + tk.concept + '">' + tk.concept + "</span>" +
        "</div>" +
        '<div class="ts-think-row__text">' + tk.text + "</div>";
      feed.appendChild(row);
      void row.offsetWidth;            // reflow so the entrance plays
      row.classList.add("is-in");
      feed.scrollTop = feed.scrollHeight;
    }

    /* ---------- scenario / a11y plumbing ---------- */
    function setActiveChip() {
      chipEls.forEach(function (chip, i) {
        chip.classList.toggle("is-active", i === scenIndex);
        chip.setAttribute("aria-pressed", i === scenIndex ? "true" : "false");
      });
    }
    function applyScenarioMeta() {
      badgeEl.textContent = SC.badge;
      setActiveChip();
      // screen-reader narrative = the ordered reasoning, plus the standing caveat.
      var lines = SC.thinking.map(function (t) {
        return stripTags(t.text);
      });
      sr.textContent =
        "Illustrative candlestick scenario — " + SC.name + ". " +
        lines.join(" ") +
        " Illustrative only — not a trading signal or performance claim.";
    }

    function byKey(key) {
      for (var i = 0; i < SC.agents.length; i++) {
        if (SC.agents[i].key === key) return SC.agents[i];
      }
      return null;
    }

    // tear down bubbles + result + feed so a scenario can (re)build cleanly
    function clearScenarioDom() {
      Object.keys(bubbleEls).forEach(function (k) {
        var b = bubbleEls[k];
        if (b && b.parentNode) b.parentNode.removeChild(b);
      });
      bubbleEls = {};
      if (resultEl && resultEl.parentNode) resultEl.parentNode.removeChild(resultEl);
      resultEl = null;
      clearFeed();
    }

    /* ===================================================================
       REDUCED MOTION: static, fully-composed frame + full reasoning list.
       =================================================================== */
    function renderStatic() {
      measure();
      compose({ revealCount: SC.candles.length, growing: null, bracketP: 1, scanP: null });
      SC.agents.forEach(function (a) {
        var b = buildBubble(a);
        stampNote(a);
        placeBubble(a, b);
        b.classList.add("is-in");
      });
      buildResult();
      placeResult();
      resultEl.classList.add("is-in");
      SC.thinking.forEach(function (tk) {
        var row = el("div", "ts-think-row is-in");
        row.innerHTML =
          '<div class="ts-think-row__meta">' +
            '<span class="ts-think-row__time">' + tk.time + "</span>" +
            '<span class="ts-think-row__tag ts-tag--' + tk.concept + '">' + tk.concept + "</span>" +
          "</div>" +
          '<div class="ts-think-row__text">' + tk.text + "</div>";
        feed.appendChild(row);
      });
    }

    /* ===================================================================
       ANIMATED TIMELINE — one scenario, then advance to the next & loop.
       =================================================================== */
    var raf = 0;
    var running = false;
    var CANDLE_MS = 920;

    function startTimeline() {
      var state = { revealCount: 0, growing: null, bracketP: 0, scanP: null, scanTo: 0 };
      var shownOrder = [];
      var t0 = performance.now();
      var sched = [];
      var anims = [];

      function at(ms, fn) { sched.push({ at: ms, fn: fn, done: false }); }
      function tween(start, dur, fn, after) {
        anims.push({ start: start, dur: dur, fn: fn, after: after, done: false });
      }

      var INTRO = 600;
      var clock = INTRO;
      for (var i = 0; i < SC.candles.length; i++) {
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
      var revealEnd = clock;
      function tCandle(i) { return INTRO + (i + 1) * CANDLE_MS; }

      // reasoning lines stream in as their candle prints
      SC.thinking.forEach(function (tk) {
        at(tCandle(tk.at) + 120, function () { emitThought(tk); });
      });

      // agents
      var lastBeat = revealEnd;
      SC.agents.forEach(function (a) {
        if (a.kind === "reviewer") {
          var revAt = tCandle(a.anchor) + 1300;
          at(revAt, function () { showBubble(a); });
          tween(revAt + 500, 2200, function (p) {
            state.scanP = p; state.scanTo = a.scanTo;
          }, function () {
            state.scanP = null;
            stampNote(a);
          });
          lastBeat = Math.max(lastBeat, revAt + 2700);
        } else if (a.kind === "risk") {
          var riskAt = tCandle(a.anchor) + 250;
          at(riskAt, function () { showBubble(a); });
          at(riskAt + 1400, function () { stampNote(a); });
          tween(riskAt + 200, 2600, function (p) { state.bracketP = p; });
          lastBeat = Math.max(lastBeat, riskAt + 2800);
        } else {
          var showAt = tCandle(a.anchor) + 180;
          at(showAt, function () { showBubble(a); });
          at(showAt + 1900, function () { stampNote(a); });
          lastBeat = Math.max(lastBeat, showAt + 1900);
        }
      });

      // result tag at target
      var resultAt = tCandle(SC.idx.TARGET) + 400;
      at(resultAt, function () {
        if (!resultEl) buildResult();
        placeResult();
        resultEl.classList.add("is-in");
      });
      lastBeat = Math.max(lastBeat, resultAt);

      var holdEnd = lastBeat + 3600;
      var fadeMs = 1100;
      at(holdEnd, function () {
        Object.keys(bubbleEls).forEach(function (k) {
          bubbleEls[k].classList.add("is-out");
        });
        if (resultEl) resultEl.classList.remove("is-in");
        feed.classList.add("is-fading");
      });
      var LOOP_END = holdEnd + fadeMs;

      function showBubble(a) {
        var b = bubbleEls[a.key] || buildBubble(a);
        placeBubble(a, b);
        void b.offsetWidth;
        b.classList.add("is-in");
        if (W < 560) {
          shownOrder.forEach(function (k) {
            if (k !== a.key && bubbleEls[k]) bubbleEls[k].classList.add("is-out");
          });
        }
        shownOrder.push(a.key);
      }

      function frame(now) {
        if (!running) return;
        var t = now - t0;

        for (var k = 0; k < anims.length; k++) {
          var an = anims[k];
          if (an.done) continue;
          if (t >= an.start) {
            var p = an.dur <= 0 ? 1 : (t - an.start) / an.dur;
            if (p >= 1) { an.fn(1); if (an.after) an.after(); an.done = true; }
            else { an.fn(p); }
          }
        }
        for (var s = 0; s < sched.length; s++) {
          if (!sched[s].done && t >= sched[s].at) {
            sched[s].done = true;
            sched[s].fn();
          }
        }

        compose(state);

        if (t >= LOOP_END) {
          // advance to the next scenario and restart the timeline
          scenIndex = (scenIndex + 1) % SCENARIOS.length;
          SC = SCENARIOS[scenIndex];
          feed.classList.remove("is-fading");
          clearScenarioDom();
          applyScenarioMeta();
          measure();
          startTimeline();
          return; // old frame loop ends; new one took over
        }
        raf = requestAnimationFrame(frame);
      }
      raf = requestAnimationFrame(frame);
    }

    /* ---------- switch scenario (chip click) ---------- */
    function switchTo(i) {
      if (i === scenIndex && (running || reduce)) {
        // already showing it; for reduced motion just rebuild
        if (!reduce) return;
      }
      scenIndex = i;
      SC = SCENARIOS[scenIndex];
      if (raf) cancelAnimationFrame(raf);
      feed.classList.remove("is-fading");
      clearScenarioDom();
      applyScenarioMeta();
      measure();
      if (reduce) {
        renderStatic();
      } else {
        running = true;
        startTimeline();
      }
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
    applyScenarioMeta();

    if (reduce) {
      renderStatic();
      bindResize();
      onResize(function () {
        measure();
        compose({ revealCount: SC.candles.length, growing: null, bracketP: 1, scanP: null });
        repositionAll();
      });
      return;
    }

    measure();
    bindResize();
    running = true;
    startTimeline();

    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (entries) {
        var vis = entries[0] && entries[0].isIntersecting;
        if (vis && !running) {
          running = true;
          clearScenarioDom();
          applyScenarioMeta();
          measure();
          startTimeline();
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
  function fmt(n) { return n.toLocaleString("en-US", { maximumFractionDigits: 0 }); }
  function stripTags(s) { return s.replace(/<[^>]*>/g, ""); }

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
