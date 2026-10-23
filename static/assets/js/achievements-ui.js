/* Draws the score, rank and achievements kept by achievements.js.

     QuoridorAchievementsUI.reward(result)    the block for the end of a game (game.js puts it in the result panel); null when there is nothing to show
     QuoridorAchievementsUI.sentence(result)  the same in one sentence, for the screen-reader announcement

   and by itself, on a page that has
     [data-progress-teaser]   the short summary under a play form: rank, score and the next goal
     [data-achievements]      the whole Achievements page: rank, statistics and every achievement with its progress

   Texts are messages (translations/js-en.json, "ach.*"), so they follow the language chosen with the translate button.        */
(function (root) {
  'use strict';

  var A = root.QuoridorAchievements, I18n = root.QuoridorI18n, doc = root.document;
  if (!A) return;

  function t(key, params) { return I18n ? I18n.t(key, params) : key; }

  function h(tag, attrs, kids) {
    var n = doc.createElement(tag);
    for (var k in attrs || {}) {
      if (k === 'text') n.textContent = attrs[k];
      else if (k === 'class') n.className = attrs[k];
      else n.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) { if (c) n.appendChild(typeof c === 'string' ? doc.createTextNode(c) : c); });
    return n;
  }

  // A round badge with one of the Lucide icons (icons.js).
  function badge(name) {
    var b = h('span', { 'class': 'ach-icon', 'aria-hidden': 'true' });
    if (root.QuoridorIcons) b.innerHTML = root.QuoridorIcons.svg(name);
    return b;
  }

  // A bar for a fraction between 0 and 1. It only decorates: the figures next to it say the same in words.
  function meter(fraction) {
    var fill = h('span', { 'class': 'meter-fill' });
    fill.style.width = Math.round(Math.max(0, Math.min(1, fraction)) * 100) + '%';
    return h('span', { 'class': 'meter', 'aria-hidden': 'true' }, [fill]);
  }

  function pagePath(name) { return (I18n && I18n.root || '/') + name; }

  function byId(id) {
    var all = A.catalog();
    for (var i = 0; i < all.length; i++) if (all[i].id === id) return all[i];
    return null;
  }
  function nameOf(id) { return t('ach.' + id + '.name'); }

  function dateText(ms) {
    if (!(ms > 1e11)) return '';   // an entry without a real time
    try { return new Date(ms).toLocaleDateString(I18n ? I18n.language() : undefined, { year: 'numeric', month: 'short', day: 'numeric' }); } catch (e) { return ''; }
  }

  // ---- end of a game ---------------------------------------------------------------------------
  function streakNote(streak) {
    if (streak.days >= 2) return t('ach.streakKeep', { n: streak.days });
    return t('ach.streakStart');
  }

  function reward(res) {
    if (!res) return null;
    var rank = t('ach.rank.' + res.rank);
    var box = h('div', { 'class': 'reward-inner' });
    box.appendChild(h('p', { 'class': 'reward-points' }, [
      h('span', { 'class': 'reward-gain', text: t('ach.gain', { n: res.total }) }),
      h('span', { 'class': 'reward-total', text: t('ach.score', { n: res.score }) + ' · ' + rank })
    ]));
    if (res.rankedUp) box.appendChild(h('p', { 'class': 'reward-rankup' }, [badge('crown'), h('span', { text: t('ach.rankUp', { name: rank }) })]));

    if (res.unlocked.length) {
      box.appendChild(h('h3', { 'class': 'reward-title', text: t('ach.newTitle') }));
      var list = h('ul', { 'class': 'reward-list' });
      res.unlocked.forEach(function (u) {
        var a = byId(u.id);
        if (!a) return;
        list.appendChild(h('li', {}, [
          badge(a.icon),
          h('span', { 'class': 'reward-item' }, [h('strong', { text: nameOf(a.id) }), h('span', { 'class': 'small text-muted', text: t('ach.' + a.id + '.desc') })]),
          h('span', { 'class': 'ach-pts', text: t('ach.gain', { n: a.points }) })
        ]));
      });
      box.appendChild(list);
    }

    if (res.next) {
      box.appendChild(h('p', { 'class': 'reward-next small text-muted', text: t('ach.nextRank', { name: t('ach.rank.' + res.next.rank), n: res.next.remaining }) }));
      box.appendChild(meter(res.next.fraction));
    } else {
      box.appendChild(h('p', { 'class': 'reward-next small text-muted', text: t('ach.topRank') }));
    }
    box.appendChild(h('p', { 'class': 'small text-muted', text: streakNote(res.streak) }));
    if (!res.saved) box.appendChild(h('p', { 'class': 'small text-muted', text: t('ach.notSaved') }));
    box.appendChild(h('a', { 'class': 'reward-link', href: pagePath('achievements'), text: t('ach.viewAll') }));
    return box;
  }

  function sentence(res) {
    if (!res) return '';
    var out = t('ach.gain', { n: res.total }) + '.';
    if (res.rankedUp) out += ' ' + t('ach.rankUp', { name: t('ach.rank.' + res.rank) });
    if (res.unlocked.length) out += ' ' + t('ach.newTitle') + ': ' + res.unlocked.map(function (u) { return nameOf(u.id); }).join(', ') + '.';
    return out;
  }

  // ---- under a play form ---------------------------------------------------------------------------
  function drawTeaser(host) {
    var sum = A.summary();
    host.textContent = '';
    host.appendChild(h('p', { 'class': 'teaser-head' }, [
      badge('trophy'),
      h('span', {}, [h('strong', { text: t('ach.rank.' + sum.rank) }), ' · ' + t('ach.score', { n: sum.score })])
    ]));
    if (sum.goal) {
      var g = sum.goal;
      host.appendChild(h('p', { 'class': 'teaser-goal small' }, [
        h('span', { text: t('ach.nextGoal', { name: nameOf(g.id) }) }),
        h('span', { 'class': 'teaser-count', text: g.progress[0] + ' / ' + g.progress[1] })
      ]));
      host.appendChild(meter(g.progress[0] / g.progress[1]));
    }
    if (sum.streak.days > 0 && !sum.streak.playedToday) host.appendChild(h('p', { 'class': 'small text-muted', text: t('ach.streakToday', { n: sum.streak.days }) }));
    host.appendChild(h('a', { 'class': 'teaser-link small', href: pagePath('achievements'), text: t('ach.viewAll') }));
    host.hidden = false;
  }

  // ---- the Achievements page ---------------------------------------------------------------------
  function drawPage(host, status) {
    var sum = A.summary();
    host.textContent = '';
    if (!A.storageWorks()) host.appendChild(h('p', { 'class': 'notice', role: 'note', text: t('ach.notSaved') }));

    // Rank, score and the way to the next rank.
    var top = h('section', { 'class': 'card ach-summary', 'aria-labelledby': 'ach-rank-h' });
    top.appendChild(h('p', { 'class': 'ach-label', text: t('ach.rankLabel') }));
    top.appendChild(h('h2', { 'class': 'ach-rank', id: 'ach-rank-h' }, [badge('trophy'), h('span', { text: t('ach.rank.' + sum.rank) })]));
    top.appendChild(h('p', { 'class': 'ach-score', text: t('ach.score', { n: sum.score }) }));
    if (sum.next) {
      top.appendChild(h('p', { 'class': 'small text-muted', text: t('ach.nextRank', { name: t('ach.rank.' + sum.next.rank), n: sum.next.remaining }) }));
      top.appendChild(meter(sum.next.fraction));
    } else {
      top.appendChild(h('p', { 'class': 'small text-muted', text: t('ach.topRank') }));
    }
    var facts = [
      ['ach.stat.games', sum.stats.games], ['ach.stat.wins', sum.stats.wins], ['ach.stat.walls', sum.stats.walls],
      ['ach.stat.bestWins', sum.stats.bestWinStreak], ['ach.stat.days', sum.streak.days]
    ];
    top.appendChild(h('dl', { 'class': 'ach-stats' }, facts.map(function (f) {
      return h('div', {}, [h('dt', { text: t(f[0]) }), h('dd', { text: String(f[1]) })]);
    })));
    if (sum.streak.days > 0 && !sum.streak.playedToday) top.appendChild(h('p', { 'class': 'small text-muted', text: t('ach.streakToday', { n: sum.streak.days }) }));
    top.appendChild(h('p', { 'class': 'ach-count', text: t('ach.unlockedCount', { done: sum.unlocked, total: sum.total }) }));
    host.appendChild(top);

    // Every achievement, in groups.
    A.categories().forEach(function (cat) {
      var items = sum.items.filter(function (it) { return it.cat === cat; });
      if (!items.length) return;
      var done = items.filter(function (it) { return it.unlockedAt; }).length;
      var group = h('section', { 'class': 'ach-group', 'aria-labelledby': 'ach-cat-' + cat });
      group.appendChild(h('h2', { id: 'ach-cat-' + cat }, [t('ach.cat.' + cat), h('span', { 'class': 'ach-group-count', text: done + ' / ' + items.length })]));
      var grid = h('ul', { 'class': 'ach-grid' });
      items.forEach(function (it) {
        var open = !!it.unlockedAt;
        var state;
        if (open) state = dateText(it.unlockedAt) ? t('ach.unlockedOn', { date: dateText(it.unlockedAt) }) : t('ach.unlocked');
        else if (it.progress) state = it.progress[0] + ' / ' + it.progress[1];
        else state = t('ach.locked');
        var body = h('div', { 'class': 'ach-body' }, [
          h('h3', { 'class': 'ach-name', text: nameOf(it.id) }),
          h('p', { 'class': 'ach-desc', text: t('ach.' + it.id + '.desc') })
        ]);
        if (!open && it.progress) body.appendChild(meter(it.progress[0] / it.progress[1]));
        body.appendChild(h('p', { 'class': 'ach-state small' }, [open ? badge('check') : badge('lock'), h('span', { text: state })]));
        grid.appendChild(h('li', { 'class': 'ach-card ' + (open ? 'is-unlocked' : 'is-locked') }, [
          badge(it.icon), body, h('span', { 'class': 'ach-pts', text: t('ach.gain', { n: it.points }) })
        ]));
      });
      group.appendChild(grid);
      host.appendChild(group);
    });

    var resetBtn = h('button', { type: 'button', 'class': 'btn btn--secondary' }, [t('ach.reset')]);
    resetBtn.addEventListener('click', function () {
      if (!root.confirm(t('ach.resetConfirm'))) return;
      A.reset();
      drawPage(host, status);
      if (status) status.textContent = t('ach.resetDone');
    });
    host.appendChild(h('div', { 'class': 'ach-footer' }, [h('p', { 'class': 'small text-muted', text: t('ach.localOnly') }), resetBtn]));
  }

  root.QuoridorAchievementsUI = { reward: reward, sentence: sentence };

  // ---- pages -------------------------------------------------------------------------------------
  function start() {
    var teasers = doc.querySelectorAll('[data-progress-teaser]');
    var page = doc.querySelector('[data-achievements]');
    var status = doc.querySelector('[data-ach-status]');
    function draw() {
      Array.prototype.forEach.call(teasers, drawTeaser);
      if (page) drawPage(page, status);
    }
    if (!teasers.length && !page) return;
    draw();
    if (I18n) I18n.onChange(draw);
    // Another tab finished a game: show it here too.
    root.addEventListener('storage', function (e) { if (e.key === null || e.key === 'quoridor.progress') draw(); });
  }
  if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', start); else start();
})(typeof self !== 'undefined' ? self : this);
