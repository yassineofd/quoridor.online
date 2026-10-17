/* Runs before the page is drawn: marks scripts as available and settles the display language, so the page
   never flashes in the wrong language or the wrong reading direction.

   Language order: ?lang=xx in the address (and remembered), then the visitor's saved choice, then the browser's
   own language list, then English. The language only changes what this browser displays. It is never sent to
   the game server, so players using different languages meet in the same matchmaking pool and rooms. */
(function () {
  var root = document.documentElement;
  root.classList.add('js');

  var LANGS = ['en', 'es', 'fr', 'de', 'ar'];
  var KEY = 'quoridor.lang';
  var lang = 'en';
  try {
    var asked = /[?&]lang=([a-z]{2})(?:&|#|$)/.exec(location.search);
    var saved = null;
    try { saved = localStorage.getItem(KEY); } catch (e) { /* storage blocked */ }
    if (asked && LANGS.indexOf(asked[1]) !== -1) {
      lang = asked[1];
      try { localStorage.setItem(KEY, lang); } catch (e) { /* storage blocked */ }
    } else if (saved && LANGS.indexOf(saved) !== -1) {
      lang = saved;
    } else {
      var prefs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language];
      for (var i = 0; i < prefs.length; i++) {
        var code = String(prefs[i] || '').slice(0, 2).toLowerCase();
        if (LANGS.indexOf(code) !== -1) { lang = code; break; }
      }
    }
  } catch (e) { lang = 'en'; }

  window.QUORIDOR_LANG = lang;
  if (lang !== 'en') {
    root.lang = lang;
    root.dir = lang === 'ar' ? 'rtl' : 'ltr';
    // Hide the English text until the translation has been applied (i18n.js removes this; the timer is a safety net).
    root.classList.add('i18n-pending');
    setTimeout(function () { root.classList.remove('i18n-pending'); }, 3000);
  }
})();
