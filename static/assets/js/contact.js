/* Contact form: builds a mailto: draft in the visitor's own email app. Nothing is sent to or stored by this site. */
(function () {
  var form = document.getElementById('contact-form');
  if (!form) return;
  form.hidden = false;

  var message = document.getElementById('contact-message');
  var error = document.getElementById('contact-message-error');
  var status = document.getElementById('contact-status');
  var to = form.getAttribute('data-to');

  function field(id) { return document.getElementById(id).value.trim(); }

  function showError(text) {
    error.textContent = text;
    error.hidden = !text;
    message.setAttribute('aria-invalid', text ? 'true' : 'false');
  }

  message.addEventListener('input', function () { if (message.value.trim()) showError(''); });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (!field('contact-message')) {
      showError('Please write a message before continuing.');
      message.focus();
      return;
    }
    showError('');

    var topic = field('contact-topic');
    var lines = [field('contact-message'), ''];
    if (field('contact-name')) lines.push('Name: ' + field('contact-name'));
    if (field('contact-email')) lines.push('Reply to: ' + field('contact-email'));
    if (document.getElementById('contact-env').checked) {
      lines.push('Browser: ' + navigator.userAgent);
      lines.push('Screen: ' + window.screen.width + 'x' + window.screen.height + ', window ' + window.innerWidth + 'x' + window.innerHeight);
    }
    var href = 'mailto:' + to + '?subject=' + encodeURIComponent('[Quoridor.online] ' + topic) +
      '&body=' + encodeURIComponent(lines.join('\r\n'));

    status.hidden = false;
    var box = status.lastElementChild;
    box.textContent = 'Your email app should open with the message ready to send. If nothing happens, write to ' + to + ' directly.';
    window.location.href = href;
  });
})();
