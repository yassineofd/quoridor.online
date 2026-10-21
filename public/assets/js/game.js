/* Game screen shared by every playing mode: board, turn bar, player cards, controls, move log.

   QuoridorGame.mount(host, cfg) returns a controller.
     cfg.mode     'local' (hot-seat) | 'computer' | 'online'
     cfg.variant  which game to play (a key of Quoridor.VARIANTS); the classic game when left out
     cfg.players  how many play (2 unless the variant allows more); cfg.names then has one name per player
     cfg.options  the setup of a 'custom' game: { size, walls, borrow } (see Quoridor.CUSTOM_LIMITS)
     cfg.turnSeconds time to move in a local or computer game; 0 = no clock (32 when left out)
     cfg.bankSeconds each player's time for the whole local or computer game (300 when left out); ignored when there is no clock
     cfg.names    [name for player 0, name for player 1, ...]
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

  var TURN_SECONDS = 32;   // time to make a move; the online server enforces the same limit
  var BANK_SECONDS = 300;  // time each player has for the whole game (5 min), spent only on their own turns

  // 3:07 style clock text.
  function fmtClock(secs) {
    secs = Math.max(0, Math.ceil(secs));
    var s = secs % 60;
    return Math.floor(secs / 60) + ':' + (s < 10 ? '0' : '') + s;
  }

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
          worker.postMessage({ id: id, variant: game.variant, moves: game.moves, level: level });
        });
      },
      cancel: function () { pending = null; },
      destroy: function () { pending = null; if (worker) worker.terminate(); worker = null; }
    };
  }

  function mount(host, cfg) {
    var mode = cfg.mode;
    var seat = cfg.seat === undefined ? null : cfg.seat;
    var game = new Q.Game(cfg.variant, cfg.players, cfg.options);
    var turnSeconds = cfg.turnSeconds === undefined ? TURN_SECONDS : cfg.turnSeconds; // 0: the players take as long as they like
    var bankSeconds = cfg.bankSeconds === undefined ? BANK_SECONDS : cfg.bankSeconds;
    var bankOn = mode === 'online' || (turnSeconds > 0 && bankSeconds > 0);
    var banks = game.pawns.map(function () { return bankSeconds; }); // seconds left per player as of turnMark
    var turnMark = Date.now();                                        // when the player to move started using their bank
    var names = (cfg.names || [t('game.player1'), t('game.player2'), t('game.player3'), t('game.player4')].slice(0, game.nPlayers)).slice();
    var meta = { connected: [true, true], forfeitIn: null, rematch: [false, false], reason: null };
    var thinker = mode === 'computer' ? createThinker(cfg.level || 'medium') : null;
    var thinking = false, busy = false, destroyed = false, lastTurn = -1, lastCount = 0;
    var botName = names[1 - (seat === null ? 0 : seat)];

    host.textContent = '';
    host.classList.add('game');

    // ---- layout -----------------------------------------------------------------------
    var boardHost = h('div', { 'class': 'game-board-svg' });
    // Who sits at each end of the board (a board with one goal edge per player only).
    var twoSided = game.nPlayers === 2 && game.goals[0] !== game.goals[1];
    var tagTop = h('div', { 'class': 'board-tag', 'aria-hidden': 'true', hidden: '' }, [h('span', { 'class': 'board-tag-text' })]);
    var tagBottom = h('div', { 'class': 'board-tag', 'aria-hidden': 'true', hidden: '' }, [h('span', { 'class': 'board-tag-text' })]);
    var boardWrap = h('div', { 'class': 'game-board' }, [tagTop, boardHost, tagBottom]);
    var turn = h('div', { 'class': 'turn-bar', role: 'status', tabindex: '-1' });
    var banner = h('div', { 'class': 'notice game-banner', role: 'status', hidden: '' });
    var cards = game.pawns.map(function (pawn, i) {
      var glyph = h('span', { 'class': 'pawn-glyph pawn-glyph--' + i, 'aria-hidden': 'true' });
      var name = h('span', { 'class': 'player-name' });
      var tag = h('span', { 'class': 'player-tag' });
      var walls = h('span', { 'class': 'player-walls' });
      var clock = h('span', { 'class': 'player-clock', 'aria-hidden': 'true' });
      if (!bankOn) clock.hidden = true;
      var card = h('li', { 'class': 'player-card player-card--' + i }, [glyph, h('span', { 'class': 'player-text' }, [name, tag]), h('span', { 'class': 'player-meta' }, [walls, clock])]);
      return { card: card, name: name, tag: tag, walls: walls, clock: clock };
    });
    var timerText = h('span', { 'class': 'turn-timer-text', 'aria-hidden': 'true' });
    var timerFill = h('span', { 'class': 'turn-timer-fill' });
    var timer = h('div', { 'class': 'turn-timer', hidden: '' }, [timerText, h('span', { 'class': 'turn-timer-bar', 'aria-hidden': 'true' }, [timerFill])]);
    var vs = h('li', { 'class': 'vs-chip', 'aria-hidden': 'true', text: 'VS' });
    var players = h('ul', { 'class': 'players' + (game.nPlayers === 2 ? '' : ' players--multi'), 'aria-label': t('game.players') },
      game.nPlayers === 2 ? [cards[0].card, vs, cards[1].card] : cards.map(function (c) { return c.card; }));
    // You are on the left when you play from one seat; in hot-seat the first player is.
    if (game.nPlayers === 2 && seat === 1) { cards[1].card.style.order = '0'; vs.style.order = '1'; cards[0].card.style.order = '2'; }

    // Wall tray: how many walls the player has, and one draggable wall of each type. Drag one onto the board
    // (the nearest groove is previewed and it is placed on release), or tap it to pick a spot with taps instead.
    var trayCount = h('span', { 'class': 'wall-tray-count' });
    var trayInfo = h('span', { 'class': 'wall-tray-info', role: 'img' }, [trayCount]);
    if (root.QuoridorIcons) trayInfo.insertAdjacentHTML('afterbegin', '<span class="wall-tray-icon" aria-hidden="true">' + root.QuoridorIcons.svg('wall') + '</span>');
    var chips = ['h', 'v'].map(function (o) {
      var b = h('button', { type: 'button', 'class': 'wall-chip', 'data-o': o, 'aria-pressed': 'false' }, [h('span', { 'class': 'wall-chip-bar', 'aria-hidden': 'true' })]);
      b.__labelKey = o === 'h' ? 'game.horizontalWall' : 'game.verticalWall';
      b.setAttribute('aria-label', t(b.__labelKey));
      return b;
    });
    var tray = h('div', { 'class': 'wall-tray', role: 'group', 'aria-label': t('game.wallTray') }, [trayInfo, chips[0], chips[1]]);

    // Buttons are made from message keys, so a change of language can set their labels again (see relabel below).
    var rotateBtn = button('game.rotateWall', 'btn--secondary', function () { board.rotate(); }, 'rotate');
    var confirmBtn = button('game.confirmWall', 'btn--primary', function () { board.confirm(); }, 'check');
    var cancelBtn = button('game.cancel', 'btn--secondary', function () { board.cancel(); }, 'x');
    var wallRow = h('div', { 'class': 'btn-row wall-row', hidden: '' }, [rotateBtn, confirmBtn, cancelBtn]);
    var hint = h('p', { 'class': 'game-hint small text-muted', 'data-tip': t('game.tip') }); // shows the tip while it has nothing to say
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

    var side = h('div', { 'class': 'game-side' }, [banner, players, turn, timer, result, tray, wallRow, hint, controls, keys, log, announcer]);
    host.appendChild(h('div', { 'class': 'game-layout' }, [boardWrap, side]));

    // ---- clocks ---------------------------------------------------------------------------
    // Two clocks run: the move clock (turnSeconds, the bar under the players) and each player's bank for the
    // whole game, which drains only on their own turn. Hot-seat and computer games count down here: the move
    // clock plays the fallback move at zero, an empty bank loses the game. Online the server is in charge (it
    // sends turnLeft and clocks and acts itself); this only shows them.
    var deadline = null, timerKey = null, warned = false;

    function timerRunning() {
      if (game.winner !== null || destroyed) return false;
      if (mode !== 'online' && !turnSeconds) return false;
      if (mode === 'online') return deadline !== null;
      return mode === 'local' || (game.turn === seat && !thinking);
    }
    // Seconds left in player i's bank, counting the time their current turn has used so far.
    function liveBank(i) {
      var left = banks[i];
      if (i === game.turn && game.winner === null && !destroyed && (mode === 'online' || timerRunning())) left -= (Date.now() - turnMark) / 1000;
      return Math.max(0, left);
    }
    function chargeBank(i) { if (bankOn && mode !== 'online') banks[i] = liveBank(i); }
    // seconds: given online (the server's figure). Otherwise a new turn starts: the move limit, or less when the bank is lower.
    function resetTimer(seconds) {
      if (seconds === undefined) {
        turnMark = Date.now();
        seconds = bankOn ? Math.min(turnSeconds, liveBank(game.turn)) : turnSeconds;
      }
      deadline = Date.now() + seconds * 1000;
      warned = false;
    }
    function paintClocks() {
      if (!bankOn) return;
      cards.forEach(function (c, i) {
        var left = liveBank(i), text = fmtClock(left);
        if (c.clock.textContent !== text) c.clock.textContent = text;
        c.clock.classList.toggle('is-low', left <= 30);
      });
    }
    function tick() {
      if (deadline === null && mode !== 'online' && timerRunning()) resetTimer();
      var running = timerRunning();
      timer.hidden = !running;
      paintClocks();
      if (!running) return;
      var left = Math.max(0, deadline - Date.now());
      var secs = Math.ceil(left / 1000);
      timerText.textContent = t('game.timerLeft', { who: sayWho(game.turn), n: secs });
      timerFill.style.width = Math.min(100, left / ((mode === 'online' ? TURN_SECONDS : turnSeconds) * 10)) + '%';
      timer.classList.toggle('is-low', secs <= 5);
      if (secs <= 5 && !warned && left > 0 && (mode === 'local' || game.turn === seat)) { warned = true; announce(t('game.secondsLeft', { n: secs })); }
      if (left <= 0 && mode !== 'online') { if (bankOn && liveBank(game.turn) <= 0.05) outOfTime(game.turn); else timeUp(); }
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
    // A player's bank ran dry: they lose the game.
    function outOfTime(who) {
      deadline = null;
      banks[who] = 0;
      game.resign(who);
      meta.reason = 'timeout';
      render();
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
    host.style.setProperty('--board-ratio', String(board.ratio)); // a tall board must not claim the width of a square one

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
        c.card.classList.toggle('is-me', i === seat);
        if (!over && game.turn === i) c.card.setAttribute('aria-current', 'true'); else c.card.removeAttribute('aria-current');
      });

      // Names at the two ends of the board: the one at the bottom is the player whose goal is the top row (the other way round when the board is turned).
      if (twoSided) {
        var bottom = (game.goals[0] < game.goals[1] ? 0 : 1) ^ (cfg.flip ? 1 : 0);
        [[tagTop, 1 - bottom, '\u25B2'], [tagBottom, bottom, '\u25BC']].forEach(function (x) {
          x[0].hidden = false;
          x[0].className = 'board-tag board-tag--p' + x[1];
          x[0].firstChild.textContent = x[2] + ' ' + names[x[1]];
        });
      }

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
        var m = game.moves[i], who = i % game.nPlayers; // player 0 always moves first, then in turn
        logList.appendChild(h('li', { text: t(m.type === 'move' ? 'game.logMoved' : 'game.logWall', { name: names[who], move: game.moveName(m) }) }));
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
      var viewer = seat !== null ? seat : game.turn;
      var wallsLeft = act ? game.wallsLeft[actor()] : 0;
      if (act && wallsLeft <= 0 && m === 'wall') { board.setMode('move'); return; }
      m = board.getMode();
      tray.setAttribute('data-pawn', String(viewer));
      trayCount.textContent = String(game.wallsLeft[viewer]);
      trayInfo.setAttribute('aria-label', t('game.wallsCount', { n: game.wallsLeft[viewer] }));
      chips.forEach(function (b) {
        b.disabled = !act || wallsLeft <= 0;
        b.setAttribute('aria-pressed', String(m === 'wall' && board.getOrient() === b.getAttribute('data-o')));
      });
      wallRow.hidden = !(act && m === 'wall');
      rotateBtn.disabled = !act;
      confirmBtn.disabled = !(sel && sel.legal);
      cancelBtn.disabled = !sel;
      if (act && m === 'wall' && sel && !sel.legal) hint.textContent = sel.reason;
      var over = game.winner !== null;
      tray.hidden = over;
      if (undoBtn) undoBtn.disabled = over || thinking || game.moves.length < (mode === 'computer' ? 2 : 1) || (mode === 'computer' && game.turn !== seat);
      if (resignBtn) resignBtn.disabled = over || (mode === 'computer' && thinking);
      if (mode === 'online' && banner) renderBanner();
    }

    // ---- carrying a wall from the tray ------------------------------------------------------
    // Press and drag: the wall follows the pointer, the nearest groove on the board is previewed (red when it is
    // not allowed), and letting go places it. A press that barely moves is a tap: it picks that wall type for the
    // tap-then-confirm way of placing (and a second tap puts it back). The keyboard gets the same through Enter.
    var ghost = null, carrying = null;
    function toggleWallType(o) {
      if (board.getMode() === 'wall' && board.getOrient() === o) board.setMode('move');
      else { board.setMode('wall'); board.setOrient(o); }
    }
    function moveGhost(x, y, pointerType, onBoard) {
      if (!ghost) {
        ghost = h('div', { 'class': 'wall-ghost', 'aria-hidden': 'true' });
        // The wall as long as two squares and a groove, in the size the board is drawn at.
        var scale = board.svg.getBoundingClientRect().width / board.svg.viewBox.baseVal.width;
        var len = (2 * B.CELL + B.GAP) * scale, thick = B.GAP * scale;
        ghost.style.width = (carrying.o === 'h' ? len : thick) + 'px';
        ghost.style.height = (carrying.o === 'h' ? thick : len) + 'px';
        document.body.appendChild(ghost);
      }
      ghost.className = 'wall-ghost wall-ghost--p' + (seat !== null ? seat : game.turn);
      ghost.style.opacity = onBoard ? '0' : '1';
      ghost.style.transform = 'translate(' + x + 'px,' + (y - (pointerType !== 'mouse' ? B.TOUCH_LIFT : 0)) + 'px) translate(-50%,-50%)';
    }
    function endCarry() {
      if (carrying && carrying.stop) carrying.stop();
      if (ghost && ghost.parentNode) ghost.parentNode.removeChild(ghost);
      ghost = null; carrying = null;
      host.classList.remove('is-carrying');
    }
    chips.forEach(function (b) {
      var o = b.getAttribute('data-o');
      // The moves and the release are listened for on the document for as long as the press lasts, so the drag keeps
      // working wherever the pointer goes (capturing the pointer as well is only a help).
      function onMove(e) {
        if (!carrying || e.pointerId !== carrying.id) return;
        if (!carrying.moved) {
          if (Math.hypot(e.clientX - carrying.x0, e.clientY - carrying.y0) < 8) return;
          carrying.moved = true;
          if (board.getMode() !== 'move') board.setMode('move');
          host.classList.add('is-carrying');
        }
        var st = board.dragTo(e.clientX, e.clientY, o, carrying.type);
        hint.textContent = st && !st.legal ? st.reason : '';
        moveGhost(e.clientX, e.clientY, carrying.type, !!st);
        e.preventDefault();
      }
      function onEnd(e) {
        if (!carrying || e.pointerId !== carrying.id) return;
        var c = carrying, cancelled = e.type === 'pointercancel';
        try { b.releasePointerCapture(e.pointerId); } catch (err) { /* not captured */ }
        endCarry();
        if (!c.moved) { if (!cancelled) toggleWallType(o); return; }
        if (cancelled) board.dragCancel(); else board.dragDrop();
      }
      b.addEventListener('pointerdown', function (e) {
        if (b.disabled || carrying || (e.pointerType === 'mouse' && e.button !== 0)) return;
        carrying = { o: o, id: e.pointerId, x0: e.clientX, y0: e.clientY, moved: false, type: e.pointerType || 'mouse', chip: b };
        try { b.setPointerCapture(e.pointerId); } catch (err) { /* the document listeners below carry the drag */ }
        document.addEventListener('pointermove', onMove);
        document.addEventListener('pointerup', onEnd);
        document.addEventListener('pointercancel', onEnd);
        carrying.stop = function () {
          document.removeEventListener('pointermove', onMove);
          document.removeEventListener('pointerup', onEnd);
          document.removeEventListener('pointercancel', onEnd);
        };
        e.preventDefault();
      });
      // Enter / Space on the focused chip (a pointer tap is handled above).
      b.addEventListener('click', function (e) { if (e.detail === 0 && !b.disabled) toggleWallType(o); });
    });

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
        : meta.reason === 'timeout' ? (seat !== null && !youWon ? t('game.timedOutSelf') : t('game.timedOutName', { name: names[(game.winner + game.nPlayers - 1) % game.nPlayers] }))
        : '';
      var lastMove = game.moves[game.moves.length - 1];
      var byMove = !why && lastMove && lastMove.type === 'move' ? t(game.goalCell ? 'game.reachedCenter' : 'game.reachedEdge', { n: Math.ceil(game.moves.length / game.nPlayers) }) : '';
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
      return t(m.type === 'move' ? 'game.moved' : 'game.placedWall', { who: sayWho(player), move: game.moveName(m) });
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
      chargeBank(who);
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
      [rotateBtn, confirmBtn, cancelBtn, undoBtn, resignBtn, restartBtn, leaveBtn].forEach(function (b) {
        if (b) setLabel(b, b.__labelKey);
      });
      chips.forEach(function (b) { b.setAttribute('aria-label', t(b.__labelKey)); });
      tray.setAttribute('aria-label', t('game.wallTray'));
      hint.setAttribute('data-tip', t('game.tip'));
      players.setAttribute('aria-label', t('game.players'));
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
          announce(describeMove((game.moves.length - 1) % game.nPlayers, mv));
        }
        busy = false;
        if (meta.clocks) { banks = meta.clocks.slice(); turnMark = Date.now() - (meta.clocksAge || 0) * 1000; }
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
        endCarry();
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
