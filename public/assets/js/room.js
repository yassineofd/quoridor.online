/* Private room shell. No room server exists yet, so a real /room/{id}/ URL resolves to the
   "unavailable" state. Append ?preview=<state> to see the other designed states. */
(function () {
  var STATES = ['waiting', 'join', 'starting', 'reconnecting', 'invalid', 'full', 'expired', 'unavailable', 'left'];
  var params = new URLSearchParams(window.location.search);
  var preview = params.get('preview');
  var isPreview = STATES.indexOf(preview) !== -1;
  var state = isPreview ? preview : 'unavailable';

  Array.prototype.forEach.call(document.querySelectorAll('[data-state]'), function (p) {
    p.hidden = p.getAttribute('data-state') !== state;
  });

  var previewNote = document.querySelector('[data-preview-note]');
  if (previewNote) previewNote.hidden = !isPreview;

  // Preview-only sample values; real values will come from the room server.
  var linkEl = document.getElementById('invite-link');
  var codeEl = document.getElementById('invite-code');
  if (linkEl) linkEl.textContent = window.location.origin + window.location.pathname.split('/room/')[0] + '/room/EXAMPLE-ROOM-ID/';
  if (codeEl) codeEl.textContent = 'K7M2QX';

  var status = document.getElementById('copy-status');
  function copyText(text) {
    function done() { status.textContent = 'Copied to clipboard.'; }
    function fail() { status.textContent = 'Copy failed. Select the text and copy it manually.'; }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, fail);
    } else {
      fail();
    }
  }
  Array.prototype.forEach.call(document.querySelectorAll('[data-copy]'), function (btn) {
    btn.addEventListener('click', function () {
      var target = document.getElementById(btn.getAttribute('data-copy'));
      if (target && status) copyText(target.textContent.trim());
    });
  });

  Array.prototype.forEach.call(document.querySelectorAll('[data-leave]'), function (btn) {
    btn.addEventListener('click', function () {
      if (window.confirm('Leave this room? If a game is in progress it counts as a forfeit.')) {
        window.location.href = window.location.pathname + '?preview=left';
      }
    });
  });
})();
