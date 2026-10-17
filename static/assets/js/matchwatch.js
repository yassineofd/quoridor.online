/* Keeps an online search running while the player does something else on the site.

   The search page (play.js) leaves the ticket of a running search in this tab's session storage. Every
   other play page loads this file: it picks the search up, shows a small "still searching" note, and when
   the server finds an opponent it asks whether to join. Nothing starts without a yes: until then the
   server treats this player as "away" and holds the match for them (see server/rooms.py).

   Leaving the site's play pages lets the search lapse: the server drops a search nobody polls for 20 s. */
(function (root) {
  'use strict';
  var Online = root.QuoridorOnline;
  var I18n = root.QuoridorI18n;
  function t(key, params) { return I18n ? I18n.t(key, params) : key; }
  if (!Online) return;
  var saved = Online.loadSearch();
  if (!saved) return;

  var search = null, chip = null, toast = null, tick = null, endedTimer = null;

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
    var b = h('button', { type: 'button', 'class': 'btn ' + cls, text: t(text) });
    b.addEventListener('click', onClick);
    return b;
  }
  function remove(n) { if (n && n.parentNode) n.parentNode.removeChild(n); }

  // ---- the small "still searching" note ---------------------------------------------------
  function showChip(message, withStop) {
    remove(chip);
    var kids = [h('span', { 'class': 'bg-search__dot', 'aria-hidden': 'true' }), h('span', { text: message })];
    if (withStop) kids.push(button('watch.stop', 'btn--secondary btn--sm', stopSearching));
    chip = h('div', { 'class': 'bg-search', role: 'status' }, kids);
    document.body.appendChild(chip);
  }

  function stopSearching() {
    if (search) search.cancel();
    search = null;
    end();
  }
  // The search is over (cancelled, ended by the server, or replaced by a game): clean up the page.
  function end(message) {
    search = null;
    Online.clearSearch();
    clearInterval(tick); hideOffer();
    remove(chip); chip = null;
    if (message) {
      showChip(message, false);
      endedTimer = setTimeout(function () { remove(chip); chip = null; }, 8000);
    }
  }

  // ---- the offer --------------------------------------------------------------------------
  function gameInProgress() { return !!document.querySelector('svg.board'); }

  function hideOffer() { clearInterval(tick); remove(toast); toast = null; }

  function showOffer(offer) {
    var deadline = Date.now() + offer.expires * 1000;
    if (toast && toast.getAttribute('data-opponent') === offer.opponent) return; // already showing it
    hideOffer();
    var left = h('span', { 'class': 'match-offer__left', 'aria-hidden': 'true' });
    var join = button('watch.join', 'btn--primary', function () { answer(true); });
    var later = button('watch.notNow', 'btn--secondary', function () { answer(false); });
    var note = t(gameInProgress() ? 'watch.endsGame' : 'watch.goesToGame');
    toast = h('div', { 'class': 'match-offer', role: 'group', 'aria-label': t('watch.offerLabel'), 'data-opponent': offer.opponent }, [
      h('p', { 'class': 'match-offer__title', role: 'alert', text: t('watch.offerTitle', { name: offer.opponent }) }),
      h('p', { 'class': 'match-offer__note small text-muted' }, [note + ' ', left]),
      h('div', { 'class': 'btn-row' }, [join, later])
    ]);
    document.body.appendChild(toast);
    function update() {
      var s = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      left.textContent = t('watch.offerEnds', { n: s });
    }
    update(); tick = setInterval(update, 1000);

    function answer(yes) {
      join.disabled = later.disabled = true;
      if (!yes) {
        search.decline().then(hideOffer, hideOffer);
        return;
      }
      join.textContent = t('watch.joining');
      // The poll in progress delivers the match once the server has the answer.
      search.accept().then(null, function () {
        hideOffer();
        showChip(t('watch.gone'), true);
      });
    }
  }

  // ---- joining ----------------------------------------------------------------------------
  function joinMatch(res) {
    Online.saveSeat(res.roomId, { token: res.token, seat: res.seat, name: saved.name });
    Online.clearSearch();
    search = null;
    var go = function () { root.location.href = Online.roomUrl(res.roomId); };
    // A private room that is still waiting for a friend is closed rather than left open.
    var m = /\/room\/([A-Za-z0-9_-]{8,64})\/?$/.exec(root.location.pathname);
    var seat = m && Online.loadSeat(m[1]);
    if (seat) Online.call('POST', '/rooms/' + m[1] + '/leave', undefined, seat.token).then(go, go);
    else go();
  }

  // ---- start ------------------------------------------------------------------------------
  showChip(t('watch.still'), true);

  search = Online.search(saved.name, {
    onUpdate: function (r) {
      clearTimeout(endedTimer);
      if (r.status === 'offer') showOffer(r.offer); else hideOffer();
    },
    onMatched: joinMatch,
    onConnection: function () {},
    onSuperseded: function () { end(); remove(chip); chip = null; Online.saveSearch(saved); }, // another tab runs it now
    onError: function (err) {
      end(err && err.status === 404 ? t('watch.ended') : null);
    }
  }, { ticket: saved.ticket, away: true });

  // The page is going away, but the search carries on on the next play page.
  root.addEventListener('pagehide', function () { if (search) search.detach(); });
  root.addEventListener('pageshow', function (e) { if (e.persisted && Online.loadSearch()) root.location.reload(); });

  root.QuoridorMatchwatch = {
    // The player is now in a game with a friend: no more offers, and the search is over.
    stop: function () { stopSearching(); }
  };
})(window);
