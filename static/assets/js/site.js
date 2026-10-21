/* Light / dark theme switch. head.js applies the saved choice before the first paint; this only handles the clicks. */
(function () {
  var root = document.documentElement;
  var buttons = document.querySelectorAll('[data-theme-toggle]');
  if (!buttons.length) return;
  var meta = document.querySelector('meta[name="theme-color"]');

  function sync() {
    var light = root.getAttribute('data-theme') === 'light';
    Array.prototype.forEach.call(buttons, function (b) { b.setAttribute('aria-pressed', String(light)); });
    if (meta) meta.setAttribute('content', light ? '#F4F7FB' : '#0B1220');
  }
  Array.prototype.forEach.call(buttons, function (b) {
    b.addEventListener('click', function () {
      var light = root.getAttribute('data-theme') !== 'light';
      if (light) root.setAttribute('data-theme', 'light'); else root.removeAttribute('data-theme');
      try { localStorage.setItem('quoridor.theme', light ? 'light' : 'dark'); } catch (e) { /* storage blocked */ }
      sync();
    });
  });
  sync();
})();

/* Accessible mobile menu: aria-expanded toggle, Esc to close, focus returns to the toggle. */
(function () {
  var toggle = document.getElementById('menu-toggle');
  var nav = document.getElementById('site-nav');
  if (!toggle || !nav) return;

  function setOpen(open, returnFocus) {
    nav.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    if (!open && returnFocus) toggle.focus();
  }

  toggle.addEventListener('click', function () {
    var open = toggle.getAttribute('aria-expanded') !== 'true';
    setOpen(open, false);
    if (open) {
      var first = nav.querySelector('a');
      if (first) first.focus();
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && nav.classList.contains('is-open')) setOpen(false, true);
    // Keep Tab cycling between the menu links and the toggle while the panel is open.
    if (e.key === 'Tab' && nav.classList.contains('is-open')) {
      var links = Array.prototype.slice.call(nav.querySelectorAll('a'));
      var active = document.activeElement;
      if (e.shiftKey && active === links[0]) { e.preventDefault(); toggle.focus(); }
      else if (!e.shiftKey && active === toggle) { e.preventDefault(); links[0].focus(); }
    }
  });

  // On small screens the article table of contents starts collapsed.
  var toc = document.querySelector('.toc');
  if (toc && !window.matchMedia('(min-width: 1024px)').matches) toc.removeAttribute('open');

  // Close when the viewport grows to the desktop layout (the same width as the header breakpoint in styles.css).
  var mq = window.matchMedia('(min-width: 1200px)');
  var onChange = function () { if (mq.matches) setOpen(false, false); };
  if (mq.addEventListener) mq.addEventListener('change', onChange);
})();
