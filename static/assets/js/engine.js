/* Quoridor rules engine (two players, 9x9 board, 10 walls each).
   Pure logic, no DOM. Works in pages, in a Web Worker and (via module.exports) in tests.
   Keep in step with server/engine.py: the server is authoritative for online games and
   tests/test_parity.py replays games through both implementations.

   Coordinates: rows 0..8 from the top, columns 0..8 from the left.
     player 0 starts at (8,4) and wins on row 0; player 1 starts at (0,4) and wins on row 8.
     wall ("h", r, c) lies below row r across columns c and c+1 (r, c in 0..7)
     wall ("v", r, c) lies right of column c across rows r and r+1 (r, c in 0..7)
   Moves: {type:'move', r, c}  or  {type:'wall', o:'h'|'v', r, c}                              */
(function (root) {
  'use strict';

  var SIZE = 9;
  var WALLS_EACH = 10;
  var GOAL_ROW = [0, 8];
  var DR = [-1, 1, 0, 0];
  var DC = [0, 0, -1, 1];
  var STEP = [-9, 9, -1, 1]; // change in cell index (row * 9 + column) for each direction

  function Game() {
    this.pawns = [[8, 4], [0, 4]];
    this.h = new Uint8Array(64); // h[r*8+c] = 1 when a horizontal wall is anchored at (r,c)
    this.v = new Uint8Array(64);
    this.wallsLeft = [WALLS_EACH, WALLS_EACH];
    this.turn = 0;
    this.winner = null;
    this.moves = [];   // applied moves, in order
    this._undo = [];   // undo records, parallel to moves
    // blk[cell*4 + dir] = 1 when movement from that cell in that direction (0 up, 1 down, 2 left,
    // 3 right) is blocked by a wall or by the edge of the board. Kept in step with h / v so the
    // path searches, which dominate the computer opponent's time, need no geometry or bounds checks.
    this.blk = new Uint8Array(324);
    for (var i = 0; i < 9; i++) {
      this.blk[i * 4] = 1;                 // top row, up
      this.blk[(72 + i) * 4 + 1] = 1;      // bottom row, down
      this.blk[(i * 9) * 4 + 2] = 1;       // left column, left
      this.blk[(i * 9 + 8) * 4 + 3] = 1;   // right column, right
    }
    this._seen = new Int16Array(81);
    this._stamp = 0;
    this._queue = new Int16Array(81);
  }

  Game.prototype.isH = function (r, c) { return r >= 0 && r < 8 && c >= 0 && c < 8 && this.h[r * 8 + c] === 1; };
  Game.prototype.isV = function (r, c) { return r >= 0 && r < 8 && c >= 0 && c < 8 && this.v[r * 8 + c] === 1; };

  // Place (v = 1) or remove (v = 0) a wall, keeping h / v and the blocked-edge table in step.
  // Walls never overlap, so no two walls share an edge and clearing is always safe.
  Game.prototype._setWall = function (o, r, c, v) {
    var b = this.blk, a = r * 9 + c;
    if (o === 'h') {
      this.h[r * 8 + c] = v;
      b[a * 4 + 1] = v; b[(a + 1) * 4 + 1] = v;        // squares above the wall: down
      b[(a + 9) * 4] = v; b[(a + 10) * 4] = v;         // squares below the wall: up
    } else {
      this.v[r * 8 + c] = v;
      b[a * 4 + 3] = v; b[(a + 9) * 4 + 3] = v;        // squares left of the wall: right
      b[(a + 1) * 4 + 2] = v; b[(a + 10) * 4 + 2] = v; // squares right of the wall: left
    }
  };

  // True if a wall lies between (r,c) and its neighbour (r+dr, c+dc). The neighbour must be on the board.
  Game.prototype.blocked = function (r, c, dr, dc) {
    return this.blk[(r * 9 + c) * 4 + (dr === -1 ? 0 : dr === 1 ? 1 : dc === -1 ? 2 : 3)] === 1;
  };

  // Legal destination squares for a pawn (default: the player to move), jumps included.
  Game.prototype.pawnMoves = function (player) {
    var p = player === undefined ? this.turn : player;
    var me = this.pawns[p], opp = this.pawns[1 - p];
    var out = [];
    for (var d = 0; d < 4; d++) {
      var dr = DR[d], dc = DC[d];
      var nr = me[0] + dr, nc = me[1] + dc;
      if (nr < 0 || nr > 8 || nc < 0 || nc > 8 || this.blocked(me[0], me[1], dr, dc)) continue;
      if (nr !== opp[0] || nc !== opp[1]) { out.push([nr, nc]); continue; }
      var jr = nr + dr, jc = nc + dc;
      if (jr >= 0 && jr <= 8 && jc >= 0 && jc <= 8 && !this.blocked(nr, nc, dr, dc)) { out.push([jr, jc]); continue; }
      // Straight jump blocked by a wall or the edge: step beside the opponent instead.
      for (var e = 0; e < 4; e++) {
        var sr = DR[e], sc = DC[e];
        if ((sr === dr && sc === dc) || (sr === -dr && sc === -dc)) continue;
        var tr = nr + sr, tc = nc + sc;
        if (tr >= 0 && tr <= 8 && tc >= 0 && tc <= 8 && !this.blocked(nr, nc, sr, sc)) out.push([tr, tc]);
      }
    }
    return out;
  };

  // Breadth-first search over walls only (pawns are ignored, as the rules specify for the
  // "keep a path open" check). Returns the number of steps to the goal row, or -1 if none.
  // When `path` is an array it receives the cells of one shortest route, start to goal.
  Game.prototype.distance = function (player, path) {
    var start = this.pawns[player], goal = GOAL_ROW[player];
    if (start[0] === goal) { if (path) { path.length = 0; path.push([start[0], start[1]]); } return 0; }
    var seen = this._seen, queue = this._queue, blk = this.blk;
    var stamp = ++this._stamp;
    if (stamp > 30000) { seen.fill(0); this._stamp = stamp = 1; }
    var parent = path ? new Int16Array(81) : null;
    var head = 0, tail = 0, s = start[0] * 9 + start[1];
    queue[tail++] = s; seen[s] = stamp;
    var steps = 0, levelEnd = tail;
    while (head < tail) {
      if (head === levelEnd) { steps++; levelEnd = tail; }
      var cur = queue[head++], base = cur * 4;
      for (var d = 0; d < 4; d++) {
        if (blk[base + d] === 1) continue;
        var n = cur + STEP[d];
        if (seen[n] === stamp) continue;
        seen[n] = stamp;
        if (parent) parent[n] = cur;
        if (((n / 9) | 0) === goal) {
          if (path) {
            path.length = 0;
            for (var k = n; k !== s; k = parent[k]) path.push([(k / 9) | 0, k % 9]);
            path.push([start[0], start[1]]);
            path.reverse();
          }
          return steps + 1;
        }
        queue[tail++] = n;
      }
    }
    return -1;
  };

  // The cheap part of wall legality (no path search): null, or 'out-of-bounds' | 'no-walls' |
  // 'overlap' | 'cross'.
  Game.prototype.wallGeometryError = function (o, r, c, player) {
    var p = player === undefined ? this.turn : player;
    if ((o !== 'h' && o !== 'v') || !(r >= 0 && r <= 7 && c >= 0 && c <= 7) || r % 1 !== 0 || c % 1 !== 0) return 'out-of-bounds';
    if (this.wallsLeft[p] <= 0) return 'no-walls';
    var same = o === 'h' ? this.h : this.v, other = o === 'h' ? this.v : this.h;
    var i = r * 8 + c;
    if (same[i] === 1) return 'overlap';
    if (o === 'h' ? (c > 0 && same[i - 1] === 1) || (c < 7 && same[i + 1] === 1)
                  : (r > 0 && same[i - 8] === 1) || (r < 7 && same[i + 8] === 1)) return 'overlap';
    if (other[i] === 1) return 'cross';
    return null;
  };

  // null if the given player (default: the one to move) may place this wall now, else a reason:
  // 'out-of-bounds' | 'no-walls' | 'overlap' | 'cross' | 'blocks-path'
  Game.prototype.wallError = function (o, r, c, player) {
    var err = this.wallGeometryError(o, r, c, player);
    if (err) return err;
    this._setWall(o, r, c, 1);
    var ok = this.distance(0) >= 0 && this.distance(1) >= 0;
    this._setWall(o, r, c, 0);
    return ok ? null : 'blocks-path';
  };

  Game.prototype.canMove = function (r, c) {
    var m = this.pawnMoves();
    for (var i = 0; i < m.length; i++) if (m[i][0] === r && m[i][1] === c) return true;
    return false;
  };

  // Apply a move for the player to move. Returns null on success, else a reason code.
  Game.prototype.apply = function (move) {
    if (this.winner !== null) return 'game-over';
    if (!move || typeof move !== 'object') return 'bad-move';
    var p = this.turn, rec;
    if (move.type === 'move') {
      var r = move.r, c = move.c;
      if (!isInt(r) || !isInt(c) || !this.canMove(r, c)) return 'illegal-move';
      rec = { player: p, prev: [this.pawns[p][0], this.pawns[p][1]], winner: this.winner };
      this.pawns[p] = [r, c];
      this.moves.push({ type: 'move', r: r, c: c });
      if (r === GOAL_ROW[p]) this.winner = p;
    } else if (move.type === 'wall') {
      if (!isInt(move.r) || !isInt(move.c)) return 'bad-move';
      var err = this.wallError(move.o, move.r, move.c, p);
      if (err) return err;
      this._setWall(move.o, move.r, move.c, 1);
      this.wallsLeft[p]--;
      rec = { player: p, winner: this.winner };
      this.moves.push({ type: 'wall', o: move.o, r: move.r, c: move.c });
    } else {
      return 'bad-move';
    }
    this._undo.push(rec);
    if (this.winner === null) this.turn = 1 - p;
    return null;
  };

  // Take back the last move. Returns false if there is nothing to undo.
  Game.prototype.undo = function () {
    if (!this._undo.length) return false;
    var rec = this._undo.pop(), move = this.moves.pop();
    var p = rec.player;
    this.turn = p;
    this.winner = rec.winner;
    if (move.type === 'move') {
      this.pawns[p] = rec.prev;
    } else {
      this._setWall(move.o, move.r, move.c, 0);
      this.wallsLeft[p]++;
    }
    return true;
  };

  Game.prototype.resign = function (player) {
    if (this.winner === null) this.winner = 1 - player;
  };

  // Plain-data snapshot (the shape the server sends) and its inverse.
  Game.prototype.toJSON = function () {
    var walls = [], i;
    for (i = 0; i < 64; i++) if (this.h[i]) walls.push(['h', (i / 8) | 0, i % 8]);
    for (i = 0; i < 64; i++) if (this.v[i]) walls.push(['v', (i / 8) | 0, i % 8]);
    return {
      pawns: [this.pawns[0].slice(), this.pawns[1].slice()], walls: walls,
      wallsLeft: this.wallsLeft.slice(), turn: this.turn, winner: this.winner,
      moves: this.moves.map(function (m) { return Object.assign({}, m); })
    };
  };

  // Rebuild a game by replaying its move list, so it can still be undone. `winner` from the
  // snapshot is honoured for results that aren't a move (resignation, disconnect).
  Game.fromJSON = function (data) {
    var g = new Game(), list = (data && data.moves) || [];
    for (var i = 0; i < list.length; i++) if (g.apply(list[i])) throw new Error('Invalid move list at ' + i);
    if (data && data.winner !== undefined && data.winner !== null && g.winner === null) g.winner = data.winner;
    return g;
  };

  Game.prototype.clone = function () { return Game.fromJSON(this.toJSON()); };

  function isInt(x) { return typeof x === 'number' && isFinite(x) && Math.floor(x) === x; }

  // Short human-readable names. Files a..i run left to right, ranks 1..9 bottom to top, so
  // player 0 starts on e1 and player 1 on e9. A wall is named after the square just below
  // and left of the point where it is centred, plus its direction: "d4h", "f6v".
  function squareName(r, c) { return 'abcdefghi'.charAt(c) + (9 - r); }
  function wallName(o, r, c) { return 'abcdefghi'.charAt(c) + (8 - r) + o; }
  function moveName(m) { return m.type === 'move' ? squareName(m.r, m.c) : wallName(m.o, m.r, m.c); }

  var api = { Game: Game, SIZE: SIZE, WALLS_EACH: WALLS_EACH, GOAL_ROW: GOAL_ROW, squareName: squareName, wallName: wallName, moveName: moveName };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Quoridor = api;
})(typeof self !== 'undefined' ? self : this);
