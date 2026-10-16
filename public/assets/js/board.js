/* Quoridor board: an accessible SVG view of a Quoridor.Game plus pointer, touch and keyboard input.

   The board only draws and collects intent. It never changes the game: when the player picks a
   move it calls opts.onCommit(move) and the owner applies it (locally, or by asking the server)
   and then calls refresh().

   Input
     pawn mode  click / tap a highlighted square. Keyboard: arrows move the cursor, Enter moves.
     wall mode  the groove nearest the pointer is previewed. Mouse: click places it. Touch / pen:
                tap selects, then Confirm. Keyboard: arrows move the wall, R rotates, Enter places.
     W / M      switch to wall / pawn mode.  Esc: cancel a wall selection.                      */
(function (root) {
  'use strict';
  var Q = root.Quoridor;

  var CELL = 78, GAP = 14, PAD = 16, PITCH = CELL + GAP;
  var SIZE = PAD * 2 + 9 * CELL + 8 * GAP;
  var NS = 'http://www.w3.org/2000/svg';

  function el(tag, attrs, parent) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) if (Object.prototype.hasOwnProperty.call(attrs, k)) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }
  function cellPos(i) { return PAD + i * PITCH; }
  function anchorPos(i) { return PAD + i * PITCH + CELL + GAP / 2; } // centre of the groove crossing after index i

  var REASONS = {
    'overlap': 'That wall overlaps another wall.',
    'cross': 'That wall would cross another wall.',
    'blocks-path': 'That wall would leave a pawn with no route to its goal.',
    'no-walls': 'You have no walls left.',
    'out-of-bounds': 'That wall is off the board.'
  };

  function create(container, opts) {
    var game = opts.game;
    var flip = !!opts.flip;
    var names = opts.names || ['Player 1', 'Player 2'];
    var state = {
      mode: 'move',          // 'move' | 'wall'
      actor: null,           // player index allowed to act, or null when the board is read-only
      cursor: [8, 4],        // keyboard cursor for squares
      wallCursor: { o: 'h', r: 3, c: 3 },
      sel: null,             // selected wall {o,r,c}
      hover: null,           // hovered wall (mouse)
      keyboard: false,       // show the keyboard cursor
      last: null
    };

    var svg = el('svg', {
      'class': 'board', viewBox: '0 0 ' + SIZE + ' ' + SIZE, role: 'application',
      tabindex: '0', 'aria-roledescription': 'Quoridor board', focusable: 'true'
    });
    var title = el('title', {}, svg); title.textContent = 'Quoridor board';
    var desc = el('desc', {}, svg);
    var world = el('g', {}, svg);
    if (flip) world.setAttribute('transform', 'rotate(180 ' + SIZE / 2 + ' ' + SIZE / 2 + ')');
    el('rect', { width: SIZE, height: SIZE, rx: 28, fill: '#0b1220' }, world);

    var cellEls = [];
    for (var r = 0; r < 9; r++) {
      for (var c = 0; c < 9; c++) {
        el('rect', { x: cellPos(c), y: cellPos(r), width: CELL, height: CELL, rx: 9, fill: '#111c30', stroke: '#26364f', 'stroke-width': 2 }, world);
        if (r === 0) el('rect', { x: cellPos(c), y: cellPos(r), width: CELL, height: CELL, rx: 9, fill: '#42d9f5', 'fill-opacity': 0.13 }, world);
        if (r === 8) el('rect', { x: cellPos(c), y: cellPos(r), width: CELL, height: CELL, rx: 9, fill: '#ff9f43', 'fill-opacity': 0.13 }, world);
      }
    }
    var gHints = el('g', {}, world), gWalls = el('g', {}, world), gPreview = el('g', {}, world),
        gPawns = el('g', {}, world), gCursor = el('g', {}, world);
    world.setAttribute('pointer-events', 'none');
    // Pointer events always land on this one stable layer. The pieces above are redrawn often (on
    // focus, on hover), and a click is lost if the element under the pointer is replaced between
    // mouse-down and mouse-up.
    el('rect', { width: SIZE, height: SIZE, fill: 'transparent', 'pointer-events': 'all' }, svg);
    container.appendChild(svg);

    // ---- geometry helpers -----------------------------------------------------------
    function wallRect(o, r, c) {
      return o === 'h'
        ? { x: cellPos(c), y: cellPos(r) + CELL, width: 2 * CELL + GAP, height: GAP }
        : { x: cellPos(c) + CELL, y: cellPos(r), width: GAP, height: 2 * CELL + GAP };
    }
    function drawWall(parent, o, r, c, attrs) {
      var rc = wallRect(o, r, c);
      var a = { x: rc.x, y: rc.y, width: rc.width, height: rc.height, rx: 6 };
      for (var k in attrs) a[k] = attrs[k];
      return el('rect', a, parent);
    }

    function toBoard(clientX, clientY) {
      var b = svg.getBoundingClientRect();
      var x = (clientX - b.left) / b.width * SIZE, y = (clientY - b.top) / b.height * SIZE;
      return flip ? { x: SIZE - x, y: SIZE - y } : { x: x, y: y };
    }
    function cellAt(p) {
      var c = Math.floor((p.x - PAD + GAP / 2) / PITCH), r = Math.floor((p.y - PAD + GAP / 2) / PITCH);
      return r >= 0 && r < 9 && c >= 0 && c < 9 ? [r, c] : null;
    }
    function slotAt(p) {
      var c = Math.max(0, Math.min(7, Math.round((p.x - anchorPos(0)) / PITCH)));
      var r = Math.max(0, Math.min(7, Math.round((p.y - anchorPos(0)) / PITCH)));
      var dx = p.x - anchorPos(c), dy = p.y - anchorPos(r);
      return { o: Math.abs(dx) > Math.abs(dy) ? 'h' : 'v', r: r, c: c };
    }

    function legalTargets() { return state.actor !== null && state.actor === game.turn && game.winner === null ? game.pawnMoves(state.actor) : []; }
    function wallStatus(w) {
      if (!w) return null;
      var err = state.actor === null ? 'no-walls' : game.wallError(w.o, w.r, w.c, state.actor);
      return { wall: w, legal: err === null, reason: err ? REASONS[err] : '' };
    }
    function canAct() { return state.actor !== null && state.actor === game.turn && game.winner === null; }

    // ---- drawing --------------------------------------------------------------------
    function draw() {
      [gHints, gWalls, gPreview, gPawns, gCursor].forEach(function (g) { while (g.firstChild) g.removeChild(g.firstChild); });

      var i, w, j;
      if (canAct() && state.mode === 'move') {
        var targets = legalTargets();
        for (i = 0; i < targets.length; i++) {
          var tr = targets[i][0], tc = targets[i][1];
          el('rect', { x: cellPos(tc), y: cellPos(tr), width: CELL, height: CELL, rx: 9, fill: '#42d9f5', 'fill-opacity': 0.16, stroke: '#42d9f5', 'stroke-width': 3 }, gHints);
          el('circle', { cx: cellPos(tc) + CELL / 2, cy: cellPos(tr) + CELL / 2, r: 11, fill: '#42d9f5' }, gHints);
        }
      }
      if (state.last && state.last.type === 'move') {
        el('rect', { x: cellPos(state.last.c) + 2, y: cellPos(state.last.r) + 2, width: CELL - 4, height: CELL - 4, rx: 8, fill: 'none', stroke: '#ffffff', 'stroke-opacity': 0.5, 'stroke-width': 2, 'stroke-dasharray': '6 5' }, gHints);
      }

      var walls = game.toJSON().walls;
      for (i = 0; i < walls.length; i++) {
        w = walls[i];
        var isLast = state.last && state.last.type === 'wall' && state.last.o === w[0] && state.last.r === w[1] && state.last.c === w[2];
        drawWall(gWalls, w[0], w[1], w[2], { fill: '#5267f2', stroke: isLast ? '#ffffff' : '#9aa8ff', 'stroke-width': isLast ? 3 : 1.5 });
      }

      if (state.mode === 'wall' && canAct()) {
        var shown = state.sel || state.hover || (state.keyboard ? state.wallCursor : null);
        var st = wallStatus(shown);
        if (st) {
          drawWall(gPreview, st.wall.o, st.wall.r, st.wall.c, st.legal
            ? { fill: '#5267f2', 'fill-opacity': 0.55, stroke: '#42d9f5', 'stroke-width': 3, 'stroke-dasharray': '8 4' }
            : { fill: '#ff8a96', 'fill-opacity': 0.45, stroke: '#ff8a96', 'stroke-width': 3, 'stroke-dasharray': '3 3' });
        }
      }

      for (i = 0; i < 2; i++) {
        var pr = game.pawns[i][0], pc = game.pawns[i][1], cx = cellPos(pc) + CELL / 2, cy = cellPos(pr) + CELL / 2;
        var active = game.winner === null && game.turn === i;
        if (game.winner === i) el('circle', { cx: cx, cy: cy, r: 36, fill: 'none', stroke: '#5eead4', 'stroke-width': 4 }, gPawns);
        else if (active) el('circle', { cx: cx, cy: cy, r: 35, fill: 'none', stroke: '#ffffff', 'stroke-opacity': 0.45, 'stroke-width': 2 }, gPawns);
        el('circle', { cx: cx, cy: cy, r: 27, fill: i === 0 ? '#42d9f5' : '#ff9f43' }, gPawns);
      }

      if (state.keyboard && document.activeElement === svg) {
        var cur;
        if (state.mode === 'wall') {
          var wc = state.wallCursor, rc = wallRect(wc.o, wc.r, wc.c);
          cur = el('rect', { x: rc.x - 4, y: rc.y - 4, width: rc.width + 8, height: rc.height + 8, rx: 9, fill: 'none', stroke: '#ffffff', 'stroke-width': 2.5, 'stroke-dasharray': '5 4' }, gCursor);
        } else {
          cur = el('rect', { x: cellPos(state.cursor[1]) - 3, y: cellPos(state.cursor[0]) - 3, width: CELL + 6, height: CELL + 6, rx: 11, fill: 'none', stroke: '#ffffff', 'stroke-width': 3, 'stroke-dasharray': '6 4' }, gCursor);
        }
      }

      desc.textContent = describe(true);
      svg.setAttribute('aria-label', 'Quoridor board. ' + describe(false));
    }

    // Short summary for the label; with the full wall list it goes in the description.
    function describe(withWallList) {
      var list = game.toJSON().walls, walls = list.length;
      var parts = [
        names[0] + ' pawn on ' + Q.squareName(game.pawns[0][0], game.pawns[0][1]) + ', ' + game.wallsLeft[0] + ' walls left.',
        names[1] + ' pawn on ' + Q.squareName(game.pawns[1][0], game.pawns[1][1]) + ', ' + game.wallsLeft[1] + ' walls left.'
      ];
      parts.push(walls + (walls === 1 ? ' wall' : ' walls') + ' placed.');
      if (withWallList && walls) parts.push('Walls: ' + list.map(function (x) { return Q.wallName(x[0], x[1], x[2]); }).join(', ') + '.');
      return parts.join(' ');
    }

    // ---- intent -----------------------------------------------------------------------
    function notify() { if (opts.onChange) opts.onChange(api.selection()); }
    function say(text) { if (opts.onAnnounce) opts.onAnnounce(text); }

    function commitWall(w) {
      var st = wallStatus(w);
      if (!st) return;
      if (!st.legal) { say(st.reason); return; }
      state.sel = null; state.hover = null;
      opts.onCommit({ type: 'wall', o: w.o, r: w.r, c: w.c });
    }
    function commitMove(r, c) {
      if (!canAct()) return;
      var t = legalTargets(), ok = false;
      for (var i = 0; i < t.length; i++) if (t[i][0] === r && t[i][1] === c) ok = true;
      if (!ok) { say(Q.squareName(r, c) + ' is not a legal move.'); return; }
      opts.onCommit({ type: 'move', r: r, c: c });
    }

    var lastPointerType = 'mouse';
    svg.addEventListener('pointerdown', function (e) { lastPointerType = e.pointerType || 'mouse'; state.keyboard = false; });
    svg.addEventListener('pointermove', function (e) {
      if (e.pointerType && e.pointerType !== 'mouse') return;
      if (state.mode !== 'wall' || !canAct()) return;
      var s = slotAt(toBoard(e.clientX, e.clientY));
      if (!state.hover || state.hover.o !== s.o || state.hover.r !== s.r || state.hover.c !== s.c) { state.hover = s; draw(); notify(); }
    });
    svg.addEventListener('pointerleave', function () { if (state.hover) { state.hover = null; draw(); notify(); } });
    svg.addEventListener('click', function (e) {
      if (!canAct()) return;
      var p = toBoard(e.clientX, e.clientY);
      if (state.mode === 'move') {
        var cell = cellAt(p);
        if (cell) commitMove(cell[0], cell[1]);
      } else {
        var s = slotAt(p);
        if (lastPointerType === 'mouse' && e.detail !== 0) { commitWall(s); return; }
        state.sel = s; state.wallCursor = s; draw(); notify();
        var st = wallStatus(s);
        say(st.legal ? 'Wall ' + Q.wallName(s.o, s.r, s.c) + ' selected. Confirm to place it.' : st.reason);
      }
    });
    svg.addEventListener('focus', function () {
      try { if (svg.matches(':focus-visible')) state.keyboard = true; } catch (e) { /* older browsers */ }
      draw();
    });
    svg.addEventListener('blur', function () { draw(); });

    // Arrow keys are screen directions; the board may be rotated for the second seat.
    function screenDelta(key) {
      var d = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] }[key];
      return flip ? [-d[0], -d[1]] : d;
    }
    svg.addEventListener('keydown', function (e) {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      var k = e.key, handled = true;
      if (k.indexOf('Arrow') === 0) {
        state.keyboard = true;
        var d = screenDelta(k);
        if (state.mode === 'wall') {
          var wc = state.wallCursor;
          state.wallCursor = { o: wc.o, r: Math.max(0, Math.min(7, wc.r + d[0])), c: Math.max(0, Math.min(7, wc.c + d[1])) };
          state.sel = null;
          var st = wallStatus(state.wallCursor);
          say('Wall ' + Q.wallName(state.wallCursor.o, state.wallCursor.r, state.wallCursor.c) + (st && st.legal ? ', legal.' : '. ' + (st ? st.reason : '')));
        } else {
          state.cursor = [Math.max(0, Math.min(8, state.cursor[0] + d[0])), Math.max(0, Math.min(8, state.cursor[1] + d[1]))];
          var targets = legalTargets(), legal = false;
          for (var i = 0; i < targets.length; i++) if (targets[i][0] === state.cursor[0] && targets[i][1] === state.cursor[1]) legal = true;
          var who = game.pawns[0][0] === state.cursor[0] && game.pawns[0][1] === state.cursor[1] ? ', ' + names[0] + ' pawn'
                  : game.pawns[1][0] === state.cursor[0] && game.pawns[1][1] === state.cursor[1] ? ', ' + names[1] + ' pawn' : '';
          say(Q.squareName(state.cursor[0], state.cursor[1]) + who + (legal ? ', you can move here.' : '.'));
        }
      } else if (k === 'Enter' || k === ' ') {
        state.keyboard = true;
        if (!canAct()) { say('It is not your turn.'); }
        else if (state.mode === 'wall') commitWall(state.wallCursor);
        else commitMove(state.cursor[0], state.cursor[1]);
      } else if (k === 'r' || k === 'R') {
        if (state.mode === 'wall') api.rotate(); else handled = false;
      } else if (k === 'w' || k === 'W') {
        api.setMode('wall'); state.keyboard = true;
        say('Wall mode. Arrow keys move the wall, R rotates it, Enter places it.');
      } else if (k === 'm' || k === 'M') {
        api.setMode('move'); state.keyboard = true;
        say('Pawn mode. Arrow keys choose a square, Enter moves there.');
      } else if (k === 'Escape') {
        if (state.sel) { state.sel = null; draw(); notify(); say('Wall selection cancelled.'); }
        else if (state.mode === 'wall') { api.setMode('move'); say('Pawn mode.'); }
        else handled = false;
      } else {
        handled = false;
      }
      if (handled) { e.preventDefault(); draw(); notify(); }
    });

    var api = {
      svg: svg,
      setGame: function (g) { game = g; state.sel = null; state.hover = null; draw(); notify(); },
      refresh: function () {
        if (state.sel && !wallStatus(state.sel).legal) state.sel = null;
        draw(); notify();
      },
      setActor: function (player) { state.actor = player; if (player !== null) state.cursor = game.pawns[player].slice(); state.sel = null; state.hover = null; draw(); notify(); },
      setMode: function (m) { state.mode = m; state.sel = null; state.hover = null; draw(); notify(); if (opts.onMode) opts.onMode(m); },
      getMode: function () { return state.mode; },
      rotate: function () {
        var s = state.sel || state.hover || state.wallCursor;
        var n = { o: s.o === 'h' ? 'v' : 'h', r: s.r, c: s.c };
        state.wallCursor = n;
        if (state.sel) state.sel = n;
        state.hover = null;
        draw(); notify();
        var st = wallStatus(n);
        say('Wall ' + Q.wallName(n.o, n.r, n.c) + (st && st.legal ? ', legal.' : '. ' + (st ? st.reason : '')));
      },
      // Place the selected wall (touch / pen flow).
      confirm: function () { if (state.sel) commitWall(state.sel); },
      cancel: function () { state.sel = null; draw(); notify(); },
      // Current wall selection: null, or {wall, legal, reason}.
      selection: function () { return state.mode === 'wall' ? wallStatus(state.sel) : null; },
      hoverStatus: function () { return state.mode === 'wall' ? wallStatus(state.hover) : null; },
      setLast: function (m) { state.last = m || null; },
      focus: function () { svg.focus(); },
      destroy: function () { if (svg.parentNode) svg.parentNode.removeChild(svg); }
    };
    draw();
    return api;
  }

  root.QuoridorBoard = { create: create, SIZE: SIZE };
})(typeof self !== 'undefined' ? self : this);
