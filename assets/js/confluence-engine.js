/* =========================================================
   Kudbee Quant — Confluence Engine (interactive, CSP-safe)
   Renders the 10 REAL confluence factors (from confluence/trace.py
   FACTOR_SPECS) as a toggleable grid + a live consensus meter that
   mirrors the honest rule: a setup only qualifies when >=50% of
   factors agree AND the trend group concurs. No returns claims, no
   fabricated stats — this is a teaching demo of how the stack votes.
   ========================================================= */
(function () {
  'use strict';

  var mount = document.getElementById('confluence-engine');
  if (!mount) return;

  /* Factor data — labels/groups verbatim from confluence/trace.py.
     "what" = what it watches; "how" = how it votes (plain English). */
  var GROUPS = [
    { id: 'trend', label: 'Trend' },
    { id: 'level', label: 'Levels' },
    { id: 'smart_money', label: 'Smart money' }
  ];
  var FACTORS = [
    { g: 'trend', label: 'EMA Stack (50/800)',
      what: 'Macro regime: is price stacked above or below the 50 & 800 EMAs?',
      how: 'Bullish when close > EMA50 > EMA800 (stacked up); bearish when stacked down; neutral when mixed.' },
    { g: 'trend', label: 'EMA Momentum (13/50)',
      what: 'Near-term momentum from the fast 13 vs 50 EMA.',
      how: 'Bullish when EMA13 > EMA50; bearish when EMA13 < EMA50.' },
    { g: 'trend', label: 'EMA Cloud (13–50)',
      what: 'Pullback context: where price sits versus the 13/50 band.',
      how: 'Above the cloud = up, below = down, inside = neutral.' },
    { g: 'level', label: 'Session VWAP',
      what: 'The volume-weighted fair value institutions defend intraday.',
      how: 'Close above session VWAP = bullish; below = bearish.' },
    { g: 'level', label: 'Daily Open',
      what: "Intraday skew versus today's opening price.",
      how: "Above the daily open = bullish skew; below = bearish skew." },
    { g: 'level', label: 'Floor Pivot',
      what: "The classic floor pivot (PP) — the day's balance point.",
      how: 'Above the pivot PP = bullish; below = bearish.' },
    { g: 'smart_money', label: 'Premium / Discount',
      what: 'Which half of the dealing range price is trading in.',
      how: 'Discount half = long bias; premium half = short bias (mean-reversion logic).' },
    { g: 'smart_money', label: 'Liquidity Sweep',
      what: 'A run beyond a prior high/low that snaps back — a stop grab.',
      how: 'Swept a prior LOW then reversed = bullish; swept a prior HIGH = bearish.' },
    { g: 'smart_money', label: 'PVSRA Vector',
      what: 'A volume/spread climax candle — where large players likely acted.',
      how: 'A bull climax candle votes long; a bear climax votes short.' },
    { g: 'smart_money', label: 'Fair Value Gap',
      what: 'An unfilled imbalance (gap) the market often returns to.',
      how: 'Price tagging a bullish FVG votes long; a bearish FVG votes short.' }
  ];

  var TREND_TOTAL = FACTORS.filter(function (f) { return f.g === 'trend'; }).length;
  var THRESHOLD = 0.5;           // MIN_PCT in the validated stack
  var state = {};                // label -> bool (voting)

  /* ---- build DOM (no innerHTML of user data; all createElement) ---- */
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  var groupsWrap = el('div', 'engine__groups');
  GROUPS.forEach(function (grp) {
    var section = el('div', 'fgroup');
    section.setAttribute('data-group', grp.id);
    var head = el('div', 'fgroup__label', grp.label);
    section.appendChild(head);
    var cards = el('div', 'fcards');
    FACTORS.filter(function (f) { return f.g === grp.id; }).forEach(function (f) {
      cards.appendChild(buildCard(f));
    });
    section.appendChild(cards);
    groupsWrap.appendChild(section);
  });

  function buildCard(f) {
    var card = el('button', 'fcard');
    card.type = 'button';
    card.setAttribute('aria-pressed', 'false');
    card.setAttribute('data-label', f.label);
    var top = el('div', 'fcard__top');
    top.appendChild(el('span', 'fcard__label', f.label));
    top.appendChild(el('span', 'fcard__tag', f.g === 'smart_money' ? 'smart money' : f.g));
    card.appendChild(top);
    card.appendChild(el('span', 'fcard__vote'));
    card.appendChild(el('p', 'fcard__what', f.what));
    var detail = el('p', 'fcard__detail', f.how);
    card.appendChild(detail);
    card.addEventListener('click', function () { toggle(f.label, card); });
    state[f.label] = false;
    return card;
  }

  function toggle(label, card) {
    var on = !state[label];
    state[label] = on;
    card.classList.toggle('is-on', on);
    card.classList.toggle('is-open', on);
    card.setAttribute('aria-pressed', on ? 'true' : 'false');
    recompute();
  }

  /* ---- consensus panel ---- */
  var panel = el('aside', 'consensus');
  var title = el('div', 'consensus__title');
  title.appendChild(el('span', 'dot'));
  title.appendChild(el('span', null, 'Live consensus'));
  panel.appendChild(title);
  panel.appendChild(el('p', 'consensus__hint',
    'Tap the factors that are voting bullish. A setup only qualifies when at least half agree — and the trend lines up.'));

  var gauge = el('div', 'gauge');
  gauge.style.setProperty('--thresh', String(THRESHOLD * 100));
  var fill = el('div', 'gauge__fill');
  gauge.appendChild(fill);
  gauge.appendChild(el('div', 'gauge__thresh'));
  panel.appendChild(gauge);

  var count = el('div', 'consensus__count');
  var countNum = el('b', null, '0');
  count.appendChild(countNum);
  count.appendChild(el('span', null, '/ ' + FACTORS.length + ' factors voting'));
  panel.appendChild(count);

  var verdict = el('div', 'verdict', 'Tap factors to build a read.');
  panel.appendChild(verdict);

  var actions = el('div', 'consensus__actions');
  var reset = el('button', 'consensus__reset', 'Reset');
  reset.type = 'button';
  reset.addEventListener('click', function () {
    Object.keys(state).forEach(function (k) { state[k] = false; });
    mount.querySelectorAll('.fcard').forEach(function (c) {
      c.classList.remove('is-on', 'is-open'); c.setAttribute('aria-pressed', 'false');
    });
    recompute();
  });
  actions.appendChild(reset);
  panel.appendChild(actions);

  var foot = el('p', 'consensus__foot');
  foot.appendChild(document.createTextNode('Qualifying setups are then backtested net of fees — walk-forward + Monte Carlo. '));
  var mLink = el('a', null, 'See the methodology →');
  mLink.href = 'methodology.html';
  foot.appendChild(mLink);
  panel.appendChild(foot);

  function recompute() {
    var on = FACTORS.filter(function (f) { return state[f.label]; });
    var n = on.length;
    var trendOn = on.filter(function (f) { return f.g === 'trend'; }).length;
    var pct = n / FACTORS.length;
    var trendAligned = trendOn >= 2;          // the trend group concurs (2 of 3)
    var qualifies = pct >= THRESHOLD && trendAligned;

    countNum.textContent = String(n);
    gauge.style.setProperty('--pct', String(Math.round(pct * 100)));

    verdict.classList.remove('is-go', 'is-no');
    if (qualifies) {
      verdict.classList.add('is-go');
      verdict.innerHTML = '';
      verdict.appendChild(strongNode('✓ Setup qualifies. '));
      verdict.appendChild(document.createTextNode(
        n + '/' + FACTORS.length + ' factors agree (≥' + (THRESHOLD * 100) +
        '%) and the trend group concurs — it goes to the backtester.'));
    } else if (n === 0) {
      verdict.textContent = 'Tap factors to build a read.';
    } else {
      verdict.classList.add('is-no');
      verdict.innerHTML = '';
      verdict.appendChild(strongNode('No trade yet. '));
      var need = Math.max(0, Math.ceil(THRESHOLD * FACTORS.length) - n);
      if (pct >= THRESHOLD && !trendAligned) {
        verdict.appendChild(document.createTextNode(
          'Enough factors agree, but the trend group (' + trendOn + '/' + TREND_TOTAL +
          ') doesn’t concur. The stack stays flat.'));
      } else {
        verdict.appendChild(document.createTextNode(
          'Need ≥' + (THRESHOLD * 100) + '% of factors and the trend to line up — ' +
          need + ' more to go.'));
      }
    }
  }
  function strongNode(t) { var b = document.createElement('b'); b.textContent = t; return b; }

  /* ---- assemble ---- */
  var grid = el('div', 'engine__grid reveal');
  grid.appendChild(groupsWrap);
  grid.appendChild(panel);
  mount.appendChild(grid);
  recompute();

  /* Hook the existing scroll-reveal if it hasn't already observed this node. */
  if ('IntersectionObserver' in window &&
      !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('is-visible'); io.unobserve(e.target); } });
    }, { threshold: 0.12 });
    io.observe(grid);
  } else {
    grid.classList.add('is-visible');
  }
})();
