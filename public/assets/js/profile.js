/* What this browser remembers about the player. It all stays in localStorage on this device; none of it is sent anywhere.

     name     the display name used last time, put into the name fields again
     scores   a tally between two named players: how many games each has won against the other

   A tally is kept by name, because names are not accounts: a friend who plays under another name starts a new
   tally. Each browser tallies the games it saw, so two friends see the same score when both played them all.

     QuoridorProfile.name()                      -> '' or the remembered display name
     QuoridorProfile.setName(name)
     QuoridorProfile.tally(a, b)                 -> [wins of a, wins of b], or null when they have not played yet
     QuoridorProfile.record(a, b, winner, id)    -> the new tally. winner is 0 (a) or 1 (b); id names the game, so
                                                    a game shown again (a reload) is not counted twice.          */
(function (root) {
  'use strict';

  var NAME_KEY = 'quoridor.username';
  var SCORES_KEY = 'quoridor.scores';
  var MAX_PAIRS = 50;   // tallies kept; the ones played longest ago go first
  var MAX_SEEN = 40;    // finished games remembered, so showing a result again never counts it twice
  var memory = null;    // the tally while storage refuses to save it, so it still works until the page is closed

  // ---- display name ---------------------------------------------------------------------
  function name() {
    try {
      var v = root.localStorage.getItem(NAME_KEY);
      return typeof v === 'string' ? v.trim().slice(0, 20) : '';
    } catch (e) { return ''; }
  }
  function setName(value) { try { root.localStorage.setItem(NAME_KEY, value); } catch (e) { /* storage blocked */ } }

  // ---- scores ---------------------------------------------------------------------------
  function valid(p) {
    return !!p && typeof p.id === 'string' && Array.isArray(p.names) && p.names.length === 2 && Array.isArray(p.wins) && p.wins.length === 2;
  }
  function load() {
    if (memory) return memory;
    var data = null;
    try { data = JSON.parse(root.localStorage.getItem(SCORES_KEY)); } catch (e) { /* storage blocked or damaged */ }
    if (!data || !Array.isArray(data.pairs) || !Array.isArray(data.seen)) data = { pairs: [], seen: [] };
    data.pairs = data.pairs.filter(valid);   // an entry edited by hand into nonsense is ignored
    return data;
  }
  function save(data) {
    try { root.localStorage.setItem(SCORES_KEY, JSON.stringify(data)); memory = null; } catch (e) { memory = data; }
  }

  // "Sara" and "sara" are one friend.
  function key(value) { return String(value).normalize('NFC').toLowerCase(); }

  // A tally is {id, names: [x, y], wins: [of x, of y], at}; x and y are in key order, so a pair has one tally whoever is "a".
  function pairId(ka, kb) { return ka < kb ? ka + '\n' + kb : kb + '\n' + ka; }
  function find(data, id) {
    for (var i = 0; i < data.pairs.length; i++) {
      if (data.pairs[i].id === id) return data.pairs[i];
    }
    return null;
  }
  function winsOf(p, ka) {
    var first = key(p.names[0]) === ka;
    var x = Math.max(0, Math.floor(Number(p.wins[first ? 0 : 1])) || 0), y = Math.max(0, Math.floor(Number(p.wins[first ? 1 : 0])) || 0);
    return [x, y];
  }

  function tally(a, b) {
    var ka = key(a), kb = key(b);
    if (!ka || ka === kb) return null;
    var p = find(load(), pairId(ka, kb));
    return p ? winsOf(p, ka) : null;
  }

  function record(a, b, winner, id) {
    var ka = key(a), kb = key(b);
    if ((winner !== 0 && winner !== 1) || !ka || ka === kb) return null;
    var data = load();
    if (data.seen.indexOf(id) === -1) {
      var pid = pairId(ka, kb), p = find(data, pid);
      if (!p) {
        p = { id: pid, names: ka < kb ? [a, b] : [b, a], wins: [0, 0], at: 0 };
        data.pairs.push(p);
      }
      var aSlot = key(p.names[0]) === ka ? 0 : 1;
      var counts = winsOf(p, ka);
      counts[winner] += 1;
      p.wins = aSlot === 0 ? counts : [counts[1], counts[0]];
      p.names[aSlot] = a; p.names[1 - aSlot] = b;   // the way they spelled their names last
      p.at = Date.now();
      data.seen.push(id);
      if (data.seen.length > MAX_SEEN) data.seen = data.seen.slice(-MAX_SEEN);
      while (data.pairs.length > MAX_PAIRS) {   // drop the tally played longest ago, never the one just updated
        var oldest = null;
        data.pairs.forEach(function (q) { if (q !== p && (!oldest || (q.at || 0) < (oldest.at || 0))) oldest = q; });
        data.pairs.splice(data.pairs.indexOf(oldest), 1);
      }
      save(data);
    }
    return tally(a, b);
  }

  root.QuoridorProfile = { name: name, setName: setName, tally: tally, record: record };
})(typeof self !== 'undefined' ? self : this);
