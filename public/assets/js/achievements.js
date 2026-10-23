/* Achievements, score and rank. It all stays in localStorage on this device (the entry named quoridor.progress); none of it is sent anywhere,
   and there is no account behind it: clearing the site data starts the score over.

   Every finished game is worth points, and so is every achievement it unlocks. The score decides the rank. The score is not
   stored: the points of the games are, and the points of the achievements are added up from the ones unlocked, so changing the
   points of an achievement in CATALOG changes the score of everybody at once.

     QuoridorAchievements.recordGame(info [, now])
        info  { mode: 'local' | 'computer' | 'online', variant, players, options, level, seat, winner, reason, moves }
              the same things game.js knows when a game ends (seat is null when no one player is "you", as on one device)
        now   the time of the game in milliseconds (tests); Date.now() when left out
        -> null when the game is too short to count, else what it earned:
           { won, gained, bonus, total, unlocked: [{id, points}], score, rank, rankedUp, next, streak, saved }
     QuoridorAchievements.summary([now]) -> the score, rank, streak, statistics and every achievement with its progress
     QuoridorAchievements.reset()
     QuoridorAchievements.catalog() / ranks() / storageWorks() / configure({storage})

   Texts are messages (translations/js-en.json): ach.<id>.name and ach.<id>.desc for each achievement, ach.rank.<n> for each rank.
   To add an achievement: add it to CATALOG, add its two messages, translate them (python i18n.py missing es), and see docs/achievements.md. */
