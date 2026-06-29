/* =========================================================
   Kudbee Quant — hero ambient FX (CSP-safe canvas)
   Two layers behind the hero copy:
     1) a live-building PVSRA candlestick stream (green up / red down,
        with bright "vector" climax candles) + a faint equity line,
     2) a drifting particle/ember field (honey + mint).
   A leftward alpha fade keeps the headline readable. Purely decorative
   (aria-hidden): pauses under reduced-motion or a hidden tab, so JS-off
   leaves the page fully visible. No data, no claims — texture on brand.
   ========================================================= */
(function () {
  'use strict';
  var canvas = document.getElementById('hero-fx');
  if (!canvas || !canvas.getContext) return;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var ctx = canvas.getContext('2d');
  var dpr = Math.min(window.devicePixelRatio || 1, 2);
  var W = 0, H = 0, raf = 0, running = true;
  var candles = [], particles = [], step = 18, cw = 10;

  var MINT = '46,211,168', RED = '255,99,99', HONEY = '245,166,35', BLUE = '110,183,255';

  function size() {
    var r = canvas.parentElement.getBoundingClientRect();
    W = Math.max(1, r.width); H = Math.max(1, r.height);
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    build();
  }

  // A gently-trending random walk mapped into the lower band of the hero.
  function priceBand() { return { top: H * 0.32, bot: H * 0.92 }; }
  function makeCandle(x, prevClose) {
    var band = priceBand();
    var span = band.bot - band.top;
    var drift = -span * 0.0016;                 // slight upward bias (price up = y down)
    var move = (Math.random() - 0.5) * span * 0.11 + drift;
    var open = prevClose;
    var close = Math.max(band.top + 6, Math.min(band.bot - 6, open + move));
    var hi = Math.min(open, close) - Math.random() * span * 0.05;
    var lo = Math.max(open, close) + Math.random() * span * 0.05;
    var up = close <= open;                      // y-down: close above open => bullish
    var vector = Math.random() < 0.16;           // PVSRA climax candle
    return { x: x, open: open, close: close, hi: hi, lo: lo, up: up,
             vector: vector, phase: Math.random() * 6.28 };
  }

  function build() {
    candles = [];
    var band = priceBand();
    var prev = band.top + (band.bot - band.top) * 0.6;
    var n = Math.ceil(W / step) + 3;
    for (var i = 0; i < n; i++) {
      var c = makeCandle(i * step, prev);
      prev = c.close; candles.push(c);
    }
    particles = [];
    var pn = Math.round(Math.min(64, Math.max(28, W / 26)));
    for (var k = 0; k < pn; k++) particles.push(makeParticle(true));
  }

  function makeParticle(anywhere) {
    return {
      x: Math.random() * W,
      y: anywhere ? Math.random() * H : H + 8,
      r: 0.6 + Math.random() * 1.8,
      vy: 0.15 + Math.random() * 0.5,
      vx: (Math.random() - 0.5) * 0.15,
      a: 0.15 + Math.random() * 0.5,
      hue: Math.random() < 0.5 ? HONEY : MINT,
      ph: Math.random() * 6.28
    };
  }

  function drawCandle(c, t) {
    var col = c.up ? MINT : RED;
    var bodyA = c.vector ? 0.62 : 0.4;
    var wickA = c.vector ? 0.7 : 0.42;
    var bodyTop = Math.min(c.open, c.close), bodyH = Math.max(2, Math.abs(c.close - c.open));
    if (c.vector) {
      var pulse = 0.6 + 0.4 * Math.sin(t * 0.002 + c.phase);
      ctx.shadowColor = 'rgba(' + col + ',0.9)';
      ctx.shadowBlur = 14 * pulse;
    }
    ctx.strokeStyle = 'rgba(' + col + ',' + wickA + ')'; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(c.x, c.hi); ctx.lineTo(c.x, c.lo); ctx.stroke();
    ctx.fillStyle = 'rgba(' + col + ',' + bodyA + ')';
    ctx.fillRect(c.x - cw / 2, bodyTop, cw, bodyH);
    ctx.shadowBlur = 0;
  }

  function drawEquityLine() {
    ctx.strokeStyle = 'rgba(' + BLUE + ',0.22)'; ctx.lineWidth = 1.4;
    ctx.beginPath();
    for (var i = 0; i < candles.length; i++) {
      var c = candles[i];
      if (i === 0) ctx.moveTo(c.x, c.close); else ctx.lineTo(c.x, c.close);
    }
    ctx.stroke();
  }

  function drawParticles(t) {
    for (var i = 0; i < particles.length; i++) {
      var p = particles[i];
      var tw = 0.6 + 0.4 * Math.sin(t * 0.001 + p.ph);
      ctx.beginPath();
      ctx.fillStyle = 'rgba(' + p.hue + ',' + (p.a * tw).toFixed(3) + ')';
      ctx.arc(p.x, p.y, p.r, 0, 6.2832); ctx.fill();
    }
  }

  function readabilityFade() {
    // Multiply existing pixels by a left->right alpha ramp so the headline
    // (top-left) stays clean while motion reads in the open right side.
    ctx.globalCompositeOperation = 'destination-in';
    var g = ctx.createLinearGradient(0, 0, W, 0);
    g.addColorStop(0.0, 'rgba(0,0,0,0.10)');
    g.addColorStop(0.38, 'rgba(0,0,0,0.45)');
    g.addColorStop(1.0, 'rgba(0,0,0,1.0)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.globalCompositeOperation = 'source-over';
  }

  function render(t) {
    ctx.clearRect(0, 0, W, H);
    drawEquityLine();
    for (var i = 0; i < candles.length; i++) drawCandle(candles[i], t);
    drawParticles(t);
    readabilityFade();
  }

  function frame(t) {
    if (!running) return;
    var speed = 0.35;
    for (var i = 0; i < candles.length; i++) candles[i].x -= speed;
    // recycle off-screen candles onto the right, continuing the price path
    while (candles.length && candles[0].x < -cw) {
      var last = candles[candles.length - 1];
      candles.shift();
      candles.push(makeCandle(last.x + step, last.close));
    }
    for (var k = 0; k < particles.length; k++) {
      var p = particles[k]; p.y -= p.vy; p.x += p.vx;
      if (p.y < -8) { particles[k] = makeParticle(false); }
    }
    render(t);
    raf = requestAnimationFrame(frame);
  }

  function start() { if (!raf && running) raf = requestAnimationFrame(frame); }
  function stop() { running = false; if (raf) { cancelAnimationFrame(raf); raf = 0; } }

  var rt;
  window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(size, 150); }, { passive: true });

  size();
  if (reduce) { render(0); return; }   // one static frame, no animation loop
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) { stop(); } else { running = true; start(); }
  });
  start();
})();
