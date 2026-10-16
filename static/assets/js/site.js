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

  // Close when the viewport grows to the desktop layout.
  var mq = window.matchMedia('(min-width: 1024px)');
  var onChange = function () { if (mq.matches) setOpen(false, false); };
  if (mq.addEventListener) mq.addEventListener('change', onChange);
})();
