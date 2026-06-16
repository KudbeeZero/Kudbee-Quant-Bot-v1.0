// Kudbee Quant — Control Center dashboard logic.
// External file (CSP: script-src 'self'). All data is fetched from the same-origin
// API with the session cookie; a 401 bounces to /login.
(function () {
  "use strict";

  const WATCHLIST = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
                     "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "LINKUSDT", "DOTUSDT"];

  const $ = (sel, root = document) => root.querySelector(sel);
  const el = (tag, cls, html) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  };
  const fmt = (x, d = 2) => (x == null || Number.isNaN(x) ? "—" : Number(x).toFixed(d));
  const pct = (x, d = 1) => (x == null ? "—" : (Number(x) * 100).toFixed(d) + "%");
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  async function api(path, opts) {
    const res = await fetch(path, Object.assign({ credentials: "same-origin" }, opts));
    if (res.status === 401) { window.location.href = "/login"; throw new Error("unauthorized"); }
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.status);
    return res.json();
  }

  // ---- clock ----
  function tick() {
    const c = $("#clock");
    if (c) c.textContent = new Date().toISOString().replace("T", " ").slice(0, 19) + " UTC";
  }
  setInterval(tick, 1000); tick();

  // ---- tabs ----
  function showTab(name) {
    document.querySelectorAll("[data-panel]").forEach((p) =>
      p.classList.toggle("hidden", p.getAttribute("data-panel") !== name));
    document.querySelectorAll("#tabs [data-tab]").forEach((b) =>
      b.classList.toggle("!bg-sky", b.getAttribute("data-tab") === name));
    if (name === "positions") loadOpenTrades();
    if (name === "history") loadHistory();
    if (name === "research") loadResearch();
    if (name === "runner") loadRunner();
    if (name === "chart-review") loadChartReviews();
  }
  $("#tabs").addEventListener("click", (e) => {
    const b = e.target.closest("[data-tab]");
    if (b) showTab(b.getAttribute("data-tab"));
  });

  // ---- overview ----
  async function loadOverview() {
    try {
      const [h, j] = await Promise.all([api("/api/health"), api("/api/journal")]);
      renderSystem(h, null);
      renderScorecard(j);
      renderExposure(j);
      api("/api/metrics").then((m) => renderSystem(h, m)).catch(() => {});
    } catch (e) { /* 401 handled in api() */ }
    loadSignals();
  }

  function renderSystem(health, metrics) {
    const cfg = (health && health.config) || {};
    const rows = [
      ["status", health ? health.status : "—"],
      ["interval", cfg.interval || "—"],
      ["min confluence", cfg.min_pct != null ? pct(cfg.min_pct, 0) : "—"],
      ["target", cfg.target_r != null ? cfg.target_r + "R" : "—"],
    ];
    if (metrics && !metrics.error) {
      rows.push(["cpu", fmt(metrics.cpu_pct, 0) + "%"]);
      rows.push(["mem", fmt(metrics.mem_pct, 0) + "%"]);
      rows.push(["disk", fmt(metrics.disk_pct, 0) + "%"]);
    }
    $("#system").innerHTML = rows.map(([k, v]) =>
      `<div class="flex justify-between py-0.5"><span class="text-muted">${esc(k)}</span><span>${esc(v)}</span></div>`).join("");
  }

  function renderScorecard(j) {
    const c = j.counts || {};
    const totalR = (j.resolved_series && j.resolved_series.length)
      ? j.resolved_series[j.resolved_series.length - 1] : null;
    const rows = [
      ["open / pending", (c.open || 0) + " / " + (c.pending || 0)],
      ["wins", c.hit || 0], ["losses", c.miss || 0], ["cancelled", c.cancelled || 0],
      ["cumulative R", totalR == null ? "—" : fmt(totalR, 2)],
    ];
    $("#scorecard").innerHTML = rows.map(([k, v]) =>
      `<div class="flex justify-between py-0.5"><span class="text-muted">${esc(k)}</span><span>${esc(v)}</span></div>`).join("");
  }

  function renderExposure(j) {
    const gross = j.total_gross_risk_pct;
    const color = gross > 10 ? "text-danger" : gross > 5 ? "text-honey" : "text-mint";
    const items = (j.exposure || []).slice(0, 8).map((e) =>
      `<div class="flex justify-between py-0.5"><span class="text-muted">${esc(e.symbol)}</span>` +
      `<span>${fmt(e.gross_risk * 100, 2)}%</span></div>`).join("") || `<div class="text-muted">no open risk</div>`;
    $("#exposure").innerHTML =
      `<div class="mb-2 text-2xl ${color}">${gross == null ? "—" : fmt(gross, 2) + "%"}</div>` +
      `<div class="text-[10px] text-muted mb-2">total gross risk</div>${items}`;
  }

  async function loadSignals() {
    const box = $("#signals");
    box.innerHTML = WATCHLIST.map((s) =>
      `<div class="rounded border border-edge bg-ink/40 p-2" data-sig="${s}">` +
      `<div class="text-[11px] text-muted">${s.replace("USDT", "")}</div>` +
      `<div class="text-xs text-muted">loading…</div></div>`).join("");
    WATCHLIST.forEach(async (sym) => {
      try {
        const d = await api("/api/signal/" + sym);
        const card = box.querySelector(`[data-sig="${sym}"]`);
        if (!card) return;
        const dirCls = d.direction > 0 ? "text-mint" : d.direction < 0 ? "text-danger" : "text-muted";
        const badge = d.actionable ? `<span class="kq-pill bg-mint/20 text-mint">●</span>` : "";
        card.innerHTML =
          `<div class="flex justify-between"><span class="text-[11px] text-muted">${sym.replace("USDT", "")}</span>${badge}</div>` +
          `<div class="text-sm ${dirCls}">${esc(d.side)}</div>` +
          `<div class="text-[11px] text-muted">${pct(d.confluence_pct, 0)} · ${esc(d.strength)}</div>`;
      } catch (e) { /* skip */ }
    });
  }

  // ---- positions ----
  async function loadOpenTrades() {
    const box = $("#open-trades");
    box.innerHTML = `<div class="text-muted text-xs">loading…</div>`;
    try {
      const d = await api("/api/open-trades");
      const t = d.trades || [];
      if (!t.length) { box.innerHTML = `<div class="text-muted text-xs">no open positions</div>`; return; }
      const head = ["symbol", "dir", "status", "entry", "unreal R", "MFE", "MAE", "health"];
      box.innerHTML = table(head, t.map((p) => [
        p.symbol, dirArrow(p.direction), p.status, fmt(p.entry_price, 4),
        coloredR(p.unrealized_r), fmt(p.mfe_r, 2), fmt(p.mae_r, 2), healthPill(p.health),
      ]));
      const port = d.portfolio || {};
      box.insertAdjacentHTML("afterbegin",
        `<div class="mb-3 text-xs text-muted">open: <b class="text-body">${port.total_open ?? 0}</b> · ` +
        `unrealized: ${coloredR(port.total_unrealized_r)} · open risk: ${fmt(port.total_open_risk_pct, 1)}%</div>`);
    } catch (e) { box.innerHTML = `<div class="text-danger text-xs">${esc(e.message)}</div>`; }
  }

  // ---- history ----
  function historyQuery(extra) {
    const p = new URLSearchParams({ status: "closed" });
    const tf = $("#f-tf").value, sym = $("#f-symbol").value.trim().toUpperCase(), mode = $("#f-mode").value;
    if (tf) p.set("timeframe", tf);
    if (sym) p.set("symbol", sym);
    if (mode) p.set("mode", mode);
    if (extra) for (const [k, v] of Object.entries(extra)) v ? p.set(k, v) : p.delete(k);
    return "/api/trade-history?" + p.toString();
  }

  async function loadHistory() {
    try {
      const d = await api(historyQuery());
      const a = d.portfolio || {};
      const n = a.total_trades ?? (d.trades || []).length;
      $("#f-summary").textContent = `${n} closed trades · ${a.n_resolved ?? 0} resolved`;
      const rows = [
        ["trades", n], ["win rate", pct(a.win_rate)],
        ["expectancy", fmt(a.expectancy_r, 3) + "R"], ["profit factor", fmt(a.profit_factor, 2)],
        ["total R", coloredR(a.total_r)], ["avg win", fmt(a.avg_win_r, 2) + "R"],
        ["avg loss", fmt(a.avg_loss_r, 2) + "R"],
      ];
      $("#history-analytics").innerHTML = rows.map(([k, v]) =>
        `<div class="flex justify-between py-0.5"><span class="text-muted">${esc(k)}</span><span>${v}</span></div>`).join("");
      drawEquity(d.equity_curve || []);

      // By symbol — worst total R first (where the bleeding is).
      const sym = Object.entries(a.per_symbol || {})
        .sort((x, y) => x[1].total_r - y[1].total_r);
      $("#by-symbol").innerHTML = sym.length
        ? table(["symbol", "n", "total R", "exp"], sym.map(([s, v]) =>
            [esc(s), v.n, coloredR(v.total_r), coloredR(v.expectancy_r)]))
        : `<div class="text-muted text-xs">no data</div>`;

      // By hour (UTC) — expectancy per hour-of-day.
      const hr = Object.entries(a.per_hour || {}).sort((x, y) => +x[0] - +y[0]);
      $("#by-hour").innerHTML = hr.length
        ? table(["hour", "n", "exp"], hr.map(([h, v]) =>
            [String(h).padStart(2, "0") + ":00", v.n, coloredR(v.expectancy_r)]))
        : `<div class="text-muted text-xs">no data</div>`;

      const t = (d.trades || []).slice(-40).reverse();
      $("#history-table").innerHTML = t.length
        ? table(["symbol", "tf", "dir", "result", "R", "opened"],
            t.map((p) => [p.symbol, esc(p.timeframe || "—"), dirArrow(p.direction), p.status,
              coloredR(p.outcome_r), (p.created_at || "").slice(0, 16)]))
        : `<div class="text-muted text-xs">no closed trades</div>`;

      loadByTimeframe();
    } catch (e) { $("#history-analytics").innerHTML = `<div class="text-danger text-xs">${esc(e.message)}</div>`; }
  }

  // By timeframe — one call per TF (respects symbol/mode filters), so you can
  // see which timeframe is actually carrying or bleeding the book.
  async function loadByTimeframe() {
    const TFS = ["5m", "15m", "1h", "2h", "4h"];
    try {
      const results = await Promise.all(TFS.map((tf) =>
        api(historyQuery({ timeframe: tf })).then((d) => [tf, d]).catch(() => [tf, null])));
      const rows = results.filter(([, d]) => d && (d.trades || []).length).map(([tf, d]) => {
        const a = d.portfolio || {};
        return [tf, a.total_trades ?? (d.trades || []).length, pct(a.win_rate, 0),
                coloredR(a.total_r), coloredR(a.expectancy_r)];
      });
      $("#by-tf").innerHTML = rows.length
        ? table(["tf", "n", "win%", "total R", "exp"], rows)
        : `<div class="text-muted text-xs">no data</div>`;
    } catch (e) { $("#by-tf").innerHTML = `<div class="text-danger text-xs">${esc(e.message)}</div>`; }
  }

  function drawEquity(curve) {
    const cv = $("#equity"); if (!cv) return;
    const ctx = cv.getContext("2d");
    const w = cv.width = cv.clientWidth || 600, h = cv.height;
    ctx.clearRect(0, 0, w, h);
    if (!curve.length) { ctx.fillStyle = "#5a6080"; ctx.fillText("no data", 10, 20); return; }
    const min = Math.min(0, ...curve), max = Math.max(0, ...curve), range = (max - min) || 1;
    const x = (i) => (i / (curve.length - 1 || 1)) * (w - 8) + 4;
    const y = (v) => h - 4 - ((v - min) / range) * (h - 8);
    ctx.strokeStyle = "#1e1e4a"; ctx.beginPath(); ctx.moveTo(0, y(0)); ctx.lineTo(w, y(0)); ctx.stroke();
    ctx.strokeStyle = curve[curve.length - 1] >= 0 ? "#00ff88" : "#ff4560";
    ctx.lineWidth = 1.5; ctx.beginPath();
    curve.forEach((v, i) => (i ? ctx.lineTo(x(i), y(v)) : ctx.moveTo(x(i), y(v))));
    ctx.stroke();
  }

  // ---- research ----
  async function loadResearch() {
    try {
      const d = await api("/api/research");
      const r = d.overnight_results;
      const list = Array.isArray(r) ? r : (r && r.results) || [];
      $("#research-results").innerHTML = list.length
        ? table(["candidate", "verdict", "ΔR", "trades", "win%"],
            list.slice(0, 30).map((x) => [esc(x.name || x.candidate || "—"),
              verdictPill(x.verdict), fmt(x.delta_r ?? x.expectancy_r, 3),
              x.n_trades ?? x.trades ?? "—", x.win_rate != null ? pct(x.win_rate, 0) : "—"]))
        : `<div class="text-muted text-xs">no overnight results yet</div>`;
      const ref = d.reflection || {};
      const led = d.ledger || {};
      const reg = ref.regime || {};
      const rows = [
        ["trend", reg.trend || "—"], ["vol regime", reg.vol_regime || "—"],
        ["choppy", String(reg.choppy ?? "—")],
        ["candidates", (led.n_candidates ?? (ref.ledger_summary || {}).n_candidates) ?? "—"],
        ["FDR survivors", (led.fdr_survivors ?? (ref.ledger_summary || {}).fdr_survivors) ?? "—"],
      ];
      $("#research-reflection").innerHTML = rows.map(([k, v]) =>
        `<div class="flex justify-between py-0.5"><span class="text-muted">${esc(k)}</span><span>${esc(v)}</span></div>`).join("");
    } catch (e) { $("#research-results").innerHTML = `<div class="text-danger text-xs">${esc(e.message)}</div>`; }
  }

  // ---- runner ----
  let ACTIONS = [];
  async function loadRunner() {
    try {
      const d = await api("/api/run");
      ACTIONS = d.actions || [];
      const sel = $("#action");
      if (!sel.options.length) {
        sel.innerHTML = ACTIONS.map((a) => `<option value="${a.action}">${esc(a.label)}</option>`).join("");
        sel.addEventListener("change", renderParams);
        renderParams();
      }
      renderJobs(d.jobs || []);
    } catch (e) { $("#jobs").innerHTML = `<div class="text-danger text-xs">${esc(e.message)}</div>`; }
  }

  function currentAction() { return ACTIONS.find((a) => a.action === $("#action").value); }

  function renderParams() {
    const a = currentAction(); if (!a) return;
    const props = (a.params && a.params.properties) || {};
    $("#action-desc").textContent = a.label;
    $("#action-params").innerHTML = Object.entries(props).map(([name, p]) => {
      const def = p.default;
      const isArr = p.type === "array";
      const isBool = p.type === "boolean";
      const isNum = p.type === "integer" || p.type === "number";
      if (isBool)
        return `<label class="flex items-center gap-2 text-xs"><input type="checkbox" data-p="${name}" ${def ? "checked" : ""}/> ${esc(name)}</label>`;
      const val = isArr ? (Array.isArray(def) ? def.join(",") : "BTCUSDT,ETHUSDT") : (def ?? "");
      const attrs = isNum ? `type="number" step="any"` : `type="text"`;
      return `<div><label class="kq-label">${esc(name)}${isArr ? " (comma-sep)" : ""}</label>` +
             `<input class="kq-input" data-p="${name}" data-kind="${p.type}" ${attrs} value="${esc(val)}"/></div>`;
    }).join("");
  }

  function collectParams() {
    const out = {};
    $("#action-params").querySelectorAll("[data-p]").forEach((inp) => {
      const name = inp.getAttribute("data-p");
      if (inp.type === "checkbox") { out[name] = inp.checked; return; }
      const kind = inp.getAttribute("data-kind");
      let v = inp.value.trim();
      if (v === "") return;
      if (kind === "array") out[name] = v.split(",").map((s) => s.trim()).filter(Boolean);
      else if (kind === "integer" || kind === "number") out[name] = Number(v);
      else out[name] = v;
    });
    return out;
  }

  $("#run").addEventListener("click", async () => {
    const a = currentAction(); if (!a) return;
    const btn = $("#run"); btn.disabled = true; btn.textContent = "Submitting…";
    try {
      const job = await api("/api/run/" + a.action, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ params: collectParams() }),
      });
      pollJob(job.id);
      loadRunner();
    } catch (e) {
      $("#job-result").textContent = "Error: " + e.message;
    } finally { btn.disabled = false; btn.textContent = "Run"; }
  });

  function pollJob(id) {
    const iv = setInterval(async () => {
      try {
        const j = await api("/api/run/" + id);
        renderJobs(null);
        if (j.status === "done" || j.status === "error") {
          clearInterval(iv);
          $("#job-result").textContent = j.status === "done"
            ? JSON.stringify(j.result, null, 2)
            : "Error: " + (j.error || "failed");
          loadRunner();
        }
      } catch (e) { clearInterval(iv); }
    }, 1500);
  }

  function renderJobs(jobs) {
    if (!jobs) return; // refreshed via loadRunner
    $("#jobs").innerHTML = jobs.length
      ? jobs.slice(0, 12).map((j) =>
          `<button class="flex w-full justify-between rounded border border-edge px-2 py-1 text-left hover:border-sky/60" data-job="${j.id}">` +
          `<span>${esc(j.action)}</span><span class="${statusCls(j.status)}">${esc(j.status)}</span></button>`).join("")
      : `<div class="text-muted">no jobs yet</div>`;
    $("#jobs").querySelectorAll("[data-job]").forEach((b) =>
      b.addEventListener("click", async () => {
        const j = await api("/api/run/" + b.getAttribute("data-job"));
        $("#job-result").textContent = j.status === "done"
          ? JSON.stringify(j.result, null, 2) : "(" + j.status + ") " + (j.error || "running…");
      }));
  }

  // ---- chart review ----
  const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
  let crFile = null;

  function crPickFile(f) {
    crFile = null;
    $("#cr-preview").classList.add("hidden");
    if (!f) { $("#cr-submit").disabled = true; return; }
    if (!/^image\/(png|jpeg|webp|gif)$/.test(f.type)) {
      $("#cr-result").innerHTML = `<div class="text-danger text-xs">Unsupported type — PNG/JPG/WEBP/GIF only.</div>`;
      $("#cr-submit").disabled = true; return;
    }
    if (f.size > MAX_IMAGE_BYTES) {
      $("#cr-result").innerHTML = `<div class="text-danger text-xs">Image exceeds 5MB.</div>`;
      $("#cr-submit").disabled = true; return;
    }
    crFile = f;
    $("#cr-result").innerHTML = "";
    $("#cr-drop-text").textContent = f.name;
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = $("#cr-preview");
      img.src = e.target.result;            // data: URL — allowed by CSP (img-src data:)
      img.classList.remove("hidden");
    };
    reader.readAsDataURL(f);
    $("#cr-submit").disabled = false;
  }

  function biasPill(b) {
    const c = b === "long" ? "bg-mint/20 text-mint" : b === "short" ? "bg-danger/20 text-danger" : "bg-edge text-muted";
    return `<span class="kq-pill ${c}">${esc(b || "—")}</span>`;
  }
  function recPill(r) {
    const c = r === "trade_candidate" ? "bg-mint/20 text-mint" : r === "no_trade" ? "bg-danger/20 text-danger" : "bg-honey/20 text-honey";
    return `<span class="kq-pill ${c}">${esc((r || "—").replace(/_/g, " "))}</span>`;
  }

  function renderReview(box, rv, meta) {
    const lv = rv.key_levels || {};
    const levels = [
      ["support", (lv.support || []).map((x) => fmt(x, 4)).join(", ") || "—"],
      ["resistance", (lv.resistance || []).map((x) => fmt(x, 4)).join(", ") || "—"],
      ["entry", rv.suggested_entry != null ? fmt(rv.suggested_entry, 4) : "—"],
      ["stop", rv.suggested_stop != null ? fmt(rv.suggested_stop, 4) : "—"],
      ["target", rv.suggested_target != null ? fmt(rv.suggested_target, 4) : "—"],
    ];
    box.innerHTML =
      `<div class="rounded border border-edge bg-ink/40 p-3 mt-1">` +
      `<div class="flex flex-wrap items-center gap-2 mb-2">${biasPill(rv.bias)} ${recPill(rv.final_recommendation)}` +
      `<span class="text-xs text-muted">${esc(rv.setup_name)} · conf ${esc(rv.confidence)}%</span></div>` +
      levels.map(([k, v]) =>
        `<div class="flex justify-between py-0.5 text-xs"><span class="text-muted">${esc(k)}</span><span>${esc(v)}</span></div>`).join("") +
      `<div class="mt-2 text-[11px] text-body leading-relaxed">${esc(rv.rationale)}</div>` +
      (meta ? `<div class="mt-2 text-[10px] text-muted">${esc(meta)}</div>` : "") +
      `</div>`;
  }

  async function submitChartReview() {
    if (!crFile) return;
    const btn = $("#cr-submit"); btn.disabled = true; btn.textContent = "Reviewing…";
    try {
      const fd = new FormData();
      fd.append("image", crFile);
      fd.append("symbol", $("#cr-symbol").value.trim());
      fd.append("timeframe", $("#cr-tf").value);
      fd.append("notes", $("#cr-notes").value.trim());
      const d = await api("/api/chart-review", { method: "POST", body: fd });
      renderReview($("#cr-result"), d.review, `${d.ai_model_used} · ${d.id}`);
      loadChartReviews();
    } catch (e) {
      $("#cr-result").innerHTML = `<div class="text-danger text-xs">${esc(e.message)}</div>`;
    } finally { btn.disabled = false; btn.textContent = "Review chart"; }
  }

  async function loadChartReviews() {
    const box = $("#cr-history");
    box.innerHTML = `<div class="text-muted text-xs">loading…</div>`;
    try {
      const d = await api("/api/chart-reviews");
      const r = d.reviews || [];
      if (!r.length) { box.innerHTML = `<div class="text-muted text-xs">no reviews yet</div>`; return; }
      box.innerHTML = r.map((x) =>
        `<div class="flex gap-3 rounded border border-edge bg-ink/40 p-2">` +
        (x.has_image ? `<img src="/api/chart-images/${esc(x.id)}" alt="" class="h-14 w-20 shrink-0 rounded object-cover border border-edge" />` : "") +
        `<div class="min-w-0 flex-1">` +
        `<div class="flex flex-wrap items-center gap-2">${biasPill(x.bias)} ${recPill(x.final_recommendation)}` +
        `<span class="text-xs text-body">${esc(x.symbol)}</span>` +
        `<span class="text-[11px] text-muted">${esc(x.timeframe || "")}</span></div>` +
        `<div class="text-[11px] text-muted">${esc(x.setup_name)} · conf ${esc(x.confidence)}% · ${esc((x.created_at || "").slice(0, 16))}</div>` +
        `</div></div>`).join("");
    } catch (e) { box.innerHTML = `<div class="text-danger text-xs">${esc(e.message)}</div>`; }
  }

  // ---- shared bits ----
  function table(head, rows) {
    return `<table class="w-full text-xs"><thead><tr class="text-muted text-left">` +
      head.map((h) => `<th class="py-1 pr-3 font-normal">${esc(h)}</th>`).join("") +
      `</tr></thead><tbody>` +
      rows.map((r) => `<tr class="border-t border-edge/50">` +
        r.map((c) => `<td class="py-1 pr-3">${c}</td>`).join("") + `</tr>`).join("") +
      `</tbody></table>`;
  }
  const dirArrow = (d) => d > 0 ? `<span class="text-mint">▲</span>` : d < 0 ? `<span class="text-danger">▼</span>` : "—";
  const coloredR = (r) => r == null ? "—" : `<span class="${r >= 0 ? "text-mint" : "text-danger"}">${fmt(r, 2)}R</span>`;
  const statusCls = (s) => s === "done" ? "text-mint" : s === "error" ? "text-danger" : "text-honey";
  const healthPill = (h) => {
    const c = /stop/.test(h) ? "bg-danger/20 text-danger" : /TP/.test(h) ? "bg-mint/20 text-mint" : "bg-edge text-muted";
    return `<span class="kq-pill ${c}">${esc(h || "—")}</span>`;
  };
  const verdictPill = (v) => {
    const c = /WIN/.test(v) ? "bg-mint/20 text-mint" : /HURT/.test(v) ? "bg-danger/20 text-danger" : "bg-edge text-muted";
    return `<span class="kq-pill ${c}">${esc(v || "—")}</span>`;
  };

  // ---- wiring ----
  $("#refresh").addEventListener("click", loadOverview);
  $("#logout").addEventListener("click", async () => {
    await fetch("/api/logout", { method: "POST", credentials: "same-origin" }).catch(() => {});
    window.location.href = "/login";
  });
  $("#f-apply").addEventListener("click", loadHistory);
  $("#f-tf").addEventListener("change", loadHistory);
  $("#f-mode").addEventListener("change", loadHistory);
  $("#f-symbol").addEventListener("keydown", (e) => { if (e.key === "Enter") loadHistory(); });

  // chart review wiring
  $("#cr-drop").addEventListener("click", () => $("#cr-file").click());
  $("#cr-file").addEventListener("change", (e) => crPickFile(e.target.files[0]));
  $("#cr-drop").addEventListener("dragover", (e) => { e.preventDefault(); $("#cr-drop").classList.add("border-sky/60"); });
  $("#cr-drop").addEventListener("dragleave", () => $("#cr-drop").classList.remove("border-sky/60"));
  $("#cr-drop").addEventListener("drop", (e) => {
    e.preventDefault(); $("#cr-drop").classList.remove("border-sky/60");
    crPickFile(e.dataTransfer.files[0]);
  });
  $("#cr-submit").addEventListener("click", submitChartReview);

  showTab("overview");
  loadOverview();
  setInterval(loadOverview, 90000);
})();
