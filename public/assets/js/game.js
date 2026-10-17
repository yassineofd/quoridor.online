/* Game screen shared by every playing mode: board, turn bar, player cards, controls, move log.

   QuoridorGame.mount(host, cfg) returns a controller.
     cfg.mode     'local' (hot-seat) | 'computer' | 'online'
     cfg.names    [name for player 0, name for player 1]
     cfg.nameKeys optional [message key | null, ...]: names made up by the site, which are written again when the language changes
     cfg.seat     which player "you" are (computer / online); null for hot-seat
     cfg.flip     draw the board rotated so that `seat` is at the bottom
     cfg.level    computer difficulty
     cfg.remote   online only: { send(move) -> Promise, resign(), leave(), rematch() }
     cfg.leaveHref where "Leave" goes (local and computer games): drawn as a link to this address
     cfg.onExit   called with 'again' or 'leave' when the player finishes
   For online games the owner pushes server state in with controller.setState(json, meta).      */
(function (root) {
  'use strict';
  var Q = root.Quoridor, B = root.QuoridorBoard;
  function t(key, params) { return root.QuoridorI18n ? root.QuoridorI18n.t(key, params) : key; }

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
  // icon is a Lucide icon name from icons.js; it sits before the label and is hidden from screen readers.
  // labelKey is a message key (translations/js-en.json); the button remembers it so the label can follow a change of language.
  function button(labelKey, cls, onClick, icon) {
    var b = h('button', { type: 'button', 'class': 'btn ' + (cls || 'btn--secondary') });
    if (icon && root.QuoridorIcons) b.innerHTML = root.QuoridorIcons.svg(icon);
    b.appendChild(document.createTextNode(t(labelKey)));
    b.__labelKey = labelKey;
    b.addEventListener('click', onClick);
    return b;
  }
  // Same look as button(), but a real link: it can be opened in a new tab, and the address shows on hover.
  // A plain click is handled in place (onClick may ask for confirmation); a modified click is left to the browser.
  function link(labelKey, cls, href, onClick, icon) {
    var a = h('a', { href: href, 'class': 'btn ' + (cls || 'btn--secondary') });
    if (icon && root.QuoridorIcons) a.innerHTML = root.QuoridorIcons.svg(icon);
    a.appendChild(document.createTextNode(t(labelKey)));
    a.__labelKey = labelKey;
    a.addEventListener('click', function (e) {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      onClick(e);
    });
    return a;
  }
  function setLabel(b, labelKey) {
    b.__labelKey = labelKey;
    b.lastChild.nodeValue = t(labelKey);
  }

  var TURN_SECONDS = 15;   // time to make a move; the online server enforces the same limit

  // The move played for a player whose time ran out: the pawn step that leaves the shortest route.
  function fallbackMove(game) {
    var p = game.turn, from = game.pawns[p], best = null, bestD = Infinity;
    game.pawnMoves(p).forEach(function (to) {
      game.pawns[p] = to;
      var d = game.distance(p);
      if (d >= 0 && d < bestD) { bestD = d; best = to; }
    });
    game.pawns[p] = from;
    return best ? { type: 'move', r: best[0], c: best[1] } : null;
  }

  // ---- computer opponent runner (Web Worker with a main-thread fallback) --------------
  function createThinker(level) {
    var worker = null, pending = null, nextId = 1;
    try {
      var src = document.querySelector('script[src*="game.js"]').src.replace(/game\.js.*$/, 'ai-worker.js');
      worker = new Worker(src);
      worker.onmessage = function (e) { if (pending && e.data.id === pending.id) { var p = pending; pending = null; p.resolve(e.data.move); } };
      worker.onerror = function () { worker = null; if (pending) { var p = pending; pending = null; p.fallback(); } };
    } catch (err) { worker = null; }

    return {
      choose: function (game) {
        return new Promise(function (resolve) {
          var started = Date.now();
          function done(move) { setTimeout(function () { resolve(move); }, Math.max(0, 450 - (Date.now() - started))); }
          function local() { setTimeout(function () { done(root.QuoridorAI.chooseMove(game.clone(), { level: level })); }, 30); }
          if (!worker) return local();
          var id = nextId++;
          pending = { id: id, resolve: done, fallback: local };
          worker.postMessage({ id: id, moves: game.moves, level: level });
        });
      },
      cancel: function () { pending = null; },
      destroy: function () { pending = null; if (worker) worker.terminate(); worker = null; }
    };
  }

  function mount(host, cfg) {
    var mode = cfg.mode;
    var names = (cfg.names || [t('game.player1'), t('game.player2')]).slice();
    var seat = cfg.seat === undefined ? null : cfg.seat;
    var game = new Q.Game();
    var meta = { connected: [true, true], forfeitIn: null, rematch: [false, false], reason: null };
    var thinker = mode === 'computer' ? createThinker(cfg.level || 'medium') : null;
    var thinking = false, busy = false, destroyed = false, lastTurn = -1, lastCount = 0;
    var botName = names[1 - (seat === null ? 0 : seat)];

    host.textContent = '';
    host.classList.add('game');

    // ---- layout -----------------------------------------------------------------------
    var boardHost = h('div', { 'class': 'game-board' });
    var turn = h('div', { 'class': 'turn-bar', role: 'status', tabindex: '-1' });
    var banner = h('div', { 'class': 'notice game-banner', role: 'status', hidden: '' });
    var cards = [0, 1].map(function (i) {
      var glyph = h('span', { 'class': 'pawn-glyph pawn-glyph--' + i, 'aria-hidden': 'true' });
      var name = h('span', { 'class': 'player-name' });
      var tag = h('span', { 'class': 'player-tag' });
      var walls = h('span', { 'class': 'player-walls' });
      var card = h('li', { 'class': 'player-card' }, [glyph, h('span', { 'class': 'player-text' }, [name, tag]), walls]);
      return { card: card, name: name, tag: tag, walls: walls };
    });
    var timerText = h('span', { 'class': 'turn-timer-text', 'aria-hidden': 'true' });
    var timerFill = h('span', { 'class': 'turn-timer-fill' });
    var timer = h('div', { 'class': 'turn-timer', hidden: '' }, [timerText, h('span', { 'class': 'turn-timer-bar', 'aria-hidden': 'true' }, [timerFill])]);
    var players = h('ul', { 'class': 'players', 'aria-label': t('game.players') }, cards.map(function (c) { return c.card; }));

    // Buttons are made from message keys, so a change of language can set their labels again (see relabel below).
    var modeBtns = {
      move: button('game.movePawn', 'btn--secondary btn--toggle', function () { board.setMode('move'); }, 'move'),
      wall: button('game.placeWall', 'btn--secondary btn--toggle', function () { board.setMode('wall'); }, 'wall')
    };
    var rotateBtn = button('game.rotateWall', 'btn--secondary', function () { board.rotate(); }, 'rotate');
    var confirmBtn = button('game.confirmWall', 'btn--primary', function () { board.confirm(); }, 'check');
    var cancelBtn = button('game.cancel', 'btn--secondary', function () { board.cancel(); }, 'x');
    var actionRow = h('div', { 'class': 'btn-row', role: 'group', 'aria-label': t('game.chooseAction') }, [modeBtns.move, modeBtns.wall]);
    var wallRow = h('div', { 'class': 'btn-row wall-row', hidden: '' }, [rotateBtn, confirmBtn, cancelBtn]);
    var hint = h('p', { 'class': 'game-hint small text-muted' });
    var keys = h('p', { 'class': 'small text-muted game-keys', text: t('game.keys') });

    var undoBtn = mode !== 'online' ? button('game.undo', 'btn--secondary', onUndo, 'undo') : null;
    var resignBtn = mode !== 'local' ? button('game.resign', 'btn--secondary', onResign, 'flag') : null;
    var restartBtn = mode !== 'online' ? button('game.restart', 'btn--secondary', onRestart, 'restart') : null;
    // Leaving a game that never touches the server is just a trip to cfg.leaveHref (when the page gave one).
    function leaveControl(labelKey, cls, onClick) {
      if (cfg.leaveHref && mode !== 'online') return link(labelKey, cls, cfg.leaveHref, onClick, 'logout');
      return button(labelKey, cls, onClick, 'logout');
    }
    var leaveBtn = leaveControl(mode === 'online' ? 'game.leaveGame' : 'game.leave', 'btn--secondary', onLeave);
    var controls = h('div', { 'class': 'btn-row game-controls' }, [undoBtn, resignBtn, restartBtn, leaveBtn]);

    var resultTitle = h('h2', { 'class': 'h-sm', tabindex: '-1' });
    var resultText = h('p', { 'class': 'text-muted' });
    var resultActions = h('div', { 'class': 'btn-row' });
    var result = h('div', { 'class': 'card result', hidden: '' }, [resultTitle, resultText, resultActions]);

    var logList = h('ol', { 'class': 'move-log' });
    var log = h('details', { 'class': 'move-log-wrap', open: '' }, [h('summary', { text: t('game.moveList') }), logList]);
    // On phones the move list starts collapsed so the board and controls fit on screen.
    if (window.matchMedia && window.matchMedia('(max-width: 899px)').matches) log.removeAttribute('open');
    var announcer = h('div', { 'class': 'sr-only', 'aria-live': 'polite', 'aria-atomic': 'true' });

    var side = h('div', { 'class': 'game-side' }, [turn, timer, banner, players, result, actionRow, wallRow, hint, controls, keys, log, announcer]);
    host.appendChild(h('div', { 'class': 'game-layout' }, [boardHost, side]));

    // ---- turn timer ---------------------------------------------------------------------
    // Hot-seat and computer games count down here and play the fallback move at zero. Online the
    // server is in charge (it sends turnLeft and plays the move itself); this only shows the clock.
    var deadline = null, timerKey = null, warned = false;

    function timerRunning() {
      if (game.winner !== null || destroyed) return false;
      if (mode === 'online') return deadline !== null;
      return mode === 'local' || (game.turn === seat && !thinking);
    }
    function resetTimer(seconds) {
      deadline = Date.now() + (seconds === undefined ? TURN_SECONDS : seconds) * 1000;
      warned = false;
    }
    function tick() {
      if (deadline === null && mode !== 'online' && timerRunning()) resetTimer();
      var running = timerRunning();
      timer.hidden = !running;
      if (!running) return;
      var left = Math.max(0, deadline - Date.now());
      var secs = Math.ceil(left / 1000);
      timerText.textContent = t('game.timerLeft', { who: sayWho(game.turn), n: secs });
      timerFill.style.width = Math.min(100, left / (TURN_SECONDS * 10)) + '%';
      timer.classList.toggle('is-low', secs <= 5);
      if (secs <= 5 && !warned && left > 0 && (mode === 'local' || game.turn === seat)) { warned = true; announce(t('game.secondsLeft', { n: secs })); }
      if (left <= 0 && mode !== 'online') timeUp();
    }
    function timeUp() {
      var m = fallbackMove(game);
      deadline = null;
      if (!m) return;
      var who = game.turn;
      commit(m);
      hint.textContent = (t('game.timeUp') + ' ' + describeMove(who, m) + ' ' + hint.textContent).trim();
      announce(hint.textContent);
    }
    var tickTimer = setInterval(tick, 250);

    function announce(text) { announcer.textContent = ''; setTimeout(function () { announcer.textContent = text; }, 20); }

    var board = B.create(boardHost, {
      game: game,
      names: names,
      flip: !!cfg.flip,
      onCommit: commit,
      onAnnounce: function (text) { hint.textContent = text; announce(text); },
      onChange: syncControls,
      onMode: function () { hint.textContent = ''; }
    });

    // ---- who may act ------------------------------------------------------------------
    function actor() {
      if (game.winner !== null || destroyed) return null;
      if (mode === 'local') return game.turn;
      if (thinking || busy) return null;
      return game.turn === seat ? seat : null;
    }

    function sayWho(i) { return i === seat && seat !== null ? t('game.you') : names[i]; }

    function render() {
      board.setGame(game);
      board.setActor(actor());
      board.setLast(game.moves.length ? game.moves[game.moves.length - 1] : null);
      board.refresh();

      var over = game.winner !== null;
      cards.forEach(function (c, i) {
        c.name.textContent = names[i];
        c.tag.textContent = (i === seat ? ' ' + t('game.youTag') : '') + (meta.connected[i] === false && mode === 'online' ? ' ' + t('game.disconnectedTag') : '');
        c.walls.textContent = t('game.wallsCount', { n: game.wallsLeft[i] });
        c.card.classList.toggle('is-active', !over && game.turn === i);
        c.card.classList.toggle('is-winner', over && game.winner === i);
        if (!over && game.turn === i) c.card.setAttribute('aria-current', 'true'); else c.card.removeAttribute('aria-current');
      });

      // Turn bar
      var text;
      if (over) text = (game.winner === seat ? t('game.youWin') : t(seat === null ? 'game.nameWinsBang' : 'game.nameWins', { name: names[game.winner] }));
      else if (mode === 'local') text = t('game.turnOf', { name: names[game.turn] });
      else if (game.turn === seat) text = t('game.yourTurn');
      else text = mode === 'computer' ? t('game.thinking', { name: botName }) : t('game.turnOf', { name: names[game.turn] });
      if (turn.textContent !== text) {
        turn.textContent = text;
        if (!over && game.turn !== lastTurn) { turn.classList.remove('flash'); void turn.offsetWidth; turn.classList.add('flash'); }
      }
      lastTurn = game.turn;

      // Move log
      while (logList.children.length > game.moves.length) logList.removeChild(logList.lastChild);
      for (var i = logList.children.length; i < game.moves.length; i++) {
        var m = game.moves[i], who = i % 2; // player 0 always moves first
        logList.appendChild(h('li', { text: t(m.type === 'move' ? 'game.logMoved' : 'game.logWall', { name: names[who], move: Q.moveName(m) }) }));
      }
      logList.scrollTop = logList.scrollHeight;

      // Result panel
      result.hidden = !over;
      if (over) showResult();

      if (mode === 'local' && !over && game.moves.length > lastCount) {
        hint.textContent = t('game.passDevice', { name: names[game.turn] });
      } else if (!over && game.turn === actor()) {
        hint.textContent = '';
      }
      lastCount = game.moves.length;
      if (mode !== 'online') {
        var key = game.moves.length + ':' + game.winner;
        if (key !== timerKey || (deadline === null && timerRunning())) { timerKey = key; resetTimer(); }
      }
      tick();
      syncControls(board.selection());
    }

    function syncControls(sel) {
      var act = actor() !== null, m = board.getMode();
      modeBtns.move.setAttribute('aria-pressed', String(m === 'move'));
      modeBtns.wall.setAttribute('aria-pressed', String(m === 'wall'));
      var wallsLeft = act ? game.wallsLeft[actor()] : 0;
      modeBtns.move.disabled = !act;
      modeBtns.wall.disabled = !act || wallsLeft <= 0;
      if (act && wallsLeft <= 0 && m === 'wall') { board.setMode('move'); return; }
      wallRow.hidden = !(act && m === 'wall');
      rotateBtn.disabled = !act;
      confirmBtn.disabled = !(sel && sel.legal);
      cancelBtn.disabled = !sel;
      if (act && m === 'wall' && sel && !sel.legal) hint.textContent = sel.reason;
      var over = game.winner !== null;
      actionRow.hidden = over;
      if (undoBtn) undoBtn.disabled = over || thinking || game.moves.length < (mode === 'computer' ? 2 : 1) || (mode === 'computer' && game.turn !== seat);
      if (resignBtn) resignBtn.disabled = over || (mode === 'computer' && thinking);
      if (mode === 'online' && banner) renderBanner();
    }

    function renderBanner() {
      var opp = seat === null ? null : 1 - seat;
      if (game.winner === null && opp !== null && meta.connected[opp] === false) {
        banner.hidden = false;
        banner.textContent = t('game.lostConnection', { name: names[opp] }) + ' ' + (meta.forfeitIn != null ? t('game.forfeitIn', { n: Math.max(0, Math.ceil(meta.forfeitIn)) }) : t('game.waitingReturn'));
      } else if (meta.notice) {
        banner.hidden = false; banner.textContent = meta.notice;
      } else {
        banner.hidden = true; banner.textContent = '';
      }
    }

    function showResult() {
      var youWon = seat !== null && game.winner === seat;
      resultTitle.textContent = seat === null ? t('game.nameWins', { name: names[game.winner] }) : (youWon ? t('game.youWon') : t('game.nameWon', { name: names[game.winner] }));
      var why = meta.reason === 'resign' ? t(youWon ? 'game.resignedOpp' : 'game.resignedSelf')
        : meta.reason === 'disconnect' ? t(youWon ? 'game.leftOpp' : 'game.disconnectedSelf')
        : '';
      var lastMove = game.moves[game.moves.length - 1];
      var byMove = !why && lastMove && lastMove.type === 'move' ? t('game.reachedEdge', { n: Math.ceil(game.moves.length / 2) }) : '';
      resultText.textContent = (why || byMove).trim();
      resultActions.textContent = '';
      if (mode === 'online') {
        var wanted = seat !== null && meta.rematch[seat];
        var oppWants = seat !== null && meta.rematch[1 - seat];
        var rb = button(wanted ? 'game.rematchRequested' : (oppWants ? 'game.rematchAccept' : 'game.rematchRequest'), 'btn--primary', function () { cfg.remote.rematch(); }, 'restart');
        rb.disabled = wanted;
        resultActions.appendChild(rb);
        if (oppWants && !wanted) resultText.textContent += ' ' + t('game.rematchWanted');
      } else {
        resultActions.appendChild(button('game.playAgain', 'btn--primary', function () { exit('again'); }, 'restart'));
      }
      resultActions.appendChild(leaveControl('game.leave', 'btn--secondary', function () { exit('leave'); }));
      if (!result.dataset.announced || result.dataset.announced !== String(game.winner) + game.moves.length) {
        result.dataset.announced = String(game.winner) + game.moves.length;
        announce(resultTitle.textContent + '. ' + resultText.textContent);
        resultTitle.focus();
      }
    }

    // ---- applying moves ---------------------------------------------------------------
    function describeMove(player, m) {
      return t(m.type === 'move' ? 'game.moved' : 'game.placedWall', { who: sayWho(player), move: Q.moveName(m) });
    }

    function commit(move) {
      var who = game.turn;
      if (mode === 'online') {
        busy = true; render();
        cfg.remote.send(move).then(function () { busy = false; }, function (err) {
          busy = false; render();
          hint.textContent = err && (err.code || err.message) && root.QuoridorI18n ? root.QuoridorI18n.errorText(err) : t('game.moveRefused');
          announce(hint.textContent);
        });
        return;
      }
      var err = game.apply(move);
      if (err) { hint.textContent = t('game.moveNotAllowed'); announce(hint.textContent); return; }
      board.setMode('move');
      announce(describeMove(who, move));
      if (mode === 'computer' && game.winner === null) {
        thinking = true; render();
        thinker.choose(game).then(function (m) {
          if (destroyed || !thinking) return;
          thinking = false;
          var p = game.turn;
          if (m && !game.apply(m)) announce(describeMove(p, m));
          render();
        });
        return;
      }
      render();
    }

    function onUndo() {
      if (mode === 'computer') { game.undo(); game.undo(); } else game.undo();
      board.setMode('move');
      hint.textContent = t('game.movedBack');
      announce(t('game.movedBack'));
      render();
    }
    function onRestart() {
      if (game.moves.length && game.winner === null && !window.confirm(t('game.confirmRestart'))) return;
      exit('again');
    }
    function onResign() {
      if (!window.confirm(t('game.confirmResign'))) return;
      if (mode === 'online') { cfg.remote.resign(); return; }
      if (thinker) { thinking = false; thinker.cancel(); }
      game.resign(seat);
      meta.reason = 'resign';
      render();
    }
    function onLeave() {
      var live = game.winner === null && game.moves.length > 0;
      var text = t(mode === 'online' && live ? 'game.confirmLeaveOnline' : 'game.confirmLeave');
      if ((live || mode === 'online') && !window.confirm(text)) return;
      exit('leave');
    }
    function exit(kind) {
      if (cfg.onExit) cfg.onExit(kind);
    }

    // ---- first move for the computer, if it plays first --------------------------------
    function start() {
      render();
      if (mode === 'computer' && game.turn !== seat) {
        thinking = true; render();
        thinker.choose(game).then(function (m) {
          if (destroyed) return;
          thinking = false;
          if (m) game.apply(m);
          render();
        });
      }
      turn.focus();
    }

    // A change of language: set the static labels again and redraw everything the screen built from messages.
    function relabel() {
      if (destroyed) return;
      // Names the site made up ("You", "Medium robot", "Player 2") follow the language; names people typed do not.
      if (cfg.nameKeys) cfg.nameKeys.forEach(function (k, i) { if (k) names[i] = t(k); });
      botName = names[1 - (seat === null ? 0 : seat)];
      [modeBtns.move, modeBtns.wall, rotateBtn, confirmBtn, cancelBtn, undoBtn, resignBtn, restartBtn, leaveBtn].forEach(function (b) {
        if (b) setLabel(b, b.__labelKey);
      });
      players.setAttribute('aria-label', t('game.players'));
      actionRow.setAttribute('aria-label', t('game.chooseAction'));
      keys.textContent = t('game.keys');
      log.firstChild.textContent = t('game.moveList');
      logList.textContent = '';
      hint.textContent = '';
      render();
    }
    var offLanguage = root.QuoridorI18n ? root.QuoridorI18n.onChange(relabel) : null;

    var controller = {
      game: function () { return game; },
      // Online: replace the game with the server's version. meta: {connected, forfeitIn, rematch, reason, notice, names}
      setState: function (json, m) {
        var prev = game.moves.length;
        game = Q.Game.fromJSON(json);
        meta = Object.assign({ connected: [true, true], forfeitIn: null, rematch: [false, false], reason: null }, m || {});
        if (meta.names) { names = meta.names.slice(); }
        if (game.moves.length < prev) { logList.textContent = ''; }
        if (game.moves.length > prev && prev > 0 || (game.moves.length > 0 && prev === 0 && lastCount === 0)) {
          var mv = game.moves[game.moves.length - 1];
          announce(describeMove((game.moves.length - 1) % 2, mv));
        }
        busy = false;
        var key = game.moves.length + ':' + game.winner;
        if (meta.turnLeft != null && key !== timerKey) { timerKey = key; resetTimer(meta.turnLeft); }
        else if (meta.turnLeft == null) deadline = null;
        render();
      },
      announce: announce,
      focus: function () { turn.focus(); },
      destroy: function () {
        destroyed = true;
        if (offLanguage) offLanguage();
        clearInterval(tickTimer);
        if (thinker) thinker.destroy();
        board.destroy();
        host.textContent = '';
        host.classList.remove('game');
      }
    };
    start();
    return controller;
  }

  root.QuoridorGame = { mount: mount };
})(typeof self !== 'undefined' ? self : this);
