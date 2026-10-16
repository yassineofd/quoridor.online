/* Play-mode forms. The game engine, matchmaking and room servers are not built yet,
   so every form validates its input and then reports honestly that the feature is not live. */
(function () {
  var USERNAME_RE = /^[A-Za-z0-9 _.\-]{2,20}$/;
  var CODE_RE = /^[A-HJ-NP-Z2-9]{6}$/; // unambiguous alphabet: no 0/O/1/I

  function $(sel, root) { return (root || document).querySelector(sel); }

  function showError(input, errorEl, message) {
    errorEl.textContent = message;
    errorEl.hidden = false;
    input.setAttribute('aria-invalid', 'true');
    input.focus();
  }
  function clearError(input, errorEl) {
    errorEl.hidden = true;
    errorEl.textContent = '';
    input.removeAttribute('aria-invalid');
  }

  function checkUsername(input, errorEl) {
    var value = input.value.trim();
    if (!USERNAME_RE.test(value)) {
      showError(input, errorEl, 'Use 2 to 20 characters: letters, numbers, spaces, dots, dashes or underscores.');
      return null;
    }
    clearError(input, errorEl);
    return value;
  }

  var form = $('[data-play-form]');
  if (!form) return;

  var notice = $('[data-unavailable]');
  var kind = form.getAttribute('data-play-form');
  var nameInput = $('#username', form);
  var nameError = $('#username-error', form);
  var codeInput = $('#code', form);
  var codeError = $('#code-error', form);

  if (nameInput) nameInput.addEventListener('input', function () { clearError(nameInput, nameError); });
  if (codeInput) {
    codeInput.addEventListener('input', function () {
      codeInput.value = codeInput.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
      clearError(codeInput, codeError);
    });
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (nameInput && !checkUsername(nameInput, nameError)) return;
    if (kind === 'join-room' && codeInput && !CODE_RE.test(codeInput.value)) {
      showError(codeInput, codeError, 'Pairing codes are 6 characters (letters A to Z and digits 2 to 9). Check the code and try again.');
      return;
    }
    if (notice) {
      notice.hidden = false;
      notice.setAttribute('tabindex', '-1');
      notice.focus();
    }
  });
})();
