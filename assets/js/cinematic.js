/* =========================================================
   Kudbee Quant — cinematic scroll controller
   Lenis smooth-scroll + GSAP ScrollTrigger. Pure enhancement:
   if the vendored libs fail to load, or JS is off, the page
   renders fully (no `.cin` is added, so nothing is hidden).
   ========================================================= */
(function () {
  'use strict';

  var root = document.documentElement;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var gsap = window.gsap;
  var ScrollTrigger = window.ScrollTrigger;
  var Lenis = window.Lenis;

  // No motion libs -> leave the page in its visible, static state.
  if (!gsap || !ScrollTrigger) return;

  try {
    gsap.registerPlugin(ScrollTrigger);
    // JS is confirmed running: opt into the reveal hidden-state now.
    root.classList.add('cin');

    /* ---- Smooth scroll (Lenis), wired to GSAP's ticker + ScrollTrigger ---- */
    if (Lenis && !reduce) {
      var lenis = new Lenis({ duration: 1.1, smoothWheel: true, wheelMultiplier: 1.0 });
      lenis.on('scroll', ScrollTrigger.update);
      gsap.ticker.add(function (time) { lenis.raf(time * 1000); });
      gsap.ticker.lagSmoothing(0);
      // In-page anchor links should use Lenis so they glide, not jump.
      document.querySelectorAll('a[href^="#"]').forEach(function (a) {
        a.addEventListener('click', function (e) {
          var id = a.getAttribute('href');
          if (id && id.length > 1) {
            var t = document.querySelector(id);
            if (t) { e.preventDefault(); lenis.scrollTo(t, { offset: -70 }); }
          }
        });
      });
    }

    /* ---- Scroll reveals: toggle .is-in; CSS does the easing ---- */
    var revealEls = gsap.utils.toArray('[data-reveal]');
    revealEls.forEach(function (el) {
      ScrollTrigger.create({
        trigger: el, start: 'top 88%', once: true,
        onEnter: function () { el.classList.add('is-in'); },
      });
    });
    gsap.utils.toArray('[data-reveal-group]').forEach(function (grp) {
      grp.querySelectorAll('[data-reveal]').forEach(function (el, i) {
        el.style.setProperty('--i', i);
      });
      ScrollTrigger.create({
        trigger: grp, start: 'top 85%', once: true,
        onEnter: function () { grp.classList.add('is-in'); },
      });
    });

    /* ---- Cinematic scrubbed bits (skip under reduced motion) ---- */
    if (!reduce) {
      // Hero background layers drift slower than the scroll (parallax).
      gsap.utils.toArray('.hero__layer').forEach(function (layer) {
        var depth = parseFloat(layer.getAttribute('data-depth') || '0.25');
        gsap.to(layer, {
          yPercent: depth * 45, ease: 'none',
          scrollTrigger: { trigger: '.scene--hero', start: 'top top', end: 'bottom top', scrub: true },
        });
      });
      // Hero copy gently recedes as you scroll past it.
      var heroCopy = document.querySelector('.scene--hero .hero__copy');
      if (heroCopy) {
        gsap.to(heroCopy, {
          opacity: 0.12, yPercent: -6, ease: 'none',
          scrollTrigger: { trigger: '.scene--hero', start: 'center center', end: 'bottom top', scrub: true },
        });
      }
    }

    // After layout settles (fonts/images), recompute trigger positions.
    window.addEventListener('load', function () { ScrollTrigger.refresh(); });
    ScrollTrigger.refresh();

    // Belt-and-suspenders: if anything left a reveal stuck hidden, show it.
    setTimeout(function () {
      revealEls.forEach(function (el) {
        var r = el.getBoundingClientRect();
        if (r.top < window.innerHeight && !el.classList.contains('is-in')) {
          el.classList.add('is-in');
        }
      });
    }, 1400);
  } catch (e) {
    // Never let a motion error blank the page — revert to the static, visible state.
    root.classList.remove('cin');
  }
})();
