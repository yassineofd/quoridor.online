/* Game screen shared by every playing mode: board, turn bar, player cards, controls, move log.

   QuoridorGame.mount(host, cfg) returns a controller.
     cfg.mode     'local' (hot-seat) | 'computer' | 'online'
     cfg.names    [name for player 0, name for player 1]
     cfg.seat     which player "you" are (computer / online); null for hot-seat
     cfg.flip     draw the board rotated so that `seat` is at the bottom
     cfg.level    computer difficulty
     cfg.remote   online only: { send(move) -> Promise, resign(), leave(), rematch() }
     cfg.onExit   called with 'again' or 'leave' when the player finishes
   For online games the owner pushes server state in with controller.setState(json, meta).      */
(function (root) {
  'use strict';
  var Q = root.Quoridor, B = root.QuoridorBoard;

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
  function button(text, cls, onClick) {
    var b = h('button', { type: 'button', 'class': 'btn ' + (cls || 'btn--secondary'), text: text });
    b.addEventListener('click', onClick);
    return b;
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
    var names = (cfg.names || ['Player 1', 'Player 2']).slice();
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
    var players = h('ul', { 'class': 'players', 'aria-label': 'Players' }, cards.map(function (c) { return c.card; }));

    var modeBtns = {
      move: button('Move pawn', 'btn--secondary btn--toggle', function () { board.setMode('move'); }),
      wall: button('Place wall', 'btn--secondary btn--toggle', function () { board.setMode('wall'); })
    };
    var rotateBtn = button('Rotate wall', 'btn--secondary', function () { board.rotate(); });
    var confirmBtn = button('Place selected wall', 'btn--primary', function () { board.confirm(); });
    var cancelBtn = button('Cancel', 'btn--secondary', function () { board.cancel(); });
    var actionRow = h('div', { 'class': 'btn-row', role: 'group', 'aria-label': 'Choose an action' }, [modeBtns.move, modeBtns.wall]);
    var wallRow = h('div', { 'class': 'btn-row wall-row', hidden: '' }, [rotateBtn, confirmBtn, cancelBtn]);
    var hint = h('p', { 'class': 'game-hint small text-muted' });
    var keys = h('p', { 'class': 'small text-muted game-keys', text: 'Keyboard: focus the board, arrows to choose, Enter to confirm, W for walls, R to rotate, M for pawn, Esc to cancel.' });

    var undoBtn = mode !== 'online' ? button('Undo', 'btn--secondary', onUndo) : null;
    var resignBtn = mode !== 'local' ? button('Resign', 'btn--secondary', onResign) : null;
    var restartBtn = mode !== 'online' ? button('Restart', 'btn--secondary', onRestart) : null;
    var leaveBtn = button(mode === 'online' ? 'Leave game' : 'Leave', 'btn--secondary', onLeave);
    var controls = h('div', { 'class': 'btn-row game-controls' }, [undoBtn, resignBtn, restartBtn, leaveBtn]);

    var resultTitle = h('h2', { 'class': 'h-sm', tabindex: '-1' });
    var resultText = h('p', { 'class': 'text-muted' });
    var resultActions = h('div', { 'class': 'btn-row' });
    var result = h('div', { 'class': 'card result', hidden: '' }, [resultTitle, resultText, resultActions]);

    var logList = h('ol', { 'class': 'move-log' });
    var log = h('details', { 'class': 'move-log-wrap', open: '' }, [h('summary', { text: 'Move list' }), logList]);
    // On phones the move list starts collapsed so the board and controls fit on screen.
    if (window.matchMedia && window.matchMedia('(max-width: 899px)').matches) log.removeAttribute('open');
    var announcer = h('div', { 'class': 'sr-only', 'aria-live': 'polite', 'aria-atomic': 'true' });

    var side = h('div', { 'class': 'game-side' }, [turn, banner, players, result, actionRow, wallRow, hint, controls, keys, log, announcer]);
    host.appendChild(h('div', { 'class': 'game-layout' }, [boardHost, side]));

    function announce(text) { announcer.textContent = ''; setTimeout(function () { announcer.textContent = text; }, 20); }

    var board = B.create(boardHost, {
      game: game,
      names: names,
      flip: !!cfg.flip,
      onCommit: commit,
      onAnnounce: function (t) { hint.textContent = t; announce(t); },
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

    function sayWho(i) { return i === seat && seat !== null ? 'You' : names[i]; }

    function render() {
      board.setGame(game);
      board.setActor(actor());
      board.setLast(game.moves.length ? game.moves[game.moves.length - 1] : null);
      board.refresh();

      var over = game.winner !== null;
      cards.forEach(function (c, i) {
        c.name.textContent = names[i];
        c.tag.textContent = (i === seat ? ' (you)' : '') + (meta.connected[i] === false && mode === 'online' ? ' (disconnected)' : '');
        c.walls.textContent = 'Walls: ' + game.wallsLeft[i];
        c.card.classList.toggle('is-active', !over && game.turn === i);
        c.card.classList.toggle('is-winner', over && game.winner === i);
        if (!over && game.turn === i) c.card.setAttribute('aria-current', 'true'); else c.card.removeAttribute('aria-current');
      });

      // Turn bar
      var text;
      if (over) text = (game.winner === seat ? 'You win!' : (seat === null ? names[game.winner] + ' wins!' : names[game.winner] + ' wins'));
      else if (mode === 'local') text = names[game.turn] + "'s turn";
      else if (game.turn === seat) text = 'Your turn';
      else text = mode === 'computer' ? botName + ' is thinking…' : names[game.turn] + "'s turn";
      if (turn.textContent !== text) {
        turn.textContent = text;
        if (!over && game.turn !== lastTurn) { turn.classList.remove('flash'); void turn.offsetWidth; turn.classList.add('flash'); }
      }
      lastTurn = game.turn;

      // Move log
      while (logList.children.length > game.moves.length) logList.removeChild(logList.lastChild);
      for (var i = logList.children.length; i < game.moves.length; i++) {
        var m = game.moves[i], who = i % 2; // player 0 always moves first
        logList.appendChild(h('li', { text: names[who] + ': ' + (m.type === 'move' ? 'moved to ' + Q.moveName(m) : 'placed wall ' + Q.moveName(m)) }));
      }
      logList.scrollTop = logList.scrollHeight;

      // Result panel
      result.hidden = !over;
      if (over) showResult();

      if (mode === 'local' && !over && game.moves.length > lastCount) {
        hint.textContent = 'Pass the device to ' + names[game.turn] + '.';
      } else if (!over && game.turn === actor()) {
        hint.textContent = '';
      }
      lastCount = game.moves.length;
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
        banner.textContent = names[opp] + ' lost their connection. ' + (meta.forfeitIn != null ? 'They forfeit in about ' + Math.max(0, Math.ceil(meta.forfeitIn)) + ' seconds if they do not return.' : 'Waiting for them to return.');
      } else if (meta.notice) {
        banner.hidden = false; banner.textContent = meta.notice;
      } else {
        banner.hidden = true; banner.textContent = '';
      }
    }

    function showResult() {
      var youWon = seat !== null && game.winner === seat;
      resultTitle.textContent = seat === null ? names[game.winner] + ' wins' : (youWon ? 'You won' : names[game.winner] + ' won');
      var why = meta.reason === 'resign' ? (youWon ? ' Your opponent resigned.' : ' Resignation.')
        : meta.reason === 'disconnect' ? (youWon ? ' Your opponent left the game.' : ' You were disconnected for too long.')
        : '';
      var lastMove = game.moves[game.moves.length - 1];
      var byMove = !why && lastMove && lastMove.type === 'move' ? ' Reached the far edge in ' + Math.ceil(game.moves.length / 2) + ' turns.' : '';
      resultText.textContent = (why || byMove).trim();
      resultActions.textContent = '';
      if (mode === 'online') {
        var wanted = seat !== null && meta.rematch[seat];
        var oppWants = seat !== null && meta.rematch[1 - seat];
        var rb = button(wanted ? 'Rematch requested' : (oppWants ? 'Accept rematch' : 'Request rematch'), 'btn--primary', function () { cfg.remote.rematch(); });
        rb.disabled = wanted;
        resultActions.appendChild(rb);
        if (oppWants && !wanted) resultText.textContent += ' Your opponent wants a rematch.';
      } else {
        resultActions.appendChild(button('Play again', 'btn--primary', function () { exit('again'); }));
      }
      resultActions.appendChild(button('Leave', 'btn--secondary', function () { exit('leave'); }));
      if (!result.dataset.announced || result.dataset.announced !== String(game.winner) + game.moves.length) {
        result.dataset.announced = String(game.winner) + game.moves.length;
        announce(resultTitle.textContent + '. ' + resultText.textContent);
        resultTitle.focus();
      }
    }

    // ---- applying moves ---------------------------------------------------------------
    function describeMove(player, m) {
      return sayWho(player) + (m.type === 'move' ? ' moved to ' : ' placed wall ') + Q.moveName(m) + '.';
    }

    function commit(move) {
      var who = game.turn;
      if (mode === 'online') {
        busy = true; render();
        cfg.remote.send(move).then(function () { busy = false; }, function (err) {
          busy = false; render();
          hint.textContent = (err && err.message) || 'That move was not accepted.';
          announce(hint.textContent);
        });
        return;
      }
      var err = game.apply(move);
      if (err) { hint.textContent = 'That move is not allowed.'; announce(hint.textContent); return; }
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
      hint.textContent = 'Move taken back.';
      announce('Move taken back.');
      render();
    }
    function onRestart() {
      if (game.moves.length && game.winner === null && !window.confirm('Restart the game? The current game will be lost.')) return;
      exit('again');
    }
    function onResign() {
      if (!window.confirm('Resign this game? Your opponent will be the winner.')) return;
      if (mode === 'online') { cfg.remote.resign(); return; }
      if (thinker) { thinking = false; thinker.cancel(); }
      game.resign(seat);
      meta.reason = 'resign';
      render();
    }
    function onLeave() {
      var live = game.winner === null && game.moves.length > 0;
      var text = mode === 'online' && live ? 'Leave this game? Leaving counts as a forfeit.' : 'Leave this game?';
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
        render();
      },
      announce: announce,
      focus: function () { turn.focus(); },
      destroy: function () {
        destroyed = true;
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
