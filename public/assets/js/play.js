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

  var searching = null, timer = null;
  function startSearch(name) {
    var panel = $('[data-searching]', form), elapsed = $('[data-search-elapsed]', form),
        slow = $('[data-slow]', form), text = $('[data-search-text]', form);
    var started = Date.now();
    form.classList.add('is-searching');
    panel.hidden = false; slow.hidden = true; text.textContent = 'Looking for an opponent…';
    submitBtn.hidden = true;
    if (nameInput) nameInput.disabled = true;
    function tick() {
      var s = Math.floor((Date.now() - started) / 1000);
      elapsed.textContent = Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2);
      if (s >= 20) slow.hidden = false;
    }
    tick(); timer = setInterval(tick, 1000);
    function stopUi() {
      clearInterval(timer); timer = null; searching = null;
      panel.hidden = true; submitBtn.hidden = false; form.classList.remove('is-searching');
      if (nameInput) nameInput.disabled = false;
    }
    searching = QuoridorOnline.search(name, {
      onMatched: function (res) {
        clearInterval(timer);
        text.textContent = 'Opponent found. Starting the game…';
        slow.hidden = true;
        enter(res, name);
      },
      onError: function (err) { stopUi(); showServerError(err); }
    });
    var cancel = $('[data-cancel-search]', form);
    cancel.onclick = function () {
      searching.cancel(); stopUi();
      if (nameInput) nameInput.focus();
    };
    cancel.focus();
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

  // Leaving the page while searching drops the search (the server also expires idle searches).
  window.addEventListener('pagehide', function () { if (searching) searching.cancel(); });

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
})();
