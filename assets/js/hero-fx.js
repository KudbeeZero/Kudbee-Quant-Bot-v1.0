/* =========================================================
   Kudbee Quant — hero ambient FX (CSP-safe canvas)
   A slow drift of PVSRA-style "vector candles" behind the hero copy.
   Purely decorative; pauses entirely under reduced-motion or when the
   tab is hidden. No data, no claims — just texture on brand.
   ========================================================= */
(function () {
  'use strict';
  var canvas = document.getElementById('hero-fx');
  if (!canvas || !canvas.getContext) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var ctx = canvas.getContext('2d');
  var dpr = Math.min(window.devicePixelRatio || 1, 2);
  var W = 0, H = 0, candles = [], raf = 0, running = true;

  // PVSRA-ish palette: neutral, bull, bear, and rare climax (glow).
  var COLORS = [
    { body: 'rgba(110,183,255,0.16)', wick: 'rgba(110,183,255,0.22)' }, // level blue
    { body: 'rgba(46,211,168,0.16)',  wick: 'rgba(46,211,168,0.24)'  }, // mint up
    { body: 'rgba(245,166,35,0.15)',  wick: 'rgba(245,166,35,0.22)'  }, // honey
    { body: 'rgba(255,99,99,0.14)',   wick: 'rgba(255,99,99,0.20)'   }  // down
  ];

  function size() {
    var r = canvas.parentElement.getBoundingClientRect();
    W = Math.max(1, r.width); H = Math.max(1, r.height);
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    build();
  }

  function build() {
    candles = [];
    var step = 26, n = Math.ceil(W / step) + 2;
    for (var i = 0; i < n; i++) {
      candles.push(makeCandle(i * step, H));
    }
  }

  function makeCandle(x, h) {
    var mid = h * (0.25 + Math.random() * 0.5);
    var body = 14 + Math.random() * 70;
    var wick = body + 10 + Math.random() * 50;
    var climax = Math.random() < 0.08;
    return {
      x: x, mid: mid, body: body, wick: wick,
      w: 9 + Math.random() * 5,
      color: COLORS[(Math.random() * COLORS.length) | 0],
      climax: climax,
      vy: (Math.random() - 0.5) * 0.12,   // gentle vertical drift
      phase: Math.random() * Math.PI * 2
    };
  }

  function frame(t) {
    if (!running) return;
    ctx.clearRect(0, 0, W, H);
    var speed = 0.18;                         // px/frame horizontal drift
    for (var i = 0; i < candles.length; i++) {
      var c = candles[i];
      c.x -= speed;
      c.mid += c.vy;
      if (c.mid < H * 0.15 || c.mid > H * 0.85) c.vy = -c.vy;
      if (c.x < -20) { c.x = W + 20; c.mid = H * (0.25 + Math.random() * 0.5); c.color = COLORS[(Math.random() * COLORS.length) | 0]; c.climax = Math.random() < 0.08; }
      var pulse = c.climax ? (0.6 + 0.4 * Math.sin(t * 0.002 + c.phase)) : 1;
      drawCandle(c, pulse);
    }
    raf = requestAnimationFrame(frame);
  }

  function drawCandle(c, pulse) {
    var half = c.w / 2;
    // wick
    ctx.strokeStyle = c.wick; ctx.lineWidth = 1.4;
    ctx.beginPath(); ctx.moveTo(c.x, c.mid - c.wick / 2); ctx.lineTo(c.x, c.mid + c.wick / 2); ctx.stroke();
    // body
    if (c.climax) { ctx.shadowColor = c.color.wick; ctx.shadowBlur = 16 * pulse; }
    ctx.fillStyle = c.color.body;
    ctx.fillRect(c.x - half, c.mid - c.body / 2, c.w, c.body);
    ctx.shadowBlur = 0;
  }

  function start() { if (!raf) { running = true; raf = requestAnimationFrame(frame); } }
  function stop() { running = false; if (raf) { cancelAnimationFrame(raf); raf = 0; } }

  document.addEventListener('visibilitychange', function () { document.hidden ? stop() : start(); });
  var rt;
  window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(size, 150); }, { passive: true });

  size();
  start();
})();
