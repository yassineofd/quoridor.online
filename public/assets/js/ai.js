/* Computer opponent for Quoridor: four levels built on the rules engine in engine.js.

   Every level uses the same evaluation (how many steps each pawn still needs, plus a small value
   for spare walls) and differs only in how it searches and how much noise it adds:
     easy    looks at its own move only, picks with heavy randomness, rarely uses walls
     medium  looks at its own move only, small randomness
     hard    looks two plies ahead (its move and your reply)
     expert  iterative deepening alpha-beta, as deep as the time budget allows (up to 6 plies)
   Candidate walls are limited to ones that lengthen the opponent's current shortest route, which
   keeps the search small enough to run in a browser.                                          */
(function (root) {
  'use strict';
  var Q = root.Quoridor || (typeof require === 'function' ? require('./engine.js') : null);

  var WIN = 100000;
  var REPEAT = 20; // score penalty for stepping back onto a recently visited square
  var TIE = 0.5; // scores this close are treated as equal when choosing the root move
  var LEVELS = {
    easy:   { depth: 1, noise: 14, wallChance: 0.2, timeMs: 0 },
    medium: { depth: 1, noise: 3, wallChance: 1, timeMs: 0 },
    hard:   { depth: 2, noise: 0.4, wallChance: 1, timeMs: 0 },
    expert: { depth: 12, noise: 0, wallChance: 1, timeMs: 1000, maxNodes: 60000, innerWalls: 10 }
  };

  // Score from the point of view of the player to move.
  function evaluate(g) {
    var t = g.turn, dm = g.distance(t), dop = g.distance(1 - t);
    return (dop - dm) * 10 + (g.wallsLeft[t] - g.wallsLeft[1 - t]) * 2 + 1;
  }

  // Walls that would lengthen the opponent's shortest route, strongest first.
  function wallCandidates(g, p, limit) {
    if (g.wallsLeft[p] <= 0) return [];
    var opp = 1 - p, path = [], base = g.distance(opp, path), seen = {}, out = [];
    function consider(o, r, c) {
      if (r < 0 || r > 7 || c < 0 || c > 7) return;
      var key = o + r + c;
      if (seen[key]) return;
      seen[key] = 1;
      if (g.wallGeometryError(o, r, c, p) !== null) return;
      // Place it, and only look further when it lengthens the opponent's route (which also proves
      // the opponent still has one); then confirm the mover is not shut in.
      g._setWall(o, r, c, 1);
      var d = g.distance(opp), legal = d > base && g.distance(p) >= 0;
      g._setWall(o, r, c, 0);
      if (legal) out.push({ move: { type: 'wall', o: o, r: r, c: c }, gain: d - base });
    }
    for (var i = 0; i + 1 < path.length; i++) {
      var a = path[i], b = path[i + 1];
      if (a[0] !== b[0]) {
        var rr = Math.min(a[0], b[0]);
        consider('h', rr, a[1]); consider('h', rr, a[1] - 1);
      } else {
        var cc = Math.min(a[1], b[1]);
        consider('v', a[0], cc); consider('v', a[0] - 1, cc);
      }
    }
    out.sort(function (x, y) { return y.gain - x.gain; });
    return limit ? out.slice(0, limit) : out;
  }

  // All moves worth considering for the player to move, best-looking first.
  function generate(g, wallChance, rng, wallLimit) {
    var p = g.turn, moves = [], i;
    var pm = g.pawnMoves(), path = [];
    g.distance(p, path);
    var next = path.length > 1 ? path[1] : null;
    for (i = 0; i < pm.length; i++) {
      var forward = next && pm[i][0] === next[0] && pm[i][1] === next[1];
      // Jumps can skip the path's next square, so also favour moves that end nearer the goal row.
      var progress = Math.abs(pm[i][0] - Q.GOAL_ROW[p]);
      moves.push({ move: { type: 'move', r: pm[i][0], c: pm[i][1] }, key: (forward ? 100 : 0) - progress });
    }
    var walls = wallCandidates(g, p, wallLimit);
    for (i = 0; i < walls.length; i++) {
      if (wallChance < 1 && rng() > wallChance) continue;
      moves.push({ move: walls[i].move, key: 40 + walls[i].gain * 10 });
    }
    moves.sort(function (a, b) { return b.key - a.key; });
    return moves;
  }

  // Squares this player has recently stood on (before the current one), most recent last.
  function recentSquares(g, player, count) {
    var replay = new Q.Game(), seen = [];
    for (var i = 0; i < g.moves.length; i++) {
      var mover = replay.turn;
      replay.apply(g.moves[i]);
      if (mover === player && g.moves[i].type === 'move') seen.push(g.moves[i].r + ',' + g.moves[i].c);
    }
    seen.pop(); // the current square
    return seen.slice(-count);
  }

  function Timeout() {}

  function negamax(g, depth, alpha, beta, ctx) {  // ctx.innerWalls: how many candidate walls to try at interior nodes
    // The game only ends when the player who just moved wins, so whoever is "to move" has lost.
    if (g.winner !== null) return -WIN - depth;
    if (depth === 0) return evaluate(g);
    if (++ctx.nodes > ctx.maxNodes || ((ctx.nodes & 63) === 0 && ctx.deadline && Date.now() > ctx.deadline)) throw new Timeout();
    var moves = generate(g, 1, null, ctx.innerWalls), best = -Infinity;
    for (var i = 0; i < moves.length; i++) {
      g.apply(moves[i].move);
      var s = -negamax(g, depth - 1, -beta, -alpha, ctx);
      g.undo();
      if (s > best) best = s;
      if (best > alpha) alpha = best;
      if (alpha >= beta) break;
    }
    return best;
  }

  // Pick a move for the player to move. g is restored before returning.
  // opts: level ('easy'|'medium'|'hard'|'expert'), rng (default Math.random), timeMs, maxNodes.
  function chooseMove(g, opts) {
    opts = opts || {};
    var cfg = LEVELS[opts.level] || LEVELS.medium;
    var rng = opts.rng || Math.random;
    var roots = generate(g, cfg.wallChance, rng, 14);
    if (!roots.length) return null;
    // An immediate win always gets played, whatever the level.
    for (var w = 0; w < roots.length; w++) {
      var m0 = roots[w].move;
      if (m0.type === 'move' && m0.r === Q.GOAL_ROW[g.turn]) return m0;
    }
    var iterative = cfg.timeMs > 0; // only the strongest level is budgeted by time / node count
    var timeMs = iterative && opts.timeMs !== undefined ? opts.timeMs : cfg.timeMs;
    var maxNodes = iterative && opts.maxNodes !== undefined ? opts.maxNodes : (cfg.maxNodes || Infinity);
    var best = roots[0].move;

    if (!iterative) {
      var ctx0 = { nodes: 0, maxNodes: Infinity, deadline: 0, innerWalls: 10 }, bestScore = -Infinity;
      for (var i = 0; i < roots.length; i++) {
        g.apply(roots[i].move);
        var s = -negamax(g, cfg.depth - 1, -Infinity, Infinity, ctx0) + (rng() - 0.5) * 2 * cfg.noise;
        g.undo();
        if (s > bestScore) { bestScore = s; best = roots[i].move; }
      }
      return best;
    }

    // Iterative deepening with a time / node budget; keep the last fully searched depth's choice.
    var ctx = { nodes: 0, maxNodes: maxNodes, deadline: timeMs ? Date.now() + timeMs : 0, innerWalls: cfg.innerWalls || 10 };
    var baseLen = g.moves.length, bestEven = null, recent = null;
    try {
      for (var depth = 1; depth <= cfg.depth; depth++) {
        // Search every root move with a window just below the best score so far, so moves that tie
        // with the best are scored exactly. When deep search sees nothing to choose between (it
        // assumes the opponent answers every step with a perfect wall), prefer the tied move that
        // leaves our own route shortest; otherwise the first-listed move wins and the pawn can
        // shuffle back and forth.
        var me = g.turn, alpha = -Infinity, cand = [], iterBest = null;
        if (!recent) recent = recentSquares(g, me, 4);
        for (var j = 0; j < roots.length; j++) {
          g.apply(roots[j].move);
          var sc = -negamax(g, depth - 1, -Infinity, -(alpha - TIE), ctx);
          // Stepping back onto a square we just left is almost never progress; deep search can
          // prefer it only because it assumes the opponent walls perfectly, and the pawn then
          // shuffles. Make that retreat earn its place.
          if (roots[j].move.type === 'move' && recent.indexOf(roots[j].move.r + ',' + roots[j].move.c) !== -1) sc -= REPEAT;
          var own = g.distance(me);
          g.undo();
          if (opts.scores) opts.scores.push({ depth: depth, move: Q.moveName(roots[j].move), score: sc, own: own });
          if (sc > alpha + TIE) { cand = []; }
          if (sc >= alpha - TIE) { cand.push({ root: roots[j], own: own }); if (sc > alpha) alpha = sc; }
        }
        iterBest = cand[0];
        for (var c = 1; c < cand.length; c++) if (cand[c].own < iterBest.own) iterBest = cand[c];
        iterBest = iterBest.root;
        best = iterBest.move;
        // Odd depths end on our own move, which makes the leaf scores optimistic (the opponent
        // never gets to answer a final wall), so trust the last finished *even* depth.
        if (depth % 2 === 0) bestEven = iterBest.move;
        if (opts.stats) opts.stats.depth = depth;
        // Search the previous best first next time.
        roots.splice(roots.indexOf(iterBest), 1);
        roots.unshift(iterBest);
        if (alpha > WIN / 2) break; // forced win found
      }
    } catch (e) {
      if (!(e instanceof Timeout)) throw e;
      while (g.moves.length > baseLen) g.undo(); // unwind whatever the aborted search had applied
    }
    if (opts.stats) opts.stats.nodes = ctx.nodes;
    return bestEven || best;
  }

  var api = { chooseMove: chooseMove, LEVELS: LEVELS, evaluate: evaluate };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.QuoridorAI = api;
})(typeof self !== 'undefined' ? self : this);
