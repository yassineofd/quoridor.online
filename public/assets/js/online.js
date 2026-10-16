/* Client for the online-play server (server/api.py): rooms, matchmaking and the live game session.

   Seat tokens are kept in localStorage per room so a reload or a dropped connection rejoins the
   same seat. They are sent in a header, never in a URL. Usernames are display names only.        */
(function (root) {
  'use strict';

  // The site can live in any sub-folder, so find its root from the stylesheet link instead of
  // assuming "/". (/assets/css/styles.css is always at <root>/assets/css/styles.css.)
  function siteRoot() {
    var link = document.querySelector('link[rel="stylesheet"][href*="assets/css/styles.css"]');
    var href = link ? link.href : location.href;
    return href.replace(/assets\/css\/styles\.css.*$/, '');
  }
  var ROOT = siteRoot();

  function ApiFailure(status, code, message) {
    this.status = status; this.code = code; this.message = message;
  }
  ApiFailure.prototype = Object.create(Error.prototype);

  // Resolves with parsed JSON, or rejects with ApiFailure. status 0 = server unreachable.
  function call(method, path, body, token, signal) {
    var headers = {};
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (token) headers['X-Seat-Token'] = token;
    return fetch(ROOT + 'api' + path, {
      method: method, headers: headers, body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer', signal: signal
    }).then(function (res) {
      return res.text().then(function (text) {
        var data = null;
        try { data = JSON.parse(text); } catch (e) { /* not our server */ }
        if (!res.ok || data === null) {
          throw new ApiFailure(data === null ? 0 : res.status, data && data.error, (data && data.message) || 'The game server could not be reached.');
        }
        return data;
      });
    }, function (err) {
      if (err && err.name === 'AbortError') throw err;
      throw new ApiFailure(0, 'unreachable', 'The game server could not be reached.');
    });
  }

  // ---- seat tokens ----------------------------------------------------------------------
  function key(roomId) { return 'quoridor.seat.' + roomId; }
  function saveSeat(roomId, info) { try { localStorage.setItem(key(roomId), JSON.stringify(info)); } catch (e) { /* storage blocked */ } }
  function loadSeat(roomId) {
    try { var v = JSON.parse(localStorage.getItem(key(roomId))); return v && v.token ? v : null; } catch (e) { return null; }
  }
  function forgetSeat(roomId) { try { localStorage.removeItem(key(roomId)); } catch (e) { /* ignore */ } }

  function roomUrl(roomId) { return ROOT + 'room/' + encodeURIComponent(roomId) + '/'; }

  // ---- matchmaking ----------------------------------------------------------------------
  // handlers: onMatched({roomId, token, seat}), onError(failure). Returns {cancel()}.
  function search(username, handlers) {
    var ticket = null, stopped = false, controller = null;
    call('POST', '/queue', { username: username }).then(function (t) {
      ticket = t.ticket;
      if (stopped) return call('DELETE', '/queue/' + ticket).catch(function () {});
      poll();
    }, function (err) { if (!stopped) handlers.onError(err); });

    function poll() {
      if (stopped) return;
      controller = new AbortController();
      call('GET', '/queue/' + ticket, undefined, undefined, controller.signal).then(function (r) {
        if (stopped) return;
        if (r.status === 'matched') { stopped = true; handlers.onMatched(r); } else poll();
      }, function (err) {
        if (stopped || (err && err.name === 'AbortError')) return;
        if (err.status === 0) setTimeout(poll, 2000); // transient: try again
        else handlers.onError(err);
      });
    }
    return {
      cancel: function () {
        stopped = true;
        if (controller) controller.abort();
        if (ticket) call('DELETE', '/queue/' + ticket).catch(function () {});
      }
    };
  }

  // ---- live session ---------------------------------------------------------------------
  // Long-polls the room and calls handlers.onState(snapshot) for each change. Reconnects by
  // itself; handlers.onConnection(false|true) reports drops; handlers.onGone() when the seat is
  // no longer valid (room deleted or left).
  function session(roomId, token, handlers) {
    var since = null, stopped = false, controller = null, failing = false, delay = 500;

    function loop() {
      if (stopped) return;
      controller = new AbortController();
      var q = since === null ? '' : '?since=' + since;
      call('GET', '/rooms/' + roomId + '/state' + q, undefined, token, controller.signal).then(function (snap) {
        if (stopped) return;
        if (failing) { failing = false; handlers.onConnection(true); }
        delay = 500;
        since = snap.version;
        handlers.onState(snap);
        setTimeout(loop, 0);
      }, function (err) {
        if (stopped || (err && err.name === 'AbortError')) return;
        if (err.status === 403 || err.status === 404) { stopped = true; handlers.onGone(err); return; }
        if (!failing) { failing = true; handlers.onConnection(false); }
        delay = Math.min(delay * 2, 5000);
        setTimeout(loop, delay);
      });
    }
    loop();

    function act(path, body) { return call('POST', '/rooms/' + roomId + path, body, token); }
    return {
      send: function (move) {
        return act('/move', { move: move }).then(function (snap) { since = snap.version; handlers.onState(snap); return snap; });
      },
      resign: function () { return act('/resign').then(function (snap) { since = snap.version; handlers.onState(snap); }); },
      rematch: function () { return act('/rematch').then(function (snap) { since = snap.version; handlers.onState(snap); }); },
      leave: function () { stopped = true; if (controller) controller.abort(); return act('/leave').catch(function () {}); },
      stop: function () { stopped = true; if (controller) controller.abort(); }
    };
  }

  root.QuoridorOnline = {
    root: ROOT, call: call, ApiFailure: ApiFailure,
    saveSeat: saveSeat, loadSeat: loadSeat, forgetSeat: forgetSeat, roomUrl: roomUrl,
    createRoom: function (username) { return call('POST', '/rooms', { username: username }); },
    joinByCode: function (code, username) { return call('POST', '/rooms/join', { code: code, username: username }); },
    peek: function (roomId) { return call('GET', '/rooms/' + roomId); },
    joinById: function (roomId, username) { return call('POST', '/rooms/' + roomId + '/join', { username: username }); },
    search: search, session: session
  };
})(typeof self !== 'undefined' ? self : this);
