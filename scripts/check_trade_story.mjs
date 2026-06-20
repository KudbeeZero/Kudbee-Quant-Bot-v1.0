/* Invariant validator for the trade-story scenarios (data behind the homepage
   animation). Canvas rendering can't run headless, so this guards the DATA that
   drives it: well-formed OHLC, in-range index beats / thinking anchors / agent
   anchors, and a sane direction-aware bracket.

   Run:  node scripts/check_trade_story.mjs
*/
import { readFileSync } from "node:fs";

const src = readFileSync(new URL("../assets/js/trade-story.js", import.meta.url), "utf8");
const start = src.indexOf("var SCENARIOS =");
const end = src.indexOf("/* ---------- color helpers");
if (start < 0 || end < 0) {
  console.error("FAIL: could not locate the SCENARIOS literal");
  process.exit(1);
}
let lit = src.slice(start + "var SCENARIOS =".length, end).trim().replace(/;\s*$/, "");
// eslint-disable-next-line no-eval
const SCENARIOS = eval("(" + lit + ")");

const errs = [];
const okConcepts = new Set();
for (const s of SCENARIOS) {
  const n = s.candles.length;
  const lows = Math.min(...s.candles.map((c) => c.l));
  const highs = Math.max(...s.candles.map((c) => c.h));
  const range = highs - lows;

  s.candles.forEach((c, i) => {
    const lo = Math.min(c.o, c.c), hi = Math.max(c.o, c.c);
    if (c.l > lo + 1e-9) errs.push(`${s.id} candle ${i}: low ${c.l} > min(o,c) ${lo}`);
    if (c.h < hi - 1e-9) errs.push(`${s.id} candle ${i}: high ${c.h} < max(o,c) ${hi}`);
    if (c.l > c.h) errs.push(`${s.id} candle ${i}: low > high`);
    if (!["norm", "vector", "climax"].includes(c.vol)) errs.push(`${s.id} candle ${i}: bad vol '${c.vol}'`);
  });

  for (const [k, v] of Object.entries(s.idx)) {
    if (v < 0 || v >= n) errs.push(`${s.id} idx.${k}=${v} out of [0,${n})`);
  }
  s.thinking.forEach((t, i) => {
    if (t.at < 0 || t.at >= n) errs.push(`${s.id} thinking[${i}].at=${t.at} out of range`);
    okConcepts.add(t.concept);
  });
  s.agents.forEach((a) => {
    if (a.anchor < 0 || a.anchor >= n) errs.push(`${s.id} agent ${a.key} anchor ${a.anchor} out of range`);
  });

  const br = s.bracket;
  if (![1, -1].includes(br.dir)) errs.push(`${s.id} bracket.dir ${br.dir} not ±1`);
  if (br.startIdx < 0 || br.startIdx >= n) errs.push(`${s.id} bracket.startIdx ${br.startIdx} out of range`);
  if (br.entry < lows || br.entry > highs) errs.push(`${s.id} bracket.entry ${br.entry} outside band [${lows},${highs}]`);
  if (br.stop < lows - range || br.stop > highs + range) errs.push(`${s.id} bracket.stop ${br.stop} implausible vs band`);
  if (br.dir === 1 && !(br.entry > br.stop)) errs.push(`${s.id} long but entry<=stop`);
  if (br.dir === -1 && !(br.entry < br.stop)) errs.push(`${s.id} short but entry>=stop`);
}

if (errs.length) {
  console.error("FAIL:\n  " + errs.join("\n  "));
  process.exit(1);
}
console.log(
  `OK — ${SCENARIOS.length} scenarios valid ` +
  `(${SCENARIOS.map((s) => `${s.id}:${s.candles.length}c/${s.thinking.length}r`).join(", ")}). ` +
  `concepts: ${[...okConcepts].sort().join(", ")}`
);
