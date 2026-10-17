/* Play-mode pages: validates the setup form, then starts the game for that mode.
     local        two players on one device         (engine.js, board.js, game.js)
     computer     one player against the computer  (+ ai.js, ai-worker.js)
     online       matchmaking, then the room page   (online.js, server)
     create-room / join-room   private rooms        (online.js, server)
   A form marked data-live="false" (no game server on this site) validates and then says so. */
(function () {
  var USERNAME_RE = /^[A-Za-z0-9 _.\-]{2,20}$/;
  var CODE_RE = /^[A-HJ-NP-Z2-9]{6}$/; // unambiguous alphabet: no 0/O/1/I

  function $(sel, root) { return (root || document).querySelector(sel); }

  function showError(input, errorEl, message) {
    errorEl.textContent = message;
    errorEl.hidden = false;
    input.setAttribute('aria-invalid', 'true');
    input.focus();
  }
  function clearError(input, errorEl) {
    errorEl.hidden = true;
    errorEl.textContent = '';
    input.removeAttribute('aria-invalid');
  }
  function checkUsername(input, errorEl) {
    var value = input.value.trim();
    if (!USERNAME_RE.test(value)) {
      showError(input, errorEl, 'Use 2 to 20 characters: letters, numbers, spaces, dots, dashes or underscores.');
      return null;
    }
    clearError(input, errorEl);
    return value;
  }

  var form = $('[data-play-form]');
  if (!form) return;

  var kind = form.getAttribute('data-play-form');
  var live = form.getAttribute('data-live') === 'true';
  var notice = $('[data-unavailable]');
  var stage = $('[data-stage]');
  var gameWrap = $('[data-game-wrap]');
  var gameHost = $('[data-game-host]');
  var nameInput = $('#username', form);
  var nameError = $('#username-error', form);
  var codeInput = $('#code', form);
  var codeError = $('#code-error', form);
  var serverError = $('[data-error]', form);
  var submitBtn = $('button[type="submit"]', form);

  if (nameInput) nameInput.addEventListener('input', function () { clearError(nameInput, nameError); });
  if (codeInput) {
    codeInput.addEventListener('input', function () {
      codeInput.value = codeInput.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
      clearError(codeInput, codeError);
    });
  }

  function showNotice() {
    if (!notice) return;
    notice.hidden = false;
    notice.setAttribute('tabindex', '-1');
    notice.focus();
  }

  // ---- showing / hiding the game --------------------------------------------------------
  var controller = null;
  function openGame(cfg) {
    cfg.onExit = function (how) {
      controller.destroy();
      controller = null;
      gameWrap.hidden = true;
      stage.hidden = false;
      if (how === 'leave') { window.location.href = QuoridorOnline.root + 'play/'; return; }
      if (submitBtn) submitBtn.focus();
    };
    stage.hidden = true;
    gameWrap.hidden = false;
    controller = QuoridorGame.mount(gameHost, cfg);
    gameWrap.scrollIntoView({ block: 'start' });
  }

  // ---- local and computer ---------------------------------------------------------------
  function startLocal() {
    var n1 = $('#name1', form), n2 = $('#name2', form);
    var names = [(n1 && n1.value.trim()) || 'Player 1', (n2 && n2.value.trim()) || 'Player 2'];
    for (var i = 0; i < 2; i++) {
      var field = i === 0 ? n1 : n2, err = $('#name' + (i + 1) + '-error', form);
      if (field && field.value.trim() && !USERNAME_RE.test(field.value.trim())) {
        showError(field, err, 'Use 2 to 20 characters: letters, numbers, spaces, dots, dashes or underscores, or leave it empty.');
        return;
      }
      if (err) { err.hidden = true; }
    }
    if (names[0].toLowerCase() === names[1].toLowerCase()) names[1] += ' (2)';
    openGame({ mode: 'local', names: names });
  }

  var LEVEL_NAMES = { easy: 'Easy robot', medium: 'Medium robot', hard: 'Hard robot', expert: 'Expert robot' };
  function startComputer() {
    var chosen = $('input[name="difficulty"]:checked', form);
    var level = chosen ? chosen.value : 'medium';
    openGame({ mode: 'computer', names: ['You', LEVEL_NAMES[level]], seat: 0, level: level });
  }

  // ---- online: matchmaking and private rooms -------------------------------------------
  function failureText(err) {
    if (!err || err.status === 0) return 'The game server could not be reached. Check your connection and try again.';
    return err.message || 'Something went wrong. Please try again.';
  }
  function showServerError(err) {
    if (!serverError) return;
    serverError.hidden = false;
    var msg = $('[data-error-text]', serverError);
    if (msg) msg.textContent = failureText(err);
    serverError.setAttribute('tabindex', '-1');
    serverError.focus();
  }
  function hideServerError() { if (serverError) serverError.hidden = true; }

  function enter(res, name) {
    QuoridorOnline.saveSeat(res.roomId, { token: res.token, seat: res.seat, name: name });
    window.location.href = QuoridorOnline.roomUrl(res.roomId);
  }

  // What the search panel says as time passes. The wording follows the real state: these are
  // display thresholds, not matchmaking rules. `alt` shows the other ways to play (computer first).
  var SEARCH_STAGES = [
    { from: 0,  alt: false, text: 'Finding your opponent…' },
    { from: 15, alt: false, text: 'Searching for an available player…' },
    { from: 30, alt: true,  text: 'Your search is active. Try another game while you wait.' },
    { from: 60, alt: true,  text: 'No match yet. You can keep searching or choose another way to play.' }
  ];
  var CONNECTION_TEXT = 'Connection problem. Trying to reconnect…';
  function stageFor(seconds) {
    var stage = SEARCH_STAGES[0];
    SEARCH_STAGES.forEach(function (s) { if (seconds >= s.from) stage = s; });
    return stage;
  }

  var PENDING_TEXT = 'Opponent found. Waiting for them to confirm…';
  var searching = null, timer = null;
  // resume: { ticket, since } picks up a search that kept running while the player was on another page.
  function startSearch(name, resume) {
    var panel = $('[data-searching]', form), elapsed = $('[data-search-elapsed]', form),
        slow = $('[data-slow]', form), text = $('[data-search-text]', form);
    var started = resume && resume.since ? resume.since : Date.now(), connected = true, pending = false, shown = '';
    form.classList.add('is-searching');
    panel.hidden = false; slow.hidden = true;
    submitBtn.hidden = true;
    if (nameInput) { nameInput.value = name; nameInput.disabled = true; }

    // Only touch the live region when the wording changes, so screen readers hear each message once.
    function say(message) { if (message !== shown) { shown = message; text.textContent = message; } }
    function tick() {
      var s = Math.max(0, Math.floor((Date.now() - started) / 1000)), stage = stageFor(s);
      elapsed.textContent = ('0' + Math.floor(s / 60)).slice(-2) + ':' + ('0' + (s % 60)).slice(-2);
      say(!connected ? CONNECTION_TEXT : pending ? PENDING_TEXT : stage.text);
      slow.hidden = !(stage.alt && connected && !pending);
    }
    tick(); timer = setInterval(tick, 1000);
    function stopUi() {
      clearInterval(timer); timer = null; searching = null;
      QuoridorOnline.clearSearch();
      panel.hidden = true; submitBtn.hidden = false; form.classList.remove('is-searching');
      if (nameInput) nameInput.disabled = false;
    }
    searching = QuoridorOnline.search(name, {
      onTicket: function (id) { QuoridorOnline.saveSearch({ ticket: id, name: name, since: started }); },
      onUpdate: function (r) { pending = !!r.pending; tick(); },
      onMatched: function (res) {
        clearInterval(timer); searching = null;
        QuoridorOnline.clearSearch();
        say('Opponent found. Starting the game…');
        document.title = 'Opponent found | ' + document.title;
        slow.hidden = true;
        enter(res, name);
      },
      onConnection: function (ok) { connected = ok; tick(); },
      onSuperseded: function () { var keep = QuoridorOnline.loadSearch(); stopUi(); if (keep) QuoridorOnline.saveSearch(keep); }, // another tab runs this search now
      onError: function (err) {
        stopUi();
        if (!(resume && err && err.status === 404)) showServerError(err); // a resumed search that already ended is not an error
      }
    }, resume ? { ticket: resume.ticket } : {});
    var cancel = $('[data-cancel-search]', form);
    cancel.onclick = function () {
      searching.cancel(); stopUi();
      if (nameInput) nameInput.focus();
    };
    if (!resume) cancel.focus();
  }

  function startOnline(name) {
    hideServerError();
    if (kind === 'online') return startSearch(name);
    submitBtn.disabled = true;
    var request = kind === 'create-room'
      ? QuoridorOnline.createRoom(name)
      : QuoridorOnline.joinByCode(codeInput.value, name);
    request.then(function (res) { enter(res, name); }, function (err) {
      submitBtn.disabled = false;
      if (kind === 'join-room' && (err.code === 'invalid' || err.code === 'full')) {
        showError(codeInput, codeError, err.message);
      } else {
        showServerError(err);
      }
    });
  }

  // Leaving the page while searching does not end the search: the ticket stays in this tab's session
  // storage and matchwatch.js on the next play page picks it up, asking before it starts any match.
  // (The server drops a search nobody has polled for 20 seconds.)
  window.addEventListener('pagehide', function () { if (searching) searching.detach(); });
  window.addEventListener('pageshow', function (e) { if (e.persisted && QuoridorOnline.loadSearch()) window.location.reload(); });

  var retry = $('[data-retry]', form);
  if (retry) retry.addEventListener('click', function () { hideServerError(); if (submitBtn) submitBtn.focus(); });

  // ---- submit ---------------------------------------------------------------------------
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (kind === 'local') return startLocal();
    if (kind === 'computer') return startComputer();

    var name = nameInput && checkUsername(nameInput, nameError);
    if (nameInput && !name) return;
    if (kind === 'join-room' && codeInput && !CODE_RE.test(codeInput.value)) {
      showError(codeInput, codeError, 'Pairing codes are 6 characters (letters A to Z and digits 2 to 9). Check the code and try again.');
      return;
    }
    if (!live) return showNotice();
    startOnline(name);
  });

  // Coming back to the search page (or reloading it) while a search is still running.
  if (kind === 'online' && live) {
    var saved = QuoridorOnline.loadSearch();
    if (saved) startSearch(saved.name, saved);
  }
})();
