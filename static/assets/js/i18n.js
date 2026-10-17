/* Language support for the whole site: the translate button, page text, and the messages the game scripts build.

   Page text is tagged at build time (see i18n.py): elements carry data-i18n="<id>" (their contents) or
   data-i18n-attr="<attribute>:<id>" (an attribute). Choosing a language downloads assets/i18n/<lang>.json once
   and swaps the text in; English is the page itself and needs no download. Anything missing from a catalog
   simply stays in English.

   Scripts ask for their own messages with QuoridorI18n.t('key', {name: 'value'}). The language is a display
   choice of this browser only: it is never sent to the game server, so people who use different languages
   share the same matchmaking and rooms.                                                                  */
(function (root) {
  'use strict';

  var STORAGE_KEY = 'quoridor.lang';
  var RTL = { ar: true };
  var NAMES = { en: 'English', es: 'Español', fr: 'Français', de: 'Deutsch', ar: 'العربية' };
  var EN = root.QuoridorI18nEn || {};
  var doc = root.document;

  var current = root.QUORIDOR_LANG || 'en';
  var catalogs = {};
  var listeners = [];

  // The site can live in any sub-folder, so find its root from the manifest link (as online.js does).
  function siteRoot() {
    var link = doc.querySelector('link[rel="manifest"]');
    return (link ? link.href : root.location.href).replace(/site\.webmanifest.*$/, '');
  }
  var ROOT = siteRoot();

  // ---- messages built by scripts ----------------------------------------------------------
  var NAME_PARAMS = { name: 1, other: 1, who: 1, host: 1 }; // parameters that hold a player's name
  var RTL_CHARS = /[֐-ࣿיִ-﷿ﹰ-﻿]/;

  // Player names are typed by people in any script. Isolating them keeps a name in one direction from
  // scrambling the sentence around it when the sentence runs the other way.
  function isolate(value) {
    var s = String(value);
    return (RTL[current] || RTL_CHARS.test(s)) ? '⁨' + s + '⁩' : s;
  }

  function t(key, params) {
    var cat = catalogs[current];
    var text = (cat && cat.j && cat.j[key]) || EN[key];
    if (text === undefined) text = key;
    if (!params) return text;
    return text.replace(/\{(\w+)\}/g, function (m, name) {
      if (!Object.prototype.hasOwnProperty.call(params, name)) return m;
      var v = params[name];
      return NAME_PARAMS[name] ? isolate(v) : String(v);
    });
  }

  function has(key) { return EN[key] !== undefined; }

  // Text for a failed request: the server sends a stable error code, which is shown in the visitor's own
  // language. The server's English sentence is only the fallback for a code this site does not know.
  function errorText(err) {
    var key = 'err.' + (err && err.code);
    if (has(key)) return t(key);
    if (err && err.status === 0) return t('err.unreachable');
    return (err && err.message) || t('err.generic');
  }

  // ---- page text --------------------------------------------------------------------------
  var homePrefix = (function () {
    var a = doc.querySelector('a.brand');
    var h = a && a.getAttribute('href');
    return h && /\/$/.test(h) ? h : './';
  })();

  // Translated text is written with root-relative links ("/play/"); pages use links relative to their own folder, without the trailing slash.
  function localizeLinks(markup) {
    return markup.replace(/\b(href|src|action)="\/(?!\/)([^"?#]*?)\/*([?#][^"]*)?"/g, function (m, attr, path, tail) {
      return attr + '="' + homePrefix + path + (tail || '') + '"';
    });
  }

  var PLACEHOLDER_SELECTOR = 'svg,input,img';

  function store(el) { return el.__q || (el.__q = {}); }

  // The element's own contents as a template: icons and fields become <svg/>, <input/>, <img/>,
  // the same notation the translations use.
  function templateOf(el) {
    return el.innerHTML
      .replace(/<svg\b[\s\S]*?<\/svg>/g, '<svg/>')
      .replace(/<input\b[^>]*>/g, '<input/>')
      .replace(/<img\b[^>]*>/g, '<img/>');
  }

  function setContents(el, template) {
    var st = store(el);
    if (st.english === undefined) {
      st.english = templateOf(el);
      st.lead = /^\s/.test(el.innerHTML);
      st.trail = /\s$/.test(el.innerHTML);
      st.parts = Array.prototype.slice.call(el.querySelectorAll(PLACEHOLDER_SELECTOR));
    }
    var holder = doc.createElement('template');
    holder.innerHTML = (st.lead ? ' ' : '') + localizeLinks(template) + (st.trail ? ' ' : '');
    var i = 0;
    Array.prototype.forEach.call(holder.content.querySelectorAll(PLACEHOLDER_SELECTOR), function (slot) {
      var real = st.parts[i++];
      if (real && slot.parentNode) slot.parentNode.replaceChild(real, slot);
    });
    el.textContent = '';
    el.appendChild(holder.content);
  }

  function setAttr(el, name, value) {
    var st = store(el);
    st.attrs = st.attrs || {};
    if (!(name in st.attrs)) st.attrs[name] = name === 'text' ? el.textContent : el.getAttribute(name);
    if (value === undefined) value = st.attrs[name];
    if (name === 'text') el.textContent = value;
    else el.setAttribute(name, value);
  }

  function applyPage() {
    var cat = current === 'en' ? null : catalogs[current];
    var page = (cat && cat.p) || {};
    Array.prototype.forEach.call(doc.querySelectorAll('[data-i18n]'), function (el) {
      var st = store(el);
      var text = page[el.getAttribute('data-i18n')];
      if (text !== undefined) setContents(el, text);
      else if (st.english !== undefined) setContents(el, st.english);
    });
    Array.prototype.forEach.call(doc.querySelectorAll('[data-i18n-attr]'), function (el) {
      el.getAttribute('data-i18n-attr').split(',').forEach(function (pair) {
        var bits = pair.split(':');
        setAttr(el, bits[0], page[bits[1]]);
      });
    });
  }

  // ---- loading and switching --------------------------------------------------------------
  function load(lang) {
    if (lang === 'en' || catalogs[lang]) return Promise.resolve();
    return root.fetch(ROOT + 'assets/i18n/' + lang + '.json', { credentials: 'omit' })
      .then(function (res) { if (!res.ok) throw new Error('catalog ' + res.status); return res.json(); })
      .then(function (cat) { catalogs[lang] = cat; });
  }

  function reflect() {
    var html = doc.documentElement;
    html.lang = current;
    html.dir = RTL[current] ? 'rtl' : 'ltr';
    var code = doc.querySelector('[data-lang-code]');
    if (code) code.textContent = current.toUpperCase();
    Array.prototype.forEach.call(doc.querySelectorAll('[data-lang]'), function (b) {
      if (b.getAttribute('data-lang') === current) b.setAttribute('aria-current', 'true');
      else b.removeAttribute('aria-current');
    });
  }

  function show(lang) {
    current = lang;
    root.QUORIDOR_LANG = lang;
    applyPage();
    reflect();
    doc.documentElement.classList.remove('i18n-pending');
    listeners.slice().forEach(function (fn) { try { fn(lang); } catch (e) { /* one listener must not stop the rest */ } });
  }

  var ready = Promise.resolve();
  function setLanguage(lang, remember) {
    if (!NAMES[lang]) return Promise.resolve();
    if (remember !== false) { try { root.localStorage.setItem(STORAGE_KEY, lang); } catch (e) { /* storage blocked */ } }
    ready = load(lang).then(function () { show(lang); }, function () {
      // The translation could not be downloaded (offline?): keep showing what is on screen.
      doc.documentElement.classList.remove('i18n-pending');
    });
    return ready;
  }

  // ---- the translate button ---------------------------------------------------------------
  function wireSwitcher() {
    var toggle = doc.getElementById('lang-toggle');
    var menu = doc.getElementById('lang-menu');
    if (!toggle || !menu) return;

    function setOpen(open, returnFocus) {
      menu.hidden = !open;
      toggle.setAttribute('aria-expanded', String(open));
      if (open) {
        var cur = menu.querySelector('[aria-current="true"]') || menu.querySelector('button');
        if (cur) cur.focus();
      } else if (returnFocus) toggle.focus();
    }
    toggle.addEventListener('click', function () { setOpen(menu.hidden, false); });
    menu.addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('[data-lang]') : null;
      if (!b) return;
      setLanguage(b.getAttribute('data-lang'));
      setOpen(false, true);
    });
    doc.addEventListener('keydown', function (e) {
      if (menu.hidden) return;
      if (e.key === 'Escape') { setOpen(false, true); return; }
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        var items = Array.prototype.slice.call(menu.querySelectorAll('button'));
        var at = items.indexOf(doc.activeElement);
        var next = items[(at + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length];
        if (next) { e.preventDefault(); next.focus(); }
      }
    });
    doc.addEventListener('click', function (e) {
      if (!menu.hidden && !(e.target.closest && e.target.closest('[data-lang-switch]'))) setOpen(false, false);
    });
    menu.addEventListener('focusout', function (e) {
      if (!menu.hidden && e.relatedTarget && !(e.relatedTarget.closest && e.relatedTarget.closest('[data-lang-switch]'))) setOpen(false, false);
    });
  }

  root.QuoridorI18n = {
    t: t,
    has: has,
    errorText: errorText,
    language: function () { return current; },
    isRtl: function () { return !!RTL[current]; },
    setLanguage: setLanguage,
    // Call fn(lang) after every language change. Scripts use it to redraw text they built themselves.
    // Returns a function that stops the calls.
    onChange: function (fn) {
      listeners.push(fn);
      return function () { var i = listeners.indexOf(fn); if (i !== -1) listeners.splice(i, 1); };
    },
    ready: function () { return ready; },
    root: ROOT
  };

  wireSwitcher();
  reflect();
  if (current !== 'en') ready = load(current).then(function () { show(current); }, function () {
    doc.documentElement.classList.remove('i18n-pending');
  });
  else doc.documentElement.classList.remove('i18n-pending');
})(window);
