/* The tournaments page (/tournaments/): the next tournaments with their sign-up, the ones in progress and their brackets.

   A tournament starts every 8 hours, in two sizes (8 and 16 players); the server (server/tournaments.py) draws the bracket and
   makes a room for every match. This page lists them, signs the player up (the entry token stays in this browser, see
   online.js), follows the tournaments the player is in, and takes them to their match as soon as it is ready.
   Everything the server says arrives as data; the words are this site's own messages (translations/js-en.json), so each
   visitor reads the page in their own language. Times are shown in the visitor's own time zone.                            */
(function () {
  'use strict';
  // Display names: letters and digits of any alphabet, plus spaces, dots, dashes and underscores (same rule as valid_username in server/rooms.py).
  var USERNAME_RE = /^[\p{L}\p{N}\p{M} _.\-]{2,20}$/u;
  var Online = window.QuoridorOnline, I18n = window.QuoridorI18n, Profile = window.QuoridorProfile;
  var shell = document.querySelector('[data-tournaments]');
  if (!shell || !Online || !shell.hasAttribute('data-live')) return;
  function t(key, params) { return I18n ? I18n.t(key, params) : key; }

  var upcomingEl = shell.querySelector('[data-tour-upcoming]');
  var recentEl = shell.querySelector('[data-tour-recent]');
  var youEl = shell.querySelector('[data-tour-you]');
  var loadingEl = shell.querySelector('[data-tour-loading]');
  var errorEl = shell.querySelector('[data-error]');
  var errorText = shell.querySelector('[data-error-text]');
  var retryBtn = shell.querySelector('[data-retry]');
  var emptyUpcoming = shell.querySelector('[data-tour-empty-upcoming]');
  var emptyRecent = shell.querySelector('[data-tour-empty-recent]');
  var focusId = new URLSearchParams(location.search).get('t');

  var offset = 0;              // server time minus this device's time, in seconds
  var list = [];               // the summaries the server last listed
  var cards = {};              // id -> { el, parts... } for the open tournaments
  var results = {};            // id -> { el, open, view } for the others
  var watchers = {};           // id -> the running watchTournament
  var views = {};              // id -> the last full view of a tournament this player follows or has opened
  var redirectTimer = null, pollTimer = null, tickTimer = null;

  function h(tag, attrs, kids) {
    var n = document.createElement(tag);
    for (var k in attrs || {}) {
      if (k === 'text') n.textContent = attrs[k];
      else if (k === 'class') n.className = attrs[k];
      else n.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) { if (c) n.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); });
    return n;
  }
  function icon(name) {
    var s = document.createElement('span');
    s.className = 'tour-icon'; s.setAttribute('aria-hidden', 'true');
    if (window.QuoridorIcons) s.innerHTML = window.QuoridorIcons.svg(name);
    return s;
  }
  function now() { return Date.now() / 1000 + offset; }
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
  function sizeTitle(size) { return t('tour.size', { n: size }); }

  // ---- loading ----------------------------------------------------------------------------
  function showError(err) {
    if (!errorEl) return;
    errorEl.hidden = false;
    errorText.textContent = I18n ? I18n.errorText(err) : (err && err.message);
  }
  function load() {
    return Online.tournaments().then(function (res) {
      if (errorEl) errorEl.hidden = true;
      offset = res.now - Date.now() / 1000;
      list = res.tournaments;
      if (loadingEl) loadingEl.hidden = true;
      sync();
    }, function (err) {
      if (loadingEl) loadingEl.hidden = true;
      showError(err);
    });
  }
  function schedulePoll() {
    clearTimeout(pollTimer);
    pollTimer = setTimeout(function () { load().then(schedulePoll, schedulePoll); }, 15000);
  }
  if (retryBtn) retryBtn.addEventListener('click', function () { if (errorEl) errorEl.hidden = true; load(); });

  // ---- following the tournaments this player is in ---------------------------------------------
  // Every tournament with an entry token in this browser, and the one in the address, is followed in full.
  function follow(id, token) {
    if (watchers[id]) return;
    watchers[id] = Online.watchTournament(id, token, {
      onState: function (view) { views[id] = view; offset = view.now - Date.now() / 1000; viewChanged(id); },
      onGone: function () { if (token) Online.forgetEntry(id); unfollow(id); delete views[id]; load(); }
    });
  }
  function unfollow(id) { if (watchers[id]) { watchers[id].stop(); delete watchers[id]; } }

  function sync() {
    var ids = {};
    list.forEach(function (s) { ids[s.id] = true; });
    // Entries of tournaments the server no longer lists are forgotten.
    Online.entries().forEach(function (e) {
      if (!ids[e.id]) { Online.forgetEntry(e.id); return; }
      var s = list.filter(function (x) { return x.id === e.id; })[0];
      if (s.status === 'open' || s.status === 'playing') follow(e.id, e.token);
    });
    list.forEach(function (s) {
      var entry = Online.loadEntry(s.id);
      if (s.id === focusId || (entry && s.status !== 'open')) follow(s.id, entry && entry.token);
    });
    paintLists();
  }

  function viewChanged(id) {
    var view = views[id];
    var entry = Online.loadEntry(id);
    // The player's own view says where they stand and, when a match is ready, where to play it.
    if (entry && view.you === null && view.status === 'open') {   // withdrawn elsewhere, or the server forgot the entry
      Online.forgetEntry(id);
    }
    if (results[id]) paintResult(id);
    paintYou();
    paintLists();
  }

  // ---- the banner about the player's own match ------------------------------------------------
  function myView() {
    // The tournament this player is in that matters most right now: one with a match ready, else one under way, else one they have won or left.
    var best = null;
    Object.keys(views).forEach(function (id) {
      var v = views[id], you = v.you;
      if (!you || !Online.loadEntry(id)) return;
      var r = you.match ? 4 : (v.status === 'playing' && you.state === 'in') ? 3 : you.state === 'champion' ? 2 : (v.status === 'playing' && you.state === 'out') ? 1 : 0;
      if (r && (!best || r > best.r)) best = { r: r, view: v };
    });
    return best && best.view;
  }

  var shownMatch = null, shownKey = null;
  function paintYou(force) {
    var v = myView();
    // Only draw it again when what it says changes (a screen reader would read the whole note out each time).
    var key = v ? v.id + ':' + v.you.state + ':' + (v.you.match ? v.you.match.roomId : '') : '';
    if (!force && key === shownKey) return;
    shownKey = key;
    clearInterval(redirectTimer); redirectTimer = null;
    youEl.textContent = '';
    document.title = baseTitle;
    if (!v) { youEl.hidden = true; shownMatch = null; return; }
    var you = v.you, match = you.match;
    youEl.hidden = false;
    var box = h('div', { 'class': 'notice tour-you' + (match ? ' tour-you--match' : '') });
    box.appendChild(icon(match ? 'play' : you.state === 'champion' ? 'crown' : 'trophy'));
    var body = h('div', {});
    if (match) {
      body.appendChild(h('h2', { text: t('tour.yourMatch', { name: match.opponent }) }));
      body.appendChild(h('p', { text: Online.roundName(match.round, v.rounds) + ' · ' + t('tour.joinWithin') }));
      var left = h('span', { 'class': 'small text-muted', 'aria-hidden': 'true' });   // (a count down is not read out each second)
      var go = h('a', { 'class': 'btn btn--primary', href: Online.roomUrl(match.roomId) }, [icon('play'), t('tour.playNow')]);
      go.addEventListener('click', function (e) { e.preventDefault(); enterMatch(v, match); });
      body.appendChild(h('div', { 'class': 'btn-row' }, [go, left]));
      document.title = t('tour.titleReady', { title: baseTitle });
      // The page takes the player to the game after a moment, as an arena would; the button skips the wait.
      if (shownMatch !== match.roomId) { shownMatch = match.roomId; countdownTo = Date.now() + 6000; }
      var tick = function () {
        var n = Math.max(0, Math.ceil((countdownTo - Date.now()) / 1000));
        left.textContent = t('tour.taking', { n: n });
        if (n <= 0) { clearInterval(redirectTimer); enterMatch(v, match); }
      };
      tick(); redirectTimer = setInterval(tick, 1000);
    } else if (you.state === 'champion') {
      body.appendChild(h('h2', { text: t('tour.youChampion') }));
    } else if (you.state === 'out') {
      body.appendChild(h('h2', { text: t('tour.youOut') }));
      body.appendChild(h('p', { text: t('tour.followBracket') }));
    } else {
      body.appendChild(h('h2', { text: t('tour.advanced') }));
      body.appendChild(h('p', { text: t('tour.nextMatchSoon') }));
    }
    box.appendChild(body);
    youEl.appendChild(box);
  }
  var baseTitle = document.title, countdownTo = 0;

  function enterMatch(view, match) {
    Online.saveSeat(match.roomId, { token: match.token, seat: match.seat, name: view.you.name, via: 'tournament' });
    window.location.href = Online.roomUrl(match.roomId);
  }

  // ---- the open tournaments: sign-up -------------------------------------------------------------
  function failureText(err) { return I18n ? I18n.errorText(err) : (err && err.message); }

  function buildCard(s) {
    var title = h('h3', { 'class': 'tour-card__title' });
    var startLine = h('p', { 'class': 'tour-card__when' });
    var left = h('span', { 'class': 'tour-card__left', 'data-countdown': '' });
    var seats = h('p', { 'class': 'tour-card__seats' });
    var names = h('ul', { 'class': 'chip-list tour-names', 'aria-label': t('tour.signedUpList') });
    var foot = h('div', { 'class': 'tour-card__foot' });
    var el = h('article', { 'class': 'card tour-card', 'data-id': s.id }, [
      h('div', { 'class': 'tour-card__head' }, [h('span', { 'class': 'icon-badge' }, [icon('trophy')]), h('div', {}, [title, startLine])]),
      seats, names, foot
    ]);
    var card = { el: el, title: title, startLine: startLine, left: left, seats: seats, names: names, foot: foot, mode: null, summary: s };
    startLine.appendChild(document.createTextNode('')); startLine.appendChild(left);
    return card;
  }

  function paintCard(card, s) {
    card.summary = s;
    card.title.textContent = sizeTitle(s.size);
    card.startLine.firstChild.nodeValue = t('tour.starts', { when: when(s.start) }) + ' · ';
    card.seats.textContent = t('tour.seats', { n: s.players, size: s.size });
    card.names.textContent = '';
    (s.names || []).forEach(function (n) { card.names.appendChild(h('li', { text: n })); });
    card.names.hidden = !(s.names && s.names.length);
    var entry = Online.loadEntry(s.id);
    var mode = entry ? 'in' : s.players >= s.size ? 'full' : 'form';
    if (card.mode !== mode) {
      card.mode = mode;
      card.foot.textContent = '';
      if (mode === 'form') card.foot.appendChild(signUpForm(card, s));
      else if (mode === 'full') card.foot.appendChild(h('p', { 'class': 'text-muted', text: t('tour.full') }));
      else card.foot.appendChild(withdrawBlock(card, s, entry));
    } else if (mode === 'in') {
      var strong = card.foot.querySelector('[data-you-name]');
      if (strong) strong.textContent = t('tour.youAreIn', { name: entry.name });
    }
    tick();
  }

  var formSeq = 0;
  function signUpForm(card, s) {
    var id = 'tour-name-' + (++formSeq);
    var input = h('input', { 'class': 'input', id: id, name: 'username', type: 'text', autocomplete: 'nickname', maxlength: '20', spellcheck: 'false', required: '' });
    var error = h('div', { 'class': 'field-error', role: 'alert', hidden: '' });
    var button = h('button', { 'class': 'btn btn--primary', type: 'submit' }, [icon('plus'), t('tour.signUp')]);
    var form = h('form', { novalidate: '', 'class': 'tour-form' }, [
      h('div', { 'class': 'field' }, [h('label', { 'for': id, text: t('tour.nameLabel') }), input, error]),
      button
    ]);
    if (Profile && Profile.name()) input.value = Profile.name();
    input.addEventListener('input', function () { error.hidden = true; input.removeAttribute('aria-invalid'); });
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var name = input.value.trim().normalize('NFC');
      if (!USERNAME_RE.test(name)) {
        error.textContent = t('err.bad-username'); error.hidden = false;
        input.setAttribute('aria-invalid', 'true'); input.focus();
        return;
      }
      if (Profile) Profile.setName(name);
      button.disabled = true;
      Online.joinTournament(s.id, name).then(function (res) {
        Online.saveEntry(s.id, { token: res.token, name: name, start: s.start });
        button.disabled = false;
        unfollow(s.id);               // (a watcher without the token cannot say where the player stands)
        follow(s.id, res.token);
        card.mode = null;
        load().then(function () { var me = card.foot.querySelector('[data-you-name]'); if (me) me.focus(); });
      }, function (err) {
        button.disabled = false;
        error.textContent = failureText(err); error.hidden = false;
        input.setAttribute('aria-invalid', 'true'); input.focus();
        if (err.code === 'tournament-full' || err.code === 'tournament-closed') load();
      });
    });
    return form;
  }

  function withdrawBlock(card, s, entry) {
    var msg = h('p', { 'class': 'tour-card__in', 'data-you-name': '', tabindex: '-1', text: t('tour.youAreIn', { name: entry.name }) });
    var out = h('button', { 'class': 'btn btn--secondary', type: 'button' }, [icon('logout'), t('tour.withdraw')]);
    out.addEventListener('click', function () {
      if (!window.confirm(t('tour.confirmWithdraw'))) return;
      out.disabled = true;
      var e = Online.loadEntry(s.id);
      Online.leaveTournament(s.id, e && e.token).then(done, function (err) {
        out.disabled = false;
        if (err.code === 'not-signed-up' || err.code === 'no-tournament') return done();
        showError(err);
      });
      function done() {
        Online.forgetEntry(s.id);
        unfollow(s.id); delete views[s.id];
        card.mode = null;
        load();
        paintYou();
      }
    });
    return h('div', { 'class': 'tour-card__in-row' }, [msg, out]);
  }

  // ---- the brackets -------------------------------------------------------------------------
  function bracketEl(view) {
    var players = view.players;
    var rounds = h('div', { 'class': 'bracket' });
    view.bracket.forEach(function (round, r) {
      var col = h('section', { 'class': 'bracket-round', 'aria-label': Online.roundName(r, view.rounds) });
      col.appendChild(h('h4', { text: Online.roundName(r, view.rounds) }));
      var ol = h('ol', { 'class': 'bracket-matches' });
      round.forEach(function (m) {
        var li = h('li', { 'class': 'bracket-match is-' + m.state });
        [m.a, m.b].forEach(function (p) {
          var cls = 'bracket-player' + (p === null ? ' is-tbd' : '') + (m.state === 'done' ? (p === m.winner ? ' is-winner' : ' is-loser') : '');
          var name = p === null ? t('tour.tbd') : players[p].name;
          var row = h('div', { 'class': cls }, [h('span', { 'class': 'bracket-name', text: name })]);
          if (m.state === 'done' && p === m.winner) {
            var mark = h('span', { 'class': 'bracket-mark', text: t(m.by === 'walkover' ? 'tour.walkover' : 'tour.won') });
            row.appendChild(mark);
          }
          li.appendChild(row);
        });
        if (m.state === 'live') li.appendChild(h('div', { 'class': 'bracket-live', text: t('tour.playingNow') }));
        ol.appendChild(li);
      });
      col.appendChild(ol);
      rounds.appendChild(col);
    });
    return rounds;
  }

  function statusLine(s, view) {
    if (s.status === 'cancelled') return t('tour.cancelled', { n: s.players, size: s.size });
    if (s.status === 'finished') return t('tour.champion', { name: s.champion });
    var r = view ? view.round : s.round;
    return t('tour.inProgress', { round: r === null || r === undefined ? '' : Online.roundName(r, s.rounds) });
  }

  function buildResult(s) {
    var title = h('h3', { 'class': 'tour-card__title' });
    var line = h('p', { 'class': 'tour-card__when' });
    var toggle = h('button', { 'class': 'btn btn--secondary btn--sm', type: 'button', 'aria-expanded': 'false' });
    var body = h('div', { 'class': 'tour-card__bracket', hidden: '' });
    var el = h('article', { 'class': 'card tour-card', 'data-id': s.id }, [
      h('div', { 'class': 'tour-card__head' }, [h('span', { 'class': 'icon-badge' }, [icon(s.status === 'finished' ? 'crown' : 'trophy')]), h('div', {}, [title, line])]),
      h('div', { 'class': 'btn-row' }, [toggle]), body
    ]);
    var r = { el: el, title: title, line: line, toggle: toggle, body: body, open: false, summary: s };
    toggle.addEventListener('click', function () {
      r.open = !r.open;
      if (r.open) follow(s.id, (Online.loadEntry(s.id) || {}).token);
      paintResult(s.id);
    });
    return r;
  }

  function paintResult(id) {
    var r = results[id], s = r.summary, view = views[id];
    r.title.textContent = sizeTitle(s.size);
    r.line.textContent = when(s.start) + ' · ' + statusLine(s, view);
    r.toggle.setAttribute('aria-expanded', String(r.open));
    r.toggle.textContent = t(r.open ? 'tour.hideBracket' : 'tour.showBracket');
    r.body.hidden = !r.open;
    r.body.textContent = '';
    if (r.open) {
      if (view && view.bracket.length) r.body.appendChild(bracketEl(view));
      else if (view && view.status === 'cancelled') r.body.appendChild(namesList(view));
      else r.body.appendChild(h('p', { 'class': 'text-muted', text: t('tour.loadingBracket') }));
    }
    r.toggle.hidden = s.status === 'cancelled' && !(view && view.players.length);
  }
  function namesList(view) {
    var ul = h('ul', { 'class': 'chip-list tour-names' });
    view.players.forEach(function (p) { ul.appendChild(h('li', { text: p.name })); });
    return ul;
  }

  // ---- the two lists -----------------------------------------------------------------------
  function paintLists() {
    var open = list.filter(function (s) { return s.status === 'open'; });
    var others = list.filter(function (s) { return s.status !== 'open'; }).reverse();   // newest first
    // Open tournaments: one card each, kept between updates so a name being typed is not lost.
    Object.keys(cards).forEach(function (id) {
      if (!open.some(function (s) { return s.id === id; })) { cards[id].el.remove(); delete cards[id]; }
    });
    open.forEach(function (s, i) {
      var card = cards[s.id];
      if (!card) { card = cards[s.id] = buildCard(s); }
      paintCard(card, s);
      // Put it in its place only when it is not there: moving a card would take the keyboard focus out of its name field.
      if (upcomingEl.children[i] !== card.el) upcomingEl.insertBefore(card.el, upcomingEl.children[i] || null);
    });
    emptyUpcoming.hidden = open.length > 0;
    Object.keys(results).forEach(function (id) {
      if (!others.some(function (s) { return s.id === id; })) { results[id].el.remove(); delete results[id]; }
    });
    others.forEach(function (s, i) {
      var r = results[s.id];
      if (!r) {
        r = results[s.id] = buildResult(s);
        var entry = Online.loadEntry(s.id);
        if (s.id === focusId || (entry && s.status === 'playing')) r.open = true;
      }
      r.summary = s;
      paintResult(s.id);
      if (recentEl.children[i] !== r.el) recentEl.insertBefore(r.el, recentEl.children[i] || null);
    });
    emptyRecent.hidden = others.length > 0;
  }

  // ---- the clock ---------------------------------------------------------------------------
  function tick() {
    Object.keys(cards).forEach(function (id) {
      var c = cards[id], s = c.summary;
      var secs = s.start - now();
      c.left.textContent = secs > 0 ? t('tour.startsIn', { left: clock(secs) }) : t('tour.starting');
    });
    if (list.some(function (s) { return s.status === 'open' && s.start - now() < -2; })) load();   // the start has passed: ask what happened
  }

  if (I18n) I18n.onChange(function () {
    baseTitle = document.title;
    Object.keys(cards).forEach(function (id) {
      var c = cards[id], field = c.foot.querySelector('input'), typed = field ? field.value : null;
      c.mode = null; paintCard(c, c.summary);                       // (the form is written again in the new language)
      var again = c.foot.querySelector('input');
      if (again && typed !== null) again.value = typed;             // what was typed so far stays
    });
    Object.keys(results).forEach(paintResult);
    paintYou(true);
  });

  load().then(function () { schedulePoll(); });
  tickTimer = setInterval(tick, 1000);
  window.addEventListener('pagehide', function () {
    Object.keys(watchers).forEach(unfollow);
    clearInterval(tickTimer); clearTimeout(pollTimer); clearInterval(redirectTimer);
  });
})();
