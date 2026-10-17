/* Private room page (/room/<id>/): lobby, waiting, joining, the synchronized game and the error states.

   The server is authoritative. This page keeps a long-poll session open, mirrors the server's
   state into the shared game screen, and sends moves as requests the server may refuse.
   Append ?preview=<state> to see the other designed screens with sample data (no server needed). */
(function () {
  var STATES = ['waiting', 'join', 'starting', 'reconnecting', 'invalid', 'full', 'expired', 'unavailable', 'left', 'game'];
  var PREVIEWABLE = STATES.filter(function (s) { return s !== 'game'; });
  var USERNAME_RE = /^[A-Za-z0-9 _.\-]{2,20}$/;
  var params = new URLSearchParams(window.location.search);
  var preview = params.get('preview');
  var isPreview = PREVIEWABLE.indexOf(preview) !== -1;
  var Online = window.QuoridorOnline;
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
    var heading = document.querySelector('[data-state="' + state + '"] h1');
    if (heading && changed && state !== 'game') heading.focus();
  }

  // ---- copy buttons -----------------------------------------------------------------------
  function copyText(text) {
    function done() { status.textContent = 'Copied to clipboard.'; }
    function fail() { status.textContent = 'Copy failed. Select the text and copy it manually.'; }
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
        if (window.confirm('Leave this room? If a game is in progress it counts as a forfeit.')) window.location.href = window.location.pathname + '?preview=left';
      });
    });
    return;
  }

  var roomId = decodeURIComponent((window.location.pathname.match(/\/room\/([^/]+)/) || [])[1] || '');
  if (!live || !roomId) { show('unavailable'); return; }

  // ---- live room ------------------------------------------------------------------------
  var gameHost = document.querySelector('[data-game-host]');
  var banner = document.querySelector('[data-connection]');
  var session = null, ui = null, seatInfo = null, lastStatus = null, startingTimer = null;

  function leaveFlow(confirmed) {
    if (confirmed !== true && !window.confirm(lastStatus === 'playing' ? 'Leave this room? You will forfeit the game.' : 'Leave this room?')) return;
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

  function onState(snap) {
    snap.receivedAt = Date.now();
    var wasStatus = lastStatus;
    lastStatus = snap.status;
    // Playing with a friend: the background search for a stranger (matchwatch.js) ends, so no offer
    // can interrupt this game.
    if (snap.status === 'playing' && window.QuoridorMatchwatch) window.QuoridorMatchwatch.stop();
    if (snap.status === 'waiting') {
      if (linkEl) linkEl.textContent = Online.roomUrl(roomId);
      if (codeEl) codeEl.textContent = snap.code || '';
      return show('waiting');
    }
    var names = [snap.players[0].name, snap.players[1].name];
    // Brief "both players are in" screen when a fresh game begins.
    if (wasStatus === 'waiting' && snap.status === 'playing') {
      var first = names[0];
      var text = document.getElementById('starting-text');
      if (text) text.textContent = names[snap.you] + ' and ' + names[1 - snap.you] + ' are connected. ' + (snap.you === 0 ? 'You move first.' : first + ' moves first.');
      show('starting');
      clearTimeout(startingTimer);
      startingTimer = setTimeout(function () { startingTimer = null; if (lastStatus) renderGame(snap); }, 2200);
      return;
    }
    if (startingTimer) { clearTimeout(startingTimer); startingTimer = null; }
    renderGame(snap);
  }

  var latest = null;
  function renderGame(snap) {
    latest = snap;
    if (startingTimer) { return; }
    var names = [snap.players[0].name, snap.players[1].name];
    var meta = {
      names: names,
      connected: [snap.players[0].connected, snap.players[1].connected],
      forfeitIn: snap.forfeitIn, rematch: snap.rematch, reason: snap.reason,
      // The snapshot may have waited out the "both players are in" screen, so take that time off.
      turnLeft: snap.turnLeft == null ? null : Math.max(0, snap.turnLeft - (Date.now() - (snap.receivedAt || Date.now())) / 1000)
    };
    if (!ui || ui.seat !== snap.you) {
      if (ui) ui.destroy();
      show('game');
      ui = QuoridorGame.mount(gameHost, {
        mode: 'online', names: names, seat: snap.you, flip: snap.you === 1, remote: session,
        onExit: function (how) { if (how === 'leave') leaveFlow(true); }  // the game screen already asked
      });
      ui.seat = snap.you;
    } else {
      show('game');
    }
    ui.setState(snap.game, meta);
  }

  function onConnection(ok) {
    if (banner) banner.hidden = ok;
    if (ui && !ok) ui.announce('Connection lost. Trying to reconnect.');
    if (ui && ok) ui.announce('Reconnected.');
    if (!ok && !ui) show('reconnecting');
  }

  function begin(token) {
    session = Online.session(roomId, token, { onState: onState, onConnection: onConnection, onGone: gone });
  }

  // Seat forfeit countdown shown in the game banner is re-rendered from the latest snapshot.
  setInterval(function () {
    if (!ui || !latest || latest.forfeitIn == null) return;
    latest.forfeitIn = Math.max(0, latest.forfeitIn - 1);
    ui.setState(latest.game, {
      names: [latest.players[0].name, latest.players[1].name],
      connected: [latest.players[0].connected, latest.players[1].connected],
      forfeitIn: latest.forfeitIn, rematch: latest.rematch, reason: latest.reason,
      turnLeft: latest.turnLeft
    });
  }, 1000);

  // ---- entry: returning seat, or a new visitor with the link ------------------------------
  var saved = Online.loadSeat(roomId);
  if (saved) {
    begin(saved.token);
  } else {
    Online.peek(roomId).then(function (info) {
      var hostName = document.getElementById('host-name');
      if (hostName) hostName.textContent = info.host;
      show('join');
    }, function (err) {
      show(err.code === 'full' ? 'full' : err.status === 0 ? 'unavailable' : 'unavailable');
    });

    var form = document.querySelector('[data-state="join"] form');
    var input = document.getElementById('username');
    var errEl = document.getElementById('username-error');
    var btn = form && form.querySelector('button[type="submit"]');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var name = input.value.trim();
      if (!USERNAME_RE.test(name)) {
        errEl.textContent = 'Use 2 to 20 characters: letters, numbers, spaces, dots, dashes or underscores.';
        errEl.hidden = false; input.setAttribute('aria-invalid', 'true'); input.focus();
        return;
      }
      errEl.hidden = true; input.removeAttribute('aria-invalid');
      btn.disabled = true;
      Online.joinById(roomId, name).then(function (res) {
        Online.saveSeat(roomId, { token: res.token, seat: res.seat, name: name });
        btn.disabled = false;
        begin(res.token);
      }, function (err) {
        btn.disabled = false;
        if (err.code === 'full') return show('full');
        if (err.code === 'unavailable') return show('unavailable');
        errEl.textContent = err.message; errEl.hidden = false; input.focus();
      });
    });
  }
})();
