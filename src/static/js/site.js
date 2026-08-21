/* kokopazu.com — site.js (no dependencies) */
(function () {
  'use strict';
  var html = document.documentElement;
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---- language banner (no forced redirect) ---- */
  try {
    var banner = document.getElementById('langBanner');
    if (banner) {
      var other = banner.getAttribute('data-other');
      var navLang = (navigator.language || '').toLowerCase();
      var prefersKo = navLang.indexOf('ko') === 0;
      var dismissed = localStorage.getItem('kokopazu-lang-banner') === '1';
      var chosen = localStorage.getItem('kokopazu-lang');
      var mismatch = (html.lang === 'ko' && !prefersKo && other === 'en') || (html.lang === 'en' && prefersKo && other === 'ko');
      if (mismatch && !dismissed && !chosen) banner.hidden = false;
      var closeBtn = banner.querySelector('[data-close]');
      if (closeBtn) closeBtn.addEventListener('click', function () { banner.hidden = true; try { localStorage.setItem('kokopazu-lang-banner', '1'); } catch (e) {} });
    }
    document.querySelectorAll('[data-lang-link]').forEach(function (a) {
      a.addEventListener('click', function () { try { localStorage.setItem('kokopazu-lang', a.getAttribute('data-lang-link')); } catch (e) {} });
    });
  } catch (e) {}

  /* ---- presskit inline language toggle (?lang=en|ko) ---- */
  try {
    if (document.body.classList.contains('page-presskit')) {
      var q = new URLSearchParams(location.search).get('lang');
      var saved = localStorage.getItem('kokopazu-lang');
      var l = q || saved || ((navigator.language || '').toLowerCase().indexOf('ko') === 0 ? 'ko' : 'en');
      html.lang = (l === 'ko') ? 'ko' : 'en';
      document.querySelectorAll('[data-lang-link]').forEach(function (a) { a.classList.toggle('active', a.getAttribute('data-lang-link') === html.lang); });
    }
  } catch (e) {}

  /* ---- header ---- */
  var top = document.getElementById('top');
  if (top) {
    var onScroll = function () { top.classList.toggle('solid', (window.scrollY || 0) > 40); };
    addEventListener('scroll', onScroll, { passive: true }); onScroll();
  }

  /* ---- hero video: desktop only, starts after page load; mobile/slow/reduced-motion keep the poster ---- */
  var hv = document.getElementById('heroVideo');
  if (hv) {
    var conn = navigator.connection || {};
    var slow = conn.saveData || /(^|-)2g$|^3g$/.test(conn.effectiveType || '');
    var small = window.innerWidth <= 720;
    if (reduce || slow || small) { hv.removeAttribute('autoplay'); }
    else {
      var startHero = function () {
        var src = hv.getAttribute('data-src'); if (!src) return;
        var s = document.createElement('source'); s.src = src; s.type = 'video/mp4'; hv.appendChild(s); hv.load();
        var p = hv.play(); if (p && p.catch) p.catch(function () {});
      };
      if (document.readyState === 'complete') setTimeout(startHero, 300);
      else addEventListener('load', function () { setTimeout(startHero, 300); }, { once: true });
    }
  }

  /* ---- reveal on scroll ---- */
  var reveals = document.querySelectorAll('.reveal');
  if (reduce || !('IntersectionObserver' in window)) { reveals.forEach(function (el) { el.classList.add('in'); }); }
  else {
    var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }); }, { rootMargin: '0px 0px -8% 0px' });
    reveals.forEach(function (el) { io.observe(el); });
  }

  /* ---- hover clips (desktop pointer only) ---- */
  if (!reduce && window.matchMedia && matchMedia('(hover:hover) and (pointer:fine)').matches) {
    document.querySelectorAll('.card, .tile').forEach(function (el) {
      var v = el.querySelector('video[data-src]'); if (!v) return;
      el.addEventListener('mouseenter', function () {
        if (!v.getAttribute('src')) { v.src = v.getAttribute('data-src'); }
        var p = v.play(); if (p && p.then) p.then(function () { v.classList.add('ready'); }).catch(function () {});
      });
      el.addEventListener('mouseleave', function () { v.pause(); v.classList.remove('ready'); });
    });
  }

  /* ---- lite YouTube ---- */
  document.querySelectorAll('.yt[data-yt]').forEach(function (box) {
    var id = box.getAttribute('data-yt');
    var go = function () {
      var f = document.createElement('iframe');
      f.src = 'https://www.youtube-nocookie.com/embed/' + id + '?autoplay=1&rel=0';
      f.title = 'Save Princess Torosso trailer';
      f.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
      f.allowFullscreen = true;
      box.innerHTML = ''; box.appendChild(f); box.classList.add('playing');
    };
    var btn = box.querySelector('.yt-play');
    (btn || box).addEventListener('click', go);
  });
})();