(function (root) {
  'use strict';

  var KEY = 'quoridor.progress';
  var MIN_MOVES = 6;   // a game that ends sooner (a resignation after a move or two) is not worth anything
  var LEVELS = ['easy', 'medium', 'hard', 'expert'];
  var VARIANT_NAMES = ['wallrush', 'pointrush', 'custom'];

  // The score a player needs for each rank (messages ach.rank.0, ach.rank.1 ...).
  var RANKS = [0, 75, 200, 400, 700, 1100, 1700];

  // Points for a finished game itself, before any achievement: for taking part, for a win, and for beating a stronger opponent.
  var PLAYED_POINTS = 5;
  var WIN_POINTS = 10;
  var BEAT_POINTS = { easy: 0, medium: 5, hard: 15, expert: 30, online: 20 };

  // ---- the achievements ------------------------------------------------------------------
  // A counter has value(stats, data) and target: it is done when the value reaches the target, and shows a progress bar on the way.
  // An event has test(stats, game): it is done by one game (game = what analyze() found out about it), so it has no progress.
  // cat groups them on the page (messages ach.cat.<cat>); icon is a name from icons.js.
  function counter(id, icon, points, cat, target, value) { return { id: id, icon: icon, points: points, cat: cat, target: target, value: value }; }
  function event(id, icon, points, cat, test) { return { id: id, icon: icon, points: points, cat: cat, test: test }; }
  function beat(level) { return function (s) { return s.beat[level]; }; }
  function stat(name) { return function (s) { return s[name]; }; }
  function variantsPlayed(s) { return VARIANT_NAMES.filter(function (v) { return s.variants[v] > 0; }).length; }
  function unlockedCount(s, data) { return Object.keys(data.unlocked).filter(known).length; }

  var CATALOG = [
    counter('firstGame', 'play', 10, 'start', 1, stat('games')),
    counter('firstWall', 'wall', 10, 'start', 1, stat('walls')),
    counter('firstWin', 'trophy', 25, 'start', 1, stat('wins')),
    counter('learn', 'flag', 10, 'start', 1, stat('losses')),

    counter('beatEasy', 'bot', 15, 'robots', 1, beat('easy')),
    counter('beatMedium', 'bot', 30, 'robots', 1, beat('medium')),
    counter('beatHard', 'bot', 60, 'robots', 1, beat('hard')),
    counter('beatExpert', 'crown', 150, 'robots', 1, beat('expert')),

    // These need a game won by walking to the goal (not by the other side giving up), so the numbers mean something.
    event('speed', 'clock', 40, 'skill', function (s, g) { return g.byGoal && g.won && g.turns <= 12; }),
    event('noWalls', 'move', 50, 'skill', function (s, g) { return g.byGoal && g.won && g.walls === 0 && g.level !== 'easy'; }),
    event('allWalls', 'shield', 40, 'skill', function (s, g) { return g.byGoal && g.won && g.wallsLeft === 0; }),
    event('jump', 'zap', 15, 'skill', function (s, g) { return g.jumped; }),
    event('detour', 'target', 30, 'skill', function (s, g) { return g.detour >= 4; }),
    event('comeback', 'award', 60, 'skill', function (s, g) { return g.byGoal && g.won && g.behind >= 5; }),

    counter('games10', 'medal', 20, 'milestones', 10, stat('games')),
    counter('games50', 'medal', 60, 'milestones', 50, stat('games')),
    counter('wins5', 'star', 30, 'milestones', 5, stat('wins')),
    counter('wins25', 'star', 75, 'milestones', 25, stat('wins')),
    counter('wins100', 'star', 200, 'milestones', 100, stat('wins')),
    counter('walls100', 'wall', 40, 'milestones', 100, stat('walls')),
    counter('hunter10', 'award', 50, 'milestones', 10, unlockedCount),
    counter('hunter20', 'trophy', 100, 'milestones', 20, unlockedCount),

    counter('winStreak3', 'flame', 40, 'streaks', 3, stat('bestWinStreak')),
    counter('winStreak7', 'flame', 120, 'streaks', 7, stat('bestWinStreak')),
    counter('days3', 'calendar', 30, 'streaks', 3, stat('bestDayStreak')),
    counter('days7', 'calendar', 80, 'streaks', 7, stat('bestDayStreak')),
    counter('days30', 'calendar', 250, 'streaks', 30, stat('bestDayStreak')),

    counter('onlineGame', 'globe', 20, 'together', 1, stat('onlinePlayed')),
    counter('onlineWin', 'globe', 40, 'together', 1, stat('onlineWins')),
    counter('online10', 'globe', 100, 'together', 10, stat('onlineWins')),
    counter('friend', 'users', 10, 'together', 1, stat('friendGames')),
    counter('explorer', 'sliders', 60, 'together', VARIANT_NAMES.length, variantsPlayed)
  ];
  var CATEGORIES = ['start', 'robots', 'skill', 'milestones', 'streaks', 'together'];

  var BY_ID = {};
  CATALOG.forEach(function (a) { BY_ID[a.id] = a; });
  function known(id) { return Object.prototype.hasOwnProperty.call(BY_ID, id); }

  // ---- storage ---------------------------------------------------------------------------
  var store = null;    // set by configure() (tests); otherwise window.localStorage
  var memory = null;   // the progress while storage refuses to save it, so it still works until the page is closed

  function storage() {
    if (store) return store;
    try { return root.localStorage; } catch (e) { return null; }
  }
  function num(v) { v = Math.floor(Number(v)); return isFinite(v) && v > 0 ? Math.min(v, 1e9) : 0; }
  function counts(source, names) {
    var out = {};
    names.forEach(function (n) { out[n] = num(source && source[n]); });
    return out;
  }

  // Whatever is in storage, made into a progress record that is safe to use (it may be old, damaged or edited by hand).
  function sanitize(d) {
    d = d && typeof d === 'object' ? d : {};
    var s = d.stats && typeof d.stats === 'object' ? d.stats : {};
    var out = {
      v: 1, xp: num(d.xp), unlocked: {},
      stats: {
        games: num(s.games), wins: num(s.wins), losses: num(s.losses), walls: num(s.walls),
        winStreak: num(s.winStreak), bestWinStreak: num(s.bestWinStreak),
        dayStreak: num(s.dayStreak), bestDayStreak: num(s.bestDayStreak), lastDay: num(s.lastDay),
        onlinePlayed: num(s.onlinePlayed), onlineWins: num(s.onlineWins), friendGames: num(s.friendGames),
        beat: counts(s.beat, LEVELS), variants: counts(s.variants, VARIANT_NAMES)
      }
    };
    var u = d.unlocked && typeof d.unlocked === 'object' ? d.unlocked : {};
    Object.keys(u).forEach(function (id) { if (known(id)) out.unlocked[id] = num(u[id]) || 1; });
    return out;
  }

  function load() {
    if (memory) return memory;
    var data = null;
    try { var raw = storage().getItem(KEY); data = raw ? JSON.parse(raw) : null; } catch (e) { /* storage blocked or damaged */ }
    return sanitize(data);
  }
  // True when the progress reached storage; false when it is only kept until the page closes.
  function save(data) {
    try { storage().setItem(KEY, JSON.stringify(data)); memory = null; return true; } catch (e) { memory = data; return false; }
  }

  // ---- days -------------------------------------------------------------------------------
  // A day number counts local calendar days, so a streak follows the player's own midnight whatever the time zone or clock change.
  function dayNumber(ms) {
    var d = new Date(ms);
    return Math.round(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 86400000);
  }
  // The days-in-a-row now: still alive when the last game was today or yesterday.
  function liveStreak(s, now) {
    var today = dayNumber(now);
    return s.lastDay && (s.lastDay === today || s.lastDay === today - 1) ? s.dayStreak : 0;
  }

  // ---- what a finished game shows ------------------------------------------------------------
  // Replays the moves for the player's seat to find what no counter keeps: jumps, the biggest detour a wall caused, the most
  // steps the player was behind in the race. Two players on a board of the engine's only (computer and online games); needs engine.js.
  function analyze(info) {
    var moves = info.moves || [], n = info.players || 2, me = info.seat;
    var out = { turns: 0, walls: 0, jumped: false, detour: 0, behind: 0 };
    var i;
    for (i = 0; i < moves.length; i++) {
      if (me === null || i % n === me) {
        out.turns++;
        if (moves[i].type === 'wall') out.walls++;
      }
    }
    if (me === null || n !== 2 || !root.Quoridor) return out;
    var g, opp = 1 - me;
    try { g = new root.Quoridor.Game(info.variant, 2, info.options); } catch (e) { return out; }
    for (i = 0; i < moves.length; i++) {
      var m = moves[i], p = i % 2, from = g.pawns[p].slice(), oppBefore = g.distance(opp);
      if (g.apply(m)) break;   // not a game this engine plays: keep what has been found so far
      if (p === me && m.type === 'move' && Math.abs(m.r - from[0]) + Math.abs(m.c - from[1]) > 1) out.jumped = true;
      if (p === me && m.type === 'wall') out.detour = Math.max(out.detour, g.distance(opp) - oppBefore);
      out.behind = Math.max(out.behind, g.distance(me) - g.distance(opp));
    }
    out.wallsLeft = g.wallsLeft[me];
    return out;
  }

  // Everything the achievements may ask about one finished game.
  function gameFacts(info) {
    var moves = info.moves || [], last = moves[moves.length - 1];
    var seat = info.seat === undefined ? null : info.seat;
    var facts = analyze({ moves: moves, players: info.players, variant: info.variant, options: info.options, seat: seat });
    facts.mode = info.mode;
    facts.variant = info.variant || 'classic';
    facts.level = info.mode === 'computer' ? info.level || 'medium' : null;
    facts.won = seat === null || info.winner === null || info.winner === undefined ? null : info.winner === seat;
    facts.byGoal = !info.reason && !!last && last.type === 'move';   // won by reaching the goal, not by the other side giving up or running out of time
    if (facts.wallsLeft === undefined) facts.wallsLeft = -1;
    return facts;
  }

  function gamePoints(g) {
    var points = PLAYED_POINTS;
    if (g.won === true) {
      points += WIN_POINTS + (g.mode === 'online' ? BEAT_POINTS.online : BEAT_POINTS[g.level] || 0);
    }
    return points;
  }

  // ---- reading the progress ------------------------------------------------------------------
  function scoreOf(data) {
    var score = data.xp;
    CATALOG.forEach(function (a) { if (data.unlocked[a.id]) score += a.points; });
    return score;
  }
  function rankOf(score) {
    var rank = 0;
    RANKS.forEach(function (at, i) { if (score >= at) rank = i; });
    return rank;
  }
  function nextRank(score, rank) {
    if (rank + 1 >= RANKS.length) return null;
    var from = RANKS[rank], at = RANKS[rank + 1];
    return { rank: rank + 1, at: at, remaining: at - score, fraction: (score - from) / (at - from) };
  }

  function summarize(data, now) {
    var s = data.stats, score = scoreOf(data), rank = rankOf(score);
    var items = CATALOG.map(function (a) {
      var progress = null;
      if (a.value) progress = [Math.min(a.value(s, data), a.target), a.target];
      return { id: a.id, icon: a.icon, points: a.points, cat: a.cat, unlockedAt: data.unlocked[a.id] || null, progress: progress };
    });
    // The goal to suggest: the locked counter that is the furthest along (the cheaper one when they tie).
    var goal = null;
    items.forEach(function (it) {
      if (it.unlockedAt || !it.progress) return;
      var f = it.progress[0] / it.progress[1];
      if (!goal || f > goal.f || (f === goal.f && it.points < goal.item.points)) goal = { f: f, item: it };
    });
    var live = liveStreak(s, now);
    return {
      score: score, rank: rank, next: nextRank(score, rank),
      unlocked: items.filter(function (it) { return it.unlockedAt; }).length, total: items.length,
      items: items, goal: goal && goal.item,
      streak: { days: live, best: s.bestDayStreak, playedToday: s.lastDay === dayNumber(now) },
      stats: { games: s.games, wins: s.wins, losses: s.losses, walls: s.walls, bestWinStreak: s.bestWinStreak, onlineWins: s.onlineWins }
    };
  }

  // ---- recording a game ------------------------------------------------------------------------
  function recordGame(info, now) {
    if (!info || !info.moves || info.moves.length < MIN_MOVES) return null;
    now = now === undefined ? Date.now() : now;
    var data = load(), s = data.stats, before = summarize(data, now);
    var g = gameFacts(info);

    s.games++;
    s.walls += g.walls;
    var day = dayNumber(now);
    if (day > s.lastDay) {
      s.dayStreak = s.lastDay === day - 1 ? s.dayStreak + 1 : 1;
      s.bestDayStreak = Math.max(s.bestDayStreak, s.dayStreak);
      s.lastDay = day;
    }
    if (g.won === true) {
      s.wins++;
      s.winStreak++;
      s.bestWinStreak = Math.max(s.bestWinStreak, s.winStreak);
      if (g.level && s.beat[g.level] !== undefined) s.beat[g.level]++;
    } else if (g.won === false) {
      s.losses++;
      s.winStreak = 0;
    }
    if (g.mode === 'online') {
      s.onlinePlayed++;
      if (g.won === true) s.onlineWins++;
    }
    if (g.mode === 'local') s.friendGames++;
    if (s.variants[g.variant] !== undefined) s.variants[g.variant]++;

    var gained = gamePoints(g);
    data.xp += gained;

    // An achievement can count the others (the trophy hunters), so go round until nothing new unlocks.
    var unlocked = [], again = true;
    while (again) {
      again = false;
      CATALOG.forEach(function (a) {
        if (data.unlocked[a.id]) return;
        var done = a.value ? a.value(s, data) >= a.target : !!a.test(s, g);
        if (done) { data.unlocked[a.id] = now; unlocked.push({ id: a.id, points: a.points }); again = true; }
      });
    }
    var saved = save(data);

    var after = summarize(data, now);
    var bonus = unlocked.reduce(function (sum, u) { return sum + u.points; }, 0);
    return {
      won: g.won, gained: gained, bonus: bonus, total: gained + bonus, unlocked: unlocked,
      score: after.score, rank: after.rank, rankedUp: after.rank > before.rank, next: after.next, streak: after.streak, saved: saved
    };
  }

  root.QuoridorAchievements = {
    recordGame: recordGame,
    summary: function (now) { return summarize(load(), now === undefined ? Date.now() : now); },
    reset: function () {
      memory = null;
      try { storage().removeItem(KEY); } catch (e) { /* storage blocked: nothing was saved */ }
    },
    // False when the browser will not keep the progress (storage blocked); the page then says so.
    storageWorks: function () {
      try {
        var st = storage(), probe = KEY + '.probe';
        st.setItem(probe, '1'); st.removeItem(probe);
        return true;
      } catch (e) { return false; }
    },
    catalog: function () { return CATALOG.slice(); },
    categories: function () { return CATEGORIES.slice(); },
    ranks: function () { return RANKS.slice(); },
    analyze: analyze,
    configure: function (o) { store = o && o.storage || null; memory = null; },
    MIN_MOVES: MIN_MOVES
  };
})(typeof self !== 'undefined' ? self : this);
