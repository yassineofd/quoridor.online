/* Tournaments on the other pages of the site (not /tournaments/ itself, which has its own script).

   1. The tournament strips (home, Play, Variants) carry a line that is filled in here: when the next tournament starts and how
      many places are taken. Without a game server the line stays hidden and the strip keeps its plain text.
   2. A player who has signed up (the entry token is in this browser, see online.js) gets a short reminder on each page while they
      wait, and when their match is ready a note with a button, wherever they are on the site (a room page included, so that a
      player looking at the result of a match does not miss the next one). A match not opened within a few minutes counts as lost,
      which is why the note is here and not only on the tournaments page.                                                     */
(function (root) {
  'use strict';
  var Online = root.QuoridorOnline;
  var I18n = root.QuoridorI18n;
  var doc = root.document;
  function t(key, params) { return I18n ? I18n.t(key, params) : key; }
  if (!Online) return;

  var lines = doc.querySelectorAll('[data-tour-live]');
  var mine = Online.entries();
  if (!lines.length && !mine.length) return;

  var offset = 0, list = [], note = null, offer = null, noteTimer = null, offerFor = null, watchers = {};
  var inRoom = /\/room\/[A-Za-z0-9_-]+\/?$/.test(root.location.pathname);   // (no reminders in the middle of a game, but a match that is ready is still announced)

  function h(tag, attrs, kids) {
    var n = doc.createElement(tag);
    for (var k in attrs || {}) {
      if (k === 'text') n.textContent = attrs[k];
      else if (k === 'class') n.className = attrs[k];
      else n.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) { if (c) n.appendChild(typeof c === 'string' ? doc.createTextNode(c) : c); });
    return n;
  }
  function remove(n) { if (n && n.parentNode) n.parentNode.removeChild(n); }
  function when(start) {
    try {
      return new Date(start * 1000).toLocaleString(I18n ? I18n.language() : undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
    } catch (e) { return new Date(start * 1000).toLocaleString(); }
  }
  function clock(seconds) {
    seconds = Math.max(0, Math.floor(seconds));
    var hh = Math.floor(seconds / 3600), mm = Math.floor(seconds / 60) % 60, ss = seconds % 60;
    return (hh ? hh + ':' + ('0' + mm).slice(-2) : mm) + ':' + ('0' + ss).slice(-2);
  }

  // ---- 1. the strips --------------------------------------------------------------------
  function paintLines() {
    var open = list.filter(function (s) { return s.status === 'open'; });
    if (!open.length) { Array.prototype.forEach.call(lines, function (el) { el.hidden = true; }); return; }
    var start = Math.min.apply(null, open.map(function (s) { return s.start; }));
    var taken = { 8: 0, 16: 0 };
    open.forEach(function (s) { if (s.start === start) taken[s.size] = s.players; });
    var text = t('tour.nextLine', { when: when(start), left: clock(start - (Date.now() / 1000 + offset)) }) + ' ' + t('tour.seatsLine', { a: taken[8], b: taken[16] });
    Array.prototype.forEach.call(lines, function (el) { el.textContent = text; el.hidden = false; });
  }

  // ---- 2. the player's own tournaments ------------------------------------------------------
  function showNote(text) {
    remove(note); clearTimeout(noteTimer);
    note = h('div', { 'class': 'bg-search tour-chip', role: 'status' }, [
      h('span', { 'class': 'bg-search__dot', 'aria-hidden': 'true' }),
      h('span', { text: text }),
      h('a', { 'class': 'btn btn--secondary btn--sm', href: Online.tournamentUrl(), text: t('tour.view') })
    ]);
    doc.body.appendChild(note);
    noteTimer = setTimeout(function () { remove(note); note = null; }, 12000);   // a reminder, not a fixture
  }

  function hideOffer() { remove(offer); offer = null; offerFor = null; }

  function showOffer(view) {
    var match = view.you.match;
    if (offerFor === match.roomId) return;
    if (inRoom && root.location.pathname.indexOf(match.roomId) !== -1) return;   // this is the match being played right here
    hideOffer();
    offerFor = match.roomId;
    remove(note); note = null;
    var play = h('button', { 'class': 'btn btn--primary', type: 'button', text: t('tour.playNow') });
    play.addEventListener('click', function () {
      Online.saveSeat(match.roomId, { token: match.token, seat: match.seat, name: view.you.name, via: 'tournament' });
      root.location.href = Online.roomUrl(match.roomId);
    });
    var gameOn = !!doc.querySelector('svg.board') && !doc.querySelector('.result:not([hidden])');   // a finished game is no reason to hesitate
    offer = h('div', { 'class': 'match-offer tour-offer', role: 'group', 'aria-label': t('tour.offerLabel') }, [
      h('p', { 'class': 'match-offer__title', role: 'alert', text: t('tour.yourMatch', { name: match.opponent }) }),
      h('p', { 'class': 'match-offer__note small text-muted', text: t(gameOn ? 'watch.endsGame' : 'tour.joinWithin') }),
      h('div', { 'class': 'btn-row' }, [play, h('a', { 'class': 'btn btn--secondary', href: Online.tournamentUrl(view.id), text: t('tour.view') })])
    ]);
    doc.body.appendChild(offer);
  }

  function follow(entry, summary) {
    if (watchers[entry.id]) return;
    watchers[entry.id] = Online.watchTournament(entry.id, entry.token, {
      onState: function (view) {
        if (view.status !== 'playing' || !view.you) {
          if (watchers[entry.id] && view.status !== 'playing') { watchers[entry.id].stop(); delete watchers[entry.id]; }
          hideOffer();
          return;
        }
        if (view.you.match) showOffer(view); else hideOffer();
      },
      onGone: function () { Online.forgetEntry(entry.id); hideOffer(); }
    });
  }

  function handleEntries() {
    mine.forEach(function (entry) {
      var s = list.filter(function (x) { return x.id === entry.id; })[0];
      if (!s) { Online.forgetEntry(entry.id); return; }
      if (s.status === 'open') { if (!inRoom) showNote(t('tour.watchIn', { when: when(s.start) })); }
      else if (s.status === 'playing') follow(entry, s);
      else if (s.status === 'cancelled') { showNote(t('tour.cancelled', { n: s.players, size: s.size })); Online.forgetEntry(entry.id); }
    });
  }

  Online.tournaments().then(function (res) {
    offset = res.now - Date.now() / 1000;
    list = res.tournaments;
    paintLines();
    handleEntries();
    if (lines.length) setInterval(paintLines, 1000);
  }, function () { /* no game server on this site, or it cannot be reached: nothing to show */ });

  if (I18n) I18n.onChange(function () { paintLines(); });
  root.addEventListener('pagehide', function () { Object.keys(watchers).forEach(function (id) { watchers[id].stop(); }); });
})(window);
