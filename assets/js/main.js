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
      document.body.classList.toggle('nav-open', open);
    });
    nav.querySelectorAll('.nav__links a, .nav__cta').forEach(function (a) {
      a.addEventListener('click', function () {
        nav.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('nav-open');
      });
    });
  }

  /* ---- Scroll reveal ---- */
  // White-screen guard: only NOW (JS is confirmed running and about to wire the
  // observer) do we enable the reveal animation. CSS keeps .reveal visible by
  // default, so if this file is disabled/blocked or anything above threw, the
  // page still renders fully instead of blanking out.
  document.documentElement.classList.add('js-anim');
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

  /* ---- Equity curve (illustrative losing run — choppy, net-down) ---- */
  (function equity() {
    var line = document.getElementById('eqLine');
    var fill = document.getElementById('eqFill');
    if (!line) return;
    // honesty: the showcased naive backtest lost money, so the curve drifts DOWN.
    var W = 460, H = 240, N = 60;
    var pts = [];
    var v = 60, drift = (190 - 60) / N; // start high (low y), end low (high y)
    for (var i = 0; i < N; i++) {
      v += drift;
      v += (Math.random() - 0.5) * 26; // chop, including a deeper drawdown mid-run
      v = Math.max(28, Math.min(220, v));
      pts.push([i / (N - 1) * W, v]);
    }
    pts[N - 1][1] = 196; // finish near the lows
    var d = smoothPath(pts);
    line.setAttribute('d', d);
    line.setAttribute('stroke', '#D96459'); // red — this run lost money
    fill.setAttribute('d', d + ' L' + W + ',' + H + ' L0,' + H + ' Z');
    if (fill.parentNode) {
      var grad = document.getElementById('eqfill');
      if (grad) grad.querySelector('stop').setAttribute('stop-color', 'rgba(244,91,105,.28)');
    }
  })();

  /* ---- Live signal badge flip ---- */
  (function signalBadge() {
    var badge = document.getElementById('signalBadge');
    if (!badge || reduceMotion) return;
    var states = [
      { t: 'hypothesis · measuring', c: 'badge--neutral' },
      { t: 'walk-forward · pending', c: 'badge--neutral' },
      { t: 'P(noise) · 21%', c: 'badge--neutral' },
      { t: 'edge · not yet proven', c: 'badge--neutral' }
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

  /* ---- Formspree-backed forms (progressive enhancement, no deps) ----
     Forms POST to their own `action` (a Formspree endpoint) so they work even
     if this script fails to load. When it does load, we intercept and submit
     via fetch() for an inline, no-redirect success/error UX. The honeypot
     `_gotcha` field + Formspree handle spam. */
  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  function setMsg(el, text, cls) {
    if (!el) return;
    el.textContent = text || '';
    el.className = 'waitlist__msg' + (cls ? ' ' + cls : '');
  }

  function wireFormspree(form, opts) {
    if (!form) return;
    var msgEl = document.getElementById(opts.msgId);
    var btn = form.querySelector('button[type="submit"]') || form.querySelector('button');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var problem = opts.validate ? opts.validate(form) : null;
      if (problem) { setMsg(msgEl, problem, 'err'); return; }

      // Endpoint must be a configured Formspree action; degrade gracefully if not.
      var endpoint = form.getAttribute('action') || '';
      if (endpoint.indexOf('formspree.io') === -1) {
        setMsg(msgEl, 'Form isn’t configured yet — email hello@kudbeequant.com.', 'err');
        return;
      }

      var origLabel = btn ? btn.textContent : '';
      if (btn) { btn.disabled = true; btn.textContent = opts.sending || 'Sending…'; }
      setMsg(msgEl, '', '');

      fetch(endpoint, {
        method: 'POST',
        body: new FormData(form),
        headers: { 'Accept': 'application/json' }
      }).then(function (res) {
        if (res.ok) {
          form.reset();
          setMsg(msgEl, opts.success, 'ok');
          return;
        }
        return res.json().then(function (d) {
          var err = (d && d.errors && d.errors.length)
            ? d.errors.map(function (x) { return x.message; }).join(' ')
            : 'Something went wrong. Please try again, or email hello@kudbeequant.com.';
          setMsg(msgEl, err, 'err');
        });
      }).catch(function () {
        setMsg(msgEl, 'Network error — please try again, or email hello@kudbeequant.com.', 'err');
      }).then(function () {
        if (btn) { btn.disabled = false; btn.textContent = origLabel; }
      });
    });
  }

  /* Contact form (name + email + message) */
  wireFormspree(document.getElementById('contactForm'), {
    msgId: 'contactMsg',
    sending: 'Sending…',
    success: 'Thanks — your message is in. We’ll reply by email soon.',
    validate: function (f) {
      var name = (f.querySelector('[name="name"]').value || '').trim();
      var email = (f.querySelector('[name="email"]').value || '').trim();
      var message = (f.querySelector('[name="message"]').value || '').trim();
      if (!name || !EMAIL_RE.test(email) || message.length < 5) {
        return 'Please add your name, a valid email, and a short message.';
      }
      return null;
    }
  });

  /* Waitlist form (email only) */
  wireFormspree(document.getElementById('waitlistForm'), {
    msgId: 'waitlistMsg',
    sending: 'Requesting…',
    success: 'You’re on the list! 🐝 Watch your inbox for your invite.',
    validate: function (f) {
      var email = (f.querySelector('[name="email"]').value || '').trim();
      if (!EMAIL_RE.test(email)) return 'Please enter a valid email address.';
      return null;
    }
  });
})();
