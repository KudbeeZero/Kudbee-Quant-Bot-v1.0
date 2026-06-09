/* =========================================================
   Kudbee Quant — interactions
   ========================================================= */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---- Year ---- */
  var yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  /* ---- Nav: scrolled state + mobile toggle ---- */
  var nav = document.getElementById('nav');
  var onScroll = function () {
    if (window.scrollY > 24) nav.classList.add('scrolled');
    else nav.classList.remove('scrolled');
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  var toggle = document.querySelector('.nav__toggle');
  if (toggle) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    nav.querySelectorAll('.nav__links a, .nav__cta').forEach(function (a) {
      a.addEventListener('click', function () {
        nav.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  /* ---- Scroll reveal ---- */
  var reveals = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && !reduceMotion) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    // stagger siblings
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add('in'); });
  }

  /* ---- Card spotlight follow ---- */
  document.querySelectorAll('.card').forEach(function (card) {
    card.addEventListener('pointermove', function (e) {
      var r = card.getBoundingClientRect();
      card.style.setProperty('--mx', ((e.clientX - r.left) / r.width * 100) + '%');
    });
  });

  /* ---- Animated counters ---- */
  function animateCount(el) {
    var target = parseFloat(el.getAttribute('data-count'));
    var decimals = parseInt(el.getAttribute('data-decimals') || '0', 10);
    var prefix = el.getAttribute('data-prefix') || '';
    var suffix = el.getAttribute('data-suffix') || '';
    var dur = 1400, start = performance.now();

    function fmt(n) {
      var v = decimals ? n.toFixed(decimals) : Math.round(n).toLocaleString('en-US');
      return prefix + v + suffix;
    }
    if (reduceMotion) { el.textContent = fmt(target); return; }
    function tick(now) {
      var p = Math.min((now - start) / dur, 1);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = fmt(target * eased);
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }
  var counters = document.querySelectorAll('[data-count]');
  if ('IntersectionObserver' in window) {
    var cio = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { animateCount(e.target); cio.unobserve(e.target); }
      });
    }, { threshold: 0.6 });
    counters.forEach(function (el) { cio.observe(el); });
  } else {
    counters.forEach(animateCount);
  }

  /* ---- Helper: build smooth SVG path from points ---- */
  function smoothPath(pts) {
    if (!pts.length) return '';
    var d = 'M' + pts[0][0] + ',' + pts[0][1];
    for (var i = 0; i < pts.length - 1; i++) {
      var p0 = pts[i], p1 = pts[i + 1];
      var cx = (p0[0] + p1[0]) / 2;
      d += ' C' + cx + ',' + p0[1] + ' ' + cx + ',' + p1[1] + ' ' + p1[0] + ',' + p1[1];
    }
    return d;
  }

  /* ---- Hero sparkline (animated, wandering) ---- */
  (function sparkline() {
    var line = document.getElementById('sparkLine');
    var fill = document.getElementById('sparkFill');
    var dot  = document.getElementById('sparkDot');
    if (!line) return;
    var W = 400, H = 160, N = 28;
    var data = [];
    var v = 80;
    for (var i = 0; i < N; i++) {
      v += (Math.random() - 0.45) * 16;
      v = Math.max(28, Math.min(132, v));
      data.push(v);
    }
    function render() {
      var pts = data.map(function (y, i) { return [i / (N - 1) * W, y]; });
      var d = smoothPath(pts);
      line.setAttribute('d', d);
      fill.setAttribute('d', d + ' L' + W + ',' + H + ' L0,' + H + ' Z');
      var last = pts[pts.length - 1];
      dot.setAttribute('cx', last[0]);
      dot.setAttribute('cy', last[1]);
    }
    render();
    if (reduceMotion) return;
    setInterval(function () {
      data.shift();
      v += (Math.random() - 0.45) * 16;
      v = Math.max(28, Math.min(132, v));
      data.push(v);
      render();
    }, 1800);
  })();

  /* ---- Equity curve (static, upward-drifting) ---- */
  (function equity() {
    var line = document.getElementById('eqLine');
    var fill = document.getElementById('eqFill');
    if (!line) return;
    var W = 460, H = 240, N = 60;
    var pts = [];
    var v = 210, drift = (210 - 30) / N;
    for (var i = 0; i < N; i++) {
      v -= drift;
      v += (Math.random() - 0.5) * 22;
      v = Math.max(20, Math.min(232, v));
      pts.push([i / (N - 1) * W, v]);
    }
    // enforce a strong finish near the top
    pts[N - 1][1] = 34;
    var d = smoothPath(pts);
    line.setAttribute('d', d);
    fill.setAttribute('d', d + ' L' + W + ',' + H + ' L0,' + H + ' Z');
  })();

  /* ---- Live signal badge flip ---- */
  (function signalBadge() {
    var badge = document.getElementById('signalBadge');
    if (!badge || reduceMotion) return;
    var states = [
      { t: '▲ LONG · 86% conf.', c: 'badge--up' },
      { t: '▲ LONG · 79% conf.', c: 'badge--up' },
      { t: '● WATCH · 61% conf.', c: 'badge--neutral' },
      { t: '▲ LONG · 88% conf.', c: 'badge--up' }
    ];
    var idx = 0;
    setInterval(function () {
      idx = (idx + 1) % states.length;
      badge.className = 'badge ' + states[idx].c;
      badge.textContent = states[idx].t;
    }, 3200);
  })();

  /* ---- Glossary live filter ---- */
  var gSearch = document.getElementById('glossarySearch');
  if (gSearch) {
    var terms = Array.prototype.slice.call(document.querySelectorAll('#glossaryList .term'));
    var empty = document.getElementById('glossaryEmpty');
    // Deep-link: ?q=term focuses the filter
    var q = new URLSearchParams(window.location.search).get('q');
    if (q) gSearch.value = q;
    function filter() {
      var v = gSearch.value.trim().toLowerCase();
      var shown = 0;
      terms.forEach(function (t) {
        var match = t.textContent.toLowerCase().indexOf(v) !== -1;
        t.hidden = !match;
        if (match) shown++;
      });
      if (empty) empty.hidden = shown !== 0;
    }
    gSearch.addEventListener('input', filter);
    if (q) filter();
  }

  /* ---- Waitlist form (front-end only, stores locally) ---- */
  var form = document.getElementById('waitlistForm');
  if (form) {
    var input = document.getElementById('email');
    var msg = document.getElementById('waitlistMsg');
    var re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var val = (input.value || '').trim();
      if (!re.test(val)) {
        msg.textContent = 'Please enter a valid email address.';
        msg.className = 'waitlist__msg err';
        input.focus();
        return;
      }
      // No backend wired yet — persist locally so nothing is lost.
      try {
        var list = JSON.parse(localStorage.getItem('kudbee_waitlist') || '[]');
        if (list.indexOf(val) === -1) list.push(val);
        localStorage.setItem('kudbee_waitlist', JSON.stringify(list));
      } catch (err) { /* storage may be unavailable; non-fatal */ }
      msg.textContent = "You're on the list! 🐝 Watch your inbox for your invite.";
      msg.className = 'waitlist__msg ok';
      form.reset();
    });
  }
})();
