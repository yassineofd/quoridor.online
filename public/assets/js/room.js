/* Private room page (/room/<id>/): lobby, waiting, joining, the synchronized game and the error states.

   The server is authoritative. This page keeps a long-poll session open, mirrors the server's
   state into the shared game screen, and sends moves as requests the server may refuse.
   A room plays the classic game or a variant (Wallrush, Pointrush for 2 to 4 players, a custom game): the room says which,
   and a room with more than two seats shows a lobby of who has joined until the last seat is taken.
   Append ?preview=<state> to see the other designed screens with sample data (no server needed). */
(function () {
  var STATES = ['waiting', 'join', 'starting', 'reconnecting', 'invalid', 'full', 'expired', 'unavailable', 'left', 'game'];
  var PREVIEWABLE = STATES.filter(function (s) { return s !== 'game'; });
  // Display names: letters and digits of any alphabet, plus spaces, dots, dashes and underscores (same rule as valid_username in server/rooms.py).
  var USERNAME_RE = /^[\p{L}\p{N}\p{M} _.\-]{2,20}$/u;
  var I18n = window.QuoridorI18n;
  function t(key, params) { return I18n ? I18n.t(key, params) : key; }
  var params = new URLSearchParams(window.location.search);
  var preview = params.get('preview');
  var isPreview = PREVIEWABLE.indexOf(preview) !== -1;
  var Online = window.QuoridorOnline;
  var Profile = window.QuoridorProfile;
  var shell = document.querySelector('[data-room-shell]');
  var live = !!shell && shell.hasAttribute('data-live');
  var previewNote = document.querySelector('[data-preview-note]');
  var linkEl = document.getElementById('invite-link');
  var codeEl = document.getElementById('invite-code');
  var status = document.getElementById('copy-status');

  var current = null;
  function show(state) {
    var changed = state !== current;
    current = state;
    Array.prototype.forEach.call(document.querySelectorAll('[data-state]'), function (p) {
      p.hidden = p.getAttribute('data-state') !== state;
    });
    if (shell) shell.classList.toggle('is-game', state === 'game');
    var heading = document.querySelector('[data-state="' + state + '"] h1:not([hidden])');
    if (heading && changed && state !== 'game') heading.focus();
  }

  // ---- copy buttons -----------------------------------------------------------------------
  function copyText(text) {
    function done() { status.textContent = t('room.copied'); }
    function fail() { status.textContent = t('room.copyFailed'); }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, fail);
    else fail();
  }
  Array.prototype.forEach.call(document.querySelectorAll('[data-copy]'), function (btn) {
    btn.addEventListener('click', function () {
      var target = document.getElementById(btn.getAttribute('data-copy'));
      if (target && status) copyText(target.textContent.trim());
    });
  });

  // ---- design preview (sample data) ------------------------------------------------------
  if (isPreview) {
    if (previewNote) previewNote.hidden = false;
    if (linkEl) linkEl.textContent = Online.roomUrl('EXAMPLE-ROOM-ID');
    if (codeEl) codeEl.textContent = 'K7M2QX';
    show(preview);
    Array.prototype.forEach.call(document.querySelectorAll('[data-leave]'), function (btn) {
      btn.addEventListener('click', function () {
        if (window.confirm(t('room.confirmLeavePreview'))) window.location.href = window.location.pathname + '?preview=left';
      });
    });
    return;
  }

  var roomId = decodeURIComponent((window.location.pathname.match(/\/room\/([^/]+)/) || [])[1] || '');
  if (!live || !roomId) { show('unavailable'); return; }

  // ---- which game this room plays ---------------------------------------------------------
  // info: { variant, players, options, turnSeconds } as the server describes a room (the invitation preview and every snapshot).
  var GAME_NAMES = { classic: 'room.game.classic', wallrush: 'room.game.wallrush', pointrush: 'room.game.pointrush', custom: 'room.game.custom' };
  function describeGame(info) {
    var v = GAME_NAMES[info.variant] ? info.variant : 'classic', n = info.players || 2, parts = [t(GAME_NAMES[v])];
    if (v === 'pointrush') parts.push(t('room.setPlayers', { n: n }));
    if (v === 'custom') {
      var o = info.options || {};
      parts.push(t('room.setBoard', { size: o.size }), t('room.setWalls', { n: o.walls }));
      if (o.borrow) parts.push(t('room.setBorrow'));
      parts.push(info.turnSeconds ? t('room.setClock', { n: info.turnSeconds }) : t('room.setClockOff'));
    }
    return parts.join(' · ');
  }
  function gameInfoOf(snap) {
    var g = snap.game || {};
    return { variant: g.variant, players: g.players, options: g.options, turnSeconds: snap.turnSeconds };
  }
  // The classic game needs no description; a variant says which one it is.
  function paintGameLine(el, info) {
    if (!el) return;
    var plain = !info.variant || info.variant === 'classic';
    el.hidden = plain;
    el.textContent = plain ? '' : t('room.gameLine', { game: describeGame(info) });
  }

  // ---- live room ------------------------------------------------------------------------
  var gameHost = document.querySelector('[data-game-host]');
  var banner = document.querySelector('[data-connection]');
  var session = null, ui = null, seatInfo = null, lastStatus = null, startingTimer = null, waitingSnap = null, joinInfo = null;

  // Only a private room is a game between friends, so only there a score is kept (see profile.js), and only between two players.
  // Seats saved by an older version of the page have no `via` and keep none.
  function keepsScore() {
    var seat = Online.loadSeat(roomId);
    return !!(seat && seat.via === 'private' && Profile && (!latest || latest.players.length === 2));
  }

  // Leaving a game in progress gives it to the opponent, who sees the win and counts it. Count the loss here too.
  function countForfeit() {
    if (lastStatus !== 'playing' || !latest || latest.players.length !== 2 || !keepsScore()) return;
    Profile.record(latest.players[0].name, latest.players[1].name, 1 - latest.you, roomId + '#' + latest.round);
  }

  function leaveFlow(confirmed) {
    var group = latest && latest.players.length > 2;
    if (confirmed !== true && !window.confirm(t(lastStatus === 'playing' ? (group ? 'room.confirmLeaveGroup' : 'room.confirmLeaveForfeit') : 'room.confirmLeave'))) return;
    countForfeit();
    var done = function () {
      Online.forgetSeat(roomId);
      if (ui) { ui.destroy(); ui = null; }
      show('left');
    };
    if (session) session.leave().then(done, done); else done();
  }
  Array.prototype.forEach.call(document.querySelectorAll('[data-leave]'), function (btn) { btn.addEventListener('click', function () { leaveFlow(); }); });

  function gone() {
    Online.forgetSeat(roomId);
    if (ui) { ui.destroy(); ui = null; }
    show('unavailable');
  }

  // ---- the waiting screen: the invitation, and for three or four players who has joined ----------------
  function setHidden(selector, hidden) {
    Array.prototype.forEach.call(document.querySelectorAll(selector), function (el) { el.hidden = hidden; });
  }
  function renderWaiting(snap) {
    waitingSnap = snap;
    var n = snap.players.length, group = n > 2, isHost = snap.you === snap.host;
    var joined = snap.players.filter(function (p) { return p.name !== null; }).length;
    setHidden('[data-group-only]', !group);
    setHidden('[data-pair-only]', group);
    setHidden('[data-host-only]', !isHost);
    setHidden('[data-guest-only]', isHost);
    if (linkEl) linkEl.textContent = Online.roomUrl(roomId);
    if (codeEl) codeEl.textContent = snap.code || '';
    var codeSection = document.getElementById('code-section');
    if (codeSection) codeSection.hidden = !snap.code; // only the host holds the pairing code
    paintGameLine(document.getElementById('waiting-game'), gameInfoOf(snap));
    var count = document.getElementById('lobby-count');
    if (count) count.textContent = t('room.lobbyCount', { n: joined, total: n });
    var list = document.getElementById('lobby');
    if (list) {
      list.textContent = '';
      snap.players.forEach(function (p, i) {
        var li = document.createElement('li');
        li.className = 'lobby-player lobby-player--' + i + (p.name === null ? ' is-empty' : '');
        var glyph = document.createElement('span');
        glyph.className = 'pawn-glyph';
        glyph.setAttribute('aria-hidden', 'true');
        var name = document.createElement('span');
        name.className = 'lobby-name';
        name.textContent = p.name === null ? t('room.lobbyEmpty') : p.name;
        var tags = [];
        if (i === snap.you) tags.push(t('game.youTag'));
        if (i === snap.host) tags.push(t('room.hostTag'));
        if (p.name !== null && !p.connected) tags.push(t('game.disconnectedTag'));
        var tag = document.createElement('span');
        tag.className = 'lobby-tag';
        tag.textContent = tags.join(' ');
        li.appendChild(glyph); li.appendChild(name); li.appendChild(tag);
        list.appendChild(li);
      });
    }
    show('waiting');
  }

  function onState(snap) {
    snap.receivedAt = Date.now();
    var wasStatus = lastStatus;
    lastStatus = snap.status;
    // Playing with a friend: the background search for a stranger (matchwatch.js) ends, so no offer
    // can interrupt this game.
    if (snap.status === 'playing' && window.QuoridorMatchwatch) window.QuoridorMatchwatch.stop();
    if (snap.status === 'waiting') {
      latest = null;
      return renderWaiting(snap);
    }
    waitingSnap = null;
    var names = snap.players.map(function (p) { return p.name; });
    // Brief "both players are in" screen when a fresh game begins.
    if (wasStatus === 'waiting' && snap.status === 'playing') {
      var text = document.getElementById('starting-text');
      if (text) {
        var first = (snap.you === 0 ? t('room.youFirst') : t('room.otherFirst', { name: names[0] }));
        text.textContent = (names.length === 2 ? t('room.connected', { name: names[snap.you], other: names[1 - snap.you] }) : t('room.allConnected', { names: names.join(', ') })) + ' ' + first;
      }
      show('starting');
      clearTimeout(startingTimer);
      startingTimer = setTimeout(function () { startingTimer = null; if (lastStatus) renderGame(snap); }, 2200);
      latest = snap;
      return;
    }
    if (startingTimer) { clearTimeout(startingTimer); startingTimer = null; }
    renderGame(snap);
  }

  var latest = null;
  // What the game screen needs besides the game itself.
  function metaOf(snap) {
    return {
      names: snap.players.map(function (p) { return p.name; }),
      connected: snap.players.map(function (p) { return p.connected; }),
      forfeitIn: snap.forfeitIn, rematch: snap.rematch, reason: snap.reason, round: snap.round,
      quitter: snap.quitter, finished: snap.status === 'finished',
      // The snapshot may have waited out the "both players are in" screen, so take that time off.
      turnLeft: snap.turnLeft == null ? null : Math.max(0, snap.turnLeft - (Date.now() - (snap.receivedAt || Date.now())) / 1000),
      clocks: snap.clocks, clocksAge: (Date.now() - (snap.receivedAt || Date.now())) / 1000
    };
  }
  function renderGame(snap) {
    latest = snap;
    if (startingTimer) { return; }
    var g = snap.game;
    if (!ui || ui.seat !== snap.you) {
      if (ui) ui.destroy();
      show('game');
      // Two players: the second seat sees the board turned round, so each player has their own pawn at the bottom. Wallrush has
      // both pawns on one line and Pointrush with more players has four edges, so those boards are shown the same way to everyone.
      var turned = g.players === 2 && snap.you === 1 && g.variant !== 'wallrush';
      ui = QuoridorGame.mount(gameHost, {
        mode: 'online', variant: g.variant, players: g.players, options: g.options, names: metaOf(snap).names, seat: snap.you, flip: turned,
        turnSeconds: snap.turnSeconds, remote: session,
        scoreId: keepsScore() ? roomId : undefined,
        onExit: function (how) { if (how === 'leave') leaveFlow(true); }  // the game screen already asked
      });
      ui.seat = snap.you;
    } else {
      show('game');
    }
    ui.setState(g, metaOf(snap));
  }

  function onConnection(ok) {
    if (banner) banner.hidden = ok;
    if (ui && !ok) ui.announce(t('room.connectionLost'));
    if (ui && ok) ui.announce(t('room.reconnected'));
    if (!ok && !ui) show('reconnecting');
  }

  function begin(token) {
    session = Online.session(roomId, token, { onState: onState, onConnection: onConnection, onGone: gone });
  }

  // Seat forfeit countdown shown in the game banner is re-rendered from the latest snapshot.
  setInterval(function () {
    if (!ui || !latest || latest.forfeitIn == null) return;
    latest.forfeitIn = Math.max(0, latest.forfeitIn - 1);
    ui.setState(latest.game, metaOf(latest));
  }, 1000);

  // A change of language: the lobby and the description of the game are built here, so write them again.
  if (I18n) I18n.onChange(function () {
    if (waitingSnap) renderWaiting(waitingSnap);
    if (joinInfo) paintJoin();
  });

  // ---- entry: returning seat, or a new visitor with the link ------------------------------
  function paintJoin() {
    var hostName = document.getElementById('host-name');
    if (hostName) hostName.textContent = joinInfo.host;
    paintGameLine(document.getElementById('join-game'), joinInfo);
  }

  var saved = Online.loadSeat(roomId);
  if (saved) {
    begin(saved.token);
  } else {
    Online.peek(roomId).then(function (info) {
      joinInfo = info;
      paintJoin();   // (a change of language rewrites the sentence around the host's name: the listener above puts it back)
      show('join');
    }, function (err) {
      show(err.code === 'full' ? 'full' : err.status === 0 ? 'unavailable' : 'unavailable');
    });

    var form = document.querySelector('[data-state="join"] form');
    var input = document.getElementById('username');
    var errEl = document.getElementById('username-error');
    var btn = form && form.querySelector('button[type="submit"]');
    if (Profile && !input.value) input.value = Profile.name();  // the name used last time
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var name = input.value.trim().normalize('NFC');
      if (!USERNAME_RE.test(name)) {
        errEl.textContent = t('err.bad-username');
        errEl.hidden = false; input.setAttribute('aria-invalid', 'true'); input.focus();
        return;
      }
      errEl.hidden = true; input.removeAttribute('aria-invalid');
      if (Profile) Profile.setName(name);
      btn.disabled = true;
      Online.joinById(roomId, name).then(function (res) {
        Online.saveSeat(roomId, { token: res.token, seat: res.seat, name: name, via: 'private' });
        btn.disabled = false;
        begin(res.token);
      }, function (err) {
        btn.disabled = false;
        if (err.code === 'full') return show('full');
        if (err.code === 'unavailable') return show('unavailable');
        errEl.textContent = I18n ? I18n.errorText(err) : err.message; errEl.hidden = false; input.focus();
      });
    });
  }
})();
