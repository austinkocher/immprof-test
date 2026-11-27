/* The editors' writing page for the ImmigrationProf Blog (layouts/write.html).
   A post is saved as a file in the site's repository on GitHub, on a branch of its own with a pull request: a draft.
   GitHub builds a preview of each draft (.github/workflows/pages.yml), and Publish merges the draft into the site.
   These are the same drafts the first form (/admin/, Sveltia CMS) makes, so either form can open the other's drafts.
   The editor signs in with a GitHub access token that stays in this browser and is sent only to api.github.com.
   On this computer, http://localhost:4176/write/?practice uses a pretend repository kept in the browser, for trying the page. */
(function () {
  'use strict';
  var D = JSON.parse(document.getElementById('write-data').textContent);
  var R = D.repo, BASE = D.branch, SITE = D.site.replace(/\/?$/, '/');
  var root = document.getElementById('write');
  var PRACTICE = /^(localhost|127\.0\.0\.1)$/.test(location.hostname) && /[?&]practice\b/.test(location.search);
  var PREFIX = 'cms/posts/', DIR = 'content/posts/', MEDIA = 'assets/media/';

  /* ---------- small helpers ---------- */
  var store = {
    get: function (k) { try { return localStorage.getItem('immprof.' + k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem('immprof.' + k, v); } catch (e) {} },
    del: function (k) { try { localStorage.removeItem('immprof.' + k); } catch (e) {} }
  };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function $(sel, el) { return (el || root).querySelector(sel); }
  function $all(sel, el) { return Array.prototype.slice.call((el || root).querySelectorAll(sel)); }
  function toB64(bytes) { var s = '', i; for (i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000)); return btoa(s); }
  function textToB64(t) { return toB64(new TextEncoder().encode(t)); }
  function b64ToText(b) { var bin = atob(b.replace(/\s/g, '')), a = new Uint8Array(bin.length), i; for (i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i); return new TextDecoder().decode(a); }
  function fileToB64(blob) { return blob.arrayBuffer().then(function (b) { return toB64(new Uint8Array(b)); }); }
  function slugify(t) {
    var s = String(t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
    return s.slice(0, 80).replace(/-+$/, '');
  }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function isoLocal(d) {
    var o = -d.getTimezoneOffset(), a = Math.abs(o);
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + 'T' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds()) + (o < 0 ? '-' : '+') + pad(Math.floor(a / 60)) + ':' + pad(a % 60);
  }
  function forInput(iso) { var d = new Date(iso); if (isNaN(d)) return ''; return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + 'T' + pad(d.getHours()) + ':' + pad(d.getMinutes()); }
  function ago(iso) {
    var m = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
    if (isNaN(m)) return '';
    if (m < 1) return 'just now';
    if (m < 60) return m + (m === 1 ? ' minute ago' : ' minutes ago');
    if (m < 1440) { var h = Math.round(m / 60); return h + (h === 1 ? ' hour ago' : ' hours ago'); }
    var d = Math.round(m / 1440); return d + (d === 1 ? ' day ago' : ' days ago');
  }

  /* ---------- the post as a file ---------- */
  function parsePost(text) {
    var m = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/.exec(text), fm = {}, body = text;
    if (m) { try { fm = jsyaml.load(m[1], { schema: jsyaml.JSON_SCHEMA }) || {}; } catch (e) { fm = {}; } body = m[2]; }
    function list(v) { return Array.isArray(v) ? v.filter(Boolean).map(String) : (v ? [String(v)] : []); }
    return {
      title: String(fm.title || ''), sections: list(fm.sections), tags: list(fm.tags), authors: list(fm.authors),
      contributors: list(fm.contributors), date: fm.date ? String(fm.date) : '', dateAuto: fm.date_auto === true || !fm.date,
      image: String(fm.image || ''), share_picture: fm.share_picture === true, wide: fm.wide === true,
      slug: String(fm.slug || ''), body: body.replace(/^\n+/, '').replace(/\s+$/, '')
    };
  }
  function writePost(p) {
    var fm = { title: p.title, sections: p.sections, tags: p.tags, authors: p.authors, date: p.date };
    if (p.dateAuto) fm.date_auto = true;   /* the date is set again at the moment of publishing, then this line is removed */
    if (p.image) fm.image = p.image;
    if (p.share_picture) fm.share_picture = true;
    if (p.wide) fm.wide = true;
    if (p.contributors.length) fm.contributors = p.contributors;
    if (p.slug) fm.slug = p.slug;
    return '---\n' + jsyaml.dump(fm, { lineWidth: -1 }) + '---\n\n' + p.body.replace(/\s+$/, '') + '\n';
  }
  function blankPost() {
    return { title: '', sections: [], tags: [], authors: [store.get('byline') || ''].filter(Boolean), contributors: [], date: '', dateAuto: true, image: '', share_picture: false, wide: false, slug: '', body: '' };
  }

  /* ---------- GitHub ---------- */
  function makeGitHub(token) {
    function call(method, path, body, raw) {
      return fetch('https://api.github.com' + path, {
        method: method,
        headers: { Authorization: 'Bearer ' + token, Accept: raw ? 'application/vnd.github.raw+json' : 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' },
        body: body ? JSON.stringify(body) : undefined, cache: 'no-store'
      }).then(function (r) {
        if (r.status === 204) return null;
        if (!r.ok) return r.json().catch(function () { return {}; }).then(function (j) { var e = new Error(j.message || ('GitHub answered ' + r.status)); e.status = r.status; throw e; });
        return raw ? r.blob() : r.json();
      });
    }
    var repo = '/repos/' + R;
    return {
      me: function () { return call('GET', '/user'); },
      repo: function () { return call('GET', repo); },
      drafts: function () { return call('GET', repo + '/pulls?state=open&per_page=100').then(function (l) { return l.filter(function (p) { return p.head.ref.indexOf(PREFIX) === 0 && p.head.repo && p.head.repo.full_name === R; }); }); },
      file: function (path, ref) { return call('GET', repo + '/contents/' + encodeURI(path) + '?ref=' + encodeURIComponent(ref)); },
      blob: function (path, ref) { return call('GET', repo + '/contents/' + encodeURI(path) + '?ref=' + encodeURIComponent(ref), null, true); },
      put: function (path, b64, branch, message, sha) { var b = { message: message, content: b64, branch: branch }; if (sha) b.sha = sha; return call('PUT', repo + '/contents/' + encodeURI(path), b); },
      mainSha: function () { return call('GET', repo + '/git/ref/heads/' + BASE).then(function (r) { return r.object.sha; }); },
      branch: function (name, sha) { return call('POST', repo + '/git/refs', { ref: 'refs/heads/' + name, sha: sha }); },
      openPR: function (title, head) { return call('POST', repo + '/pulls', { title: title, head: head, base: BASE }); },
      merge: function (n, title) { return call('PUT', repo + '/pulls/' + n + '/merge', { merge_method: 'squash', commit_title: title }); },
      close: function (n) { return call('PATCH', repo + '/pulls/' + n, { state: 'closed' }); },
      dropBranch: function (name) { return call('DELETE', repo + '/git/refs/heads/' + name); }
    };
  }
  /* A pretend repository in this browser tab, for trying the page on this computer. Nothing leaves the browser. */
  function makePractice() {
    var S; try { S = JSON.parse(sessionStorage.getItem('immprof.practice')) || null; } catch (e) { S = null; }
    if (!S) S = { n: 0, prs: [], files: {} };
    function keep() { try { sessionStorage.setItem('immprof.practice', JSON.stringify(S)); } catch (e) {} }
    function ok(v) { return new Promise(function (res) { setTimeout(function () { res(v); }, 150); }); }
    function no(status, msg) { var e = new Error(msg); e.status = status; return Promise.reject(e); }
    function sha() { return Math.random().toString(16).slice(2).padEnd(12, '0') + Date.now().toString(16); }
    return {
      me: function () { return ok({ login: 'practice-editor' }); },
      repo: function () { return ok({ permissions: { push: true } }); },
      drafts: function () { return ok(S.prs.filter(function (p) { return p.state === 'open'; })); },
      file: function (path, ref) { var f = (S.files[ref] || {})[path]; return f ? ok({ content: f.b64, sha: f.sha }) : no(404, 'Not Found'); },
      blob: function (path, ref) { var f = (S.files[ref] || {})[path]; if (!f) return no(404, 'Not Found'); var bin = atob(f.b64), a = new Uint8Array(bin.length), i; for (i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i); return ok(new Blob([a])); },
      put: function (path, b64, branch, message) { var s = sha(); S.files[branch] = S.files[branch] || {}; S.files[branch][path] = { b64: b64, sha: s }; S.prs.forEach(function (p) { if (p.head.ref === branch) { p.head.sha = s; p.updated_at = new Date().toISOString(); } }); keep(); return ok({ content: { sha: s }, commit: { sha: s } }); },
      mainSha: function () { return ok('main'); },
      branch: function (name) { if (S.files[name]) return no(422, 'Reference already exists'); S.files[name] = {}; keep(); return ok({}); },
      openPR: function (title, head) { var p = { number: ++S.n, title: title, state: 'open', updated_at: new Date().toISOString(), user: { login: 'practice-editor' }, head: { ref: head, sha: sha(), repo: { full_name: R } } }; S.prs.push(p); keep(); return ok(p); },
      merge: function (n) { S.prs.forEach(function (p) { if (p.number === n) p.state = 'merged'; }); keep(); return ok({ merged: true }); },
      close: function (n) { S.prs.forEach(function (p) { if (p.number === n) p.state = 'closed'; }); keep(); return ok({}); },
      dropBranch: function (name) { delete S.files[name]; keep(); return ok(null); }
    };
  }

  var gh = null, me = '';

  /* ---------- sign in ---------- */
  function showSignIn(problem) {
    root.innerHTML =
      '<div class="w-door">' +
      '<h1>Write for ImmigrationProf</h1>' +
      '<p>This page is for the blog’s editors. Sign in once on this device and it remembers you.</p>' +
      (problem ? '<p class="w-problem">' + esc(problem) + '</p>' : '') +
      '<form class="w-signin"><label for="w-token">Your GitHub access token</label>' +
      '<input id="w-token" type="password" autocomplete="off" spellcheck="false" placeholder="Paste the token here">' +
      '<button class="w-btn w-primary" type="submit">Sign in</button></form>' +
      '<details class="w-how"><summary>How to get a token</summary><ol>' +
      '<li>Sign in to GitHub and open <a href="https://github.com/settings/personal-access-tokens/new" target="_blank" rel="noopener">New fine-grained token</a>.</li>' +
      '<li>Give it any name. Under Repository access choose “Only select repositories” and pick <strong>' + esc(R.split('/')[1]) + '</strong>.</li>' +
      '<li>Under Repository permissions set Contents and Pull requests to “Read and write”.</li>' +
      '<li>Generate the token, copy it and paste it above.</li></ol>' +
      '<p>The token is kept in this browser and is sent only to GitHub.</p></details></div>';
    $('.w-signin').addEventListener('submit', function (ev) {
      ev.preventDefault();
      var t = $('#w-token').value.trim(); if (!t) return;
      $('.w-signin button').disabled = true; $('.w-signin button').textContent = 'Signing in';
      start(t);
    });
  }
  function start(token) {
    gh = PRACTICE ? makePractice() : makeGitHub(token);
    Promise.all([gh.me(), gh.repo()]).then(function (a) {
      if (!a[1].permissions || !a[1].permissions.push) { showSignIn('That token can read the site but cannot save to it. Check that Contents and Pull requests are set to “Read and write”.'); return; }
      me = a[0].login; if (!PRACTICE) store.set('token', token);
      route();
    }).catch(function (e) {
      store.del('token');
      showSignIn(e.status === 401 ? 'GitHub did not accept that token. It may have expired or been copied without its last characters.' : e.status === 404 ? 'That token does not include the site’s repository. Make a token that names ' + R.split('/')[1] + '.' : 'Signing in did not work: ' + e.message);
    });
  }

  /* ---------- the list of drafts ---------- */
  function showHome(note) {
    leaveEditor();
    root.innerHTML =
      '<div class="w-home"><header class="w-home-h"><h1>Write for ImmigrationProf</h1>' +
      '<a class="w-btn w-primary" href="#/new">Write a post</a></header>' +
      (PRACTICE ? '<p class="w-flash">Practice copy. Nothing here is saved to the site.</p>' : '') +
      (note ? '<p class="w-flash">' + note + '</p>' : '') +
      '<h2>Drafts</h2><div class="w-drafts"><p class="w-note">Loading the drafts.</p></div>' +
      '<p class="w-foot">Signed in as ' + esc(me) + '. <button class="w-link" type="button" id="w-out">Sign out</button></p></div>';
    $('#w-out').addEventListener('click', function () { store.del('token'); gh = null; showSignIn(); });
    gh.drafts().then(function (prs) {
      var box = $('.w-drafts'); if (!box) return;
      if (!prs.length) { box.innerHTML = '<p class="w-note">No drafts. A post you save appears here until it is published.</p>'; return; }
      box.innerHTML = '<ul class="w-list">' + prs.map(function (p) {
        var slug = p.head.ref.slice(PREFIX.length);
        return '<li data-slug="' + esc(slug) + '"><a class="w-list-t" href="#/draft/' + encodeURIComponent(slug) + '">' + esc(slug.replace(/-/g, ' ')) + '</a>' +
          '<span class="w-list-m">Saved ' + esc(ago(p.updated_at)) + ' by ' + esc(p.user ? p.user.login : '') + '</span>' +
          '<span class="w-list-a"><a href="#/draft/' + encodeURIComponent(slug) + '">Edit</a>' + (PRACTICE ? '' : '<a href="' + esc(SITE + 'preview/pr-' + p.number + '/' + slug + '/') + '" target="_blank" rel="noopener">Preview</a>') + '</span></li>';
      }).join('') + '</ul>';
      /* The list shows each draft's own title once its file has been read. */
      prs.forEach(function (p) {
        var slug = p.head.ref.slice(PREFIX.length);
        gh.file(DIR + slug + '.md', p.head.ref).then(function (f) {
          var post = parsePost(b64ToText(f.content)), li = $('.w-list li[data-slug="' + slug.replace(/"/g, '') + '"]'); if (!li) return;
          if (post.title) $('.w-list-t', li).textContent = post.title;
          if (post.slug) { var pv = $all('.w-list-a a', li)[1]; if (pv) pv.href = SITE + 'preview/pr-' + p.number + '/' + post.slug + '/'; }
        }).catch(function () {});
      });
    }).catch(function (e) { var box = $('.w-drafts'); if (box) box.innerHTML = '<p class="w-problem">The drafts could not be read: ' + esc(e.message) + '</p>'; });
  }

  /* ---------- the editor ---------- */
  var E = null;   /* the open post: { post, slug, pr, fileSha, headSha, editor, pics, dirty, timer, poll } */
  function leaveEditor() {
    if (!E) return;
    clearTimeout(E.timer); clearInterval(E.poll);
    try { E.editor.destroy(); } catch (e) {}
    E = null; window.onbeforeunload = null;
  }
  function openDraft(slug) {
    leaveEditor();
    root.innerHTML = '<p class="w-note">Opening the draft.</p>';
    gh.drafts().then(function (prs) {
      var pr = prs.filter(function (p) { return p.head.ref === PREFIX + slug; })[0];
      if (!pr) { showHome('That draft is no longer open. It may have been published.'); return; }
      return gh.file(DIR + slug + '.md', pr.head.ref).then(function (f) {
        var post = parsePost(b64ToText(f.content));
        return loadPictures(post, pr.head.ref).then(function (pics) { showEditor(post, { slug: slug, pr: pr.number, fileSha: f.sha, headSha: pr.head.sha, pics: pics }); });
      });
    }).catch(function (e) { showHome('The draft could not be opened: ' + esc(e.message)); });
  }
  /* Pictures in a draft are files in the repository that the published site does not have yet. They are fetched from the
     draft's branch and shown from the browser's memory; the text keeps their real addresses when it is saved. */
  function loadPictures(post, ref) {
    var pics = {}, names = [], re = /\]\(\/media\/([^)\s]+)\)/g, m;
    while ((m = re.exec(post.body))) if (names.indexOf(m[1]) < 0) names.push(m[1]);
    return Promise.all(names.map(function (n) {
      return gh.blob(MEDIA + decodeURIComponent(n), ref).then(function (b) { pics[n] = { url: URL.createObjectURL(b), saved: true }; }).catch(function () {});
    })).then(function () {
      Object.keys(pics).forEach(function (n) { post.body = post.body.split('](/media/' + n + ')').join('](' + pics[n].url + ')'); });
      return pics;
    });
  }
  function realAddresses(body, pics) {
    Object.keys(pics).forEach(function (n) { body = body.split('](' + pics[n].url + ')').join('](/media/' + n + ')'); });
    return body;
  }
  function pictureName(file) {
    var dot = file.name.lastIndexOf('.'), ext = dot > 0 ? file.name.slice(dot + 1).toLowerCase().replace(/[^a-z0-9]/g, '') : (file.type.split('/')[1] || 'png');
    var d = new Date();
    return (slugify(dot > 0 ? file.name.slice(0, dot) : 'picture') || 'picture') + '-' + d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) + pad(d.getHours()) + pad(d.getMinutes()) + pad(d.getSeconds()) + '.' + ext;
  }

  function showEditor(post, st) {
    st = st || {};
    E = { post: post, slug: st.slug || '', pr: st.pr || 0, fileSha: st.fileSha || '', headSha: st.headSha || '', pics: st.pics || {}, lead: null, dirty: false, busy: false };
    var opt = function (list, sel, empty) { return (empty ? '<option value="">' + esc(empty) + '</option>' : '') + list.map(function (x) { return '<option' + (x === sel ? ' selected' : '') + '>' + esc(x) + '</option>'; }).join(''); };
    root.innerHTML =
      '<div class="w-bar"><a class="w-back" href="#/">Drafts</a><span class="w-state" aria-live="polite"></span>' +
      '<span class="w-bar-b"><span class="w-mode" role="group" aria-label="How the text is shown"><button type="button" data-mode="wysiwyg">Formatted</button><button type="button" data-mode="markdown">Markdown</button></span>' +
      '<button class="w-btn" type="button" id="w-save">Save draft</button>' +
      '<button class="w-btn w-primary" type="button" id="w-publish">Publish</button></span></div>' +
      '<div class="w-status" aria-live="polite"></div>' +
      '<article class="w-post">' +
      '<header class="w-post-h">' +
      '<select class="w-sec" id="w-sec" aria-label="Section">' + opt(D.sections, post.sections[0], 'Choose a section') + '</select>' +
      '<textarea class="w-title" id="w-title" rows="1" placeholder="Title" aria-label="Title">' + esc(post.title) + '</textarea>' +
      '<p class="w-by"><label for="w-author">Posted by</label> <select id="w-author">' + opt(D.authors, post.authors[0], 'Choose your name') + '</select></p>' +
      '</header>' +
      '<div class="w-text" id="w-text"></div>' +
      '<div class="w-tags"><span class="w-tags-l">Tags:</span><span class="w-chips"></span>' +
      '<input id="w-tag" list="w-taglist" placeholder="Add a tag" aria-label="Add a tag" autocomplete="off"><datalist id="w-taglist">' + D.tags.map(function (t) { return '<option value="' + esc(t) + '">'; }).join('') + '</datalist>' +
      '<span class="w-hint">One to four. Choose from the list where a tag fits.</span></div>' +
      '<details class="w-more"><summary>More options</summary><div class="w-more-in">' +
      '<div class="w-field"><span class="w-lab">Main picture</span><span class="w-pic"></span><input type="file" id="w-lead" accept="image/*">' +
      '<span class="w-hint">Optional. Shown beside the title on the homepage and under the text of the post.</span></div>' +
      '<label class="w-check"><input type="checkbox" id="w-share"' + (post.share_picture ? ' checked' : '') + '> Share with the main picture in place of the ImmigrationProf card</label>' +
      '<label class="w-check"><input type="checkbox" id="w-wide"' + (post.wide ? ' checked' : '') + '> Let landscape pictures in the text run the full width of the page</label>' +
      '<div class="w-field"><label class="w-lab" for="w-guest">Guest author</label><select id="w-guest">' + opt(D.guests, post.contributors[0], 'None') + '</select>' +
      '<span class="w-hint">Only for a guest post. The guest is shown as the author and you as the editor who posted it.</span></div>' +
      '<div class="w-field"><span class="w-lab">Date</span><label class="w-check"><input type="radio" name="w-when" value="auto"' + (post.dateAuto ? ' checked' : '') + '> The moment it is published</label>' +
      '<label class="w-check"><input type="radio" name="w-when" value="set"' + (post.dateAuto ? '' : ' checked') + '> This date and time <input type="datetime-local" id="w-date" value="' + esc(post.dateAuto ? '' : forInput(post.date)) + '"></label></div>' +
      (E.slug ? '' : '<div class="w-field"><label class="w-lab" for="w-slug">Web address</label><input id="w-slug" type="text" placeholder="made from the title" value="' + esc(post.slug) + '" spellcheck="false">' +
        '<span class="w-hint">Leave empty and the address is made from the title. It stays the same after the first save.</span></div>') +
      (E.pr ? '<div class="w-field"><button class="w-link w-danger" type="button" id="w-discard">Delete this draft</button></div>' : '') +
      '</div></details>' +
      '</article>';

    /* the text */
    var mode = store.get('mode') === 'markdown' ? 'markdown' : 'wysiwyg';
    /* In Markdown, an eye in the toolbar shows the text as it will read, in place of the editor's own Write and Preview tabs. */
    var eye = document.createElement('button');
    eye.type = 'button'; eye.className = 'w-eye'; eye.setAttribute('aria-label', 'Show how it will read'); eye.setAttribute('aria-pressed', 'false');
    eye.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="1.7"/></svg>';
    function look(on) {
      var tabs = $all('#w-text .toastui-editor-md-tab-container .tab-item');
      if (tabs.length > 1) tabs[on ? 1 : 0].click();
      eye.setAttribute('aria-pressed', on ? 'true' : 'false');
      $('#w-text').classList.toggle('is-looking', on);
    }
    eye.addEventListener('click', function () { look(eye.getAttribute('aria-pressed') !== 'true'); });
    E.editor = new toastui.Editor({
      el: $('#w-text'), height: 'auto', minHeight: '26rem', initialEditType: mode, previewStyle: 'tab', hideModeSwitch: true,
      usageStatistics: false, autofocus: false, placeholder: 'Write the post here.', initialValue: post.body,
      toolbarItems: [['heading', 'bold', 'italic'], ['quote', 'ul', 'ol'], ['link', 'image'], [{ name: 'look', tooltip: 'Show how it will read', el: eye }]],
      hooks: { addImageBlobHook: function (blob, done) { var n = pictureName(blob); E.pics[n] = { url: URL.createObjectURL(blob), blob: blob, saved: false }; done(E.pics[n].url, ''); changed(); } },
      events: { change: function () { if (E) changed(); } }
    });
    function showMode() { $all('.w-mode button').forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-mode') === mode ? 'true' : 'false'); }); $('#w-text').classList.toggle('is-markdown', mode === 'markdown'); }
    $all('.w-mode button').forEach(function (b) { b.addEventListener('click', function () { look(false); mode = b.getAttribute('data-mode'); E.editor.changeMode(mode, true); store.set('mode', mode); showMode(); }); });
    showMode();

    /* the title grows with its text */
    var title = $('#w-title');
    function grow() { title.style.height = 'auto'; title.style.height = title.scrollHeight + 'px'; }
    title.addEventListener('input', function () { title.value = title.value.replace(/\n/g, ' '); grow(); changed(); });
    title.addEventListener('keydown', function (ev) { if (ev.key === 'Enter') { ev.preventDefault(); E.editor.focus(); } });
    grow(); window.addEventListener('resize', grow);

    /* tags */
    function drawTags() {
      $('.w-chips').innerHTML = post.tags.map(function (t, i) { return '<span class="w-chip">' + esc(t) + '<button type="button" data-i="' + i + '" aria-label="Remove the tag ' + esc(t) + '">×</button></span>'; }).join('');
      $('#w-tag').hidden = post.tags.length >= 4;
    }
    function addTag(v) {
      v = v.trim().replace(/,$/, '').trim(); if (!v || post.tags.length >= 4) return;
      var known = D.tags.filter(function (t) { return t.toLowerCase() === v.toLowerCase(); })[0];
      v = known || v;
      if (post.tags.map(function (t) { return t.toLowerCase(); }).indexOf(v.toLowerCase()) < 0) { post.tags.push(v); changed(); }
      $('#w-tag').value = ''; drawTags();
    }
    $('.w-chips').addEventListener('click', function (ev) { var b = ev.target.closest('button'); if (!b) return; post.tags.splice(+b.getAttribute('data-i'), 1); drawTags(); changed(); });
    $('#w-tag').addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ',') { ev.preventDefault(); addTag(ev.target.value); } });
    $('#w-tag').addEventListener('change', function (ev) { addTag(ev.target.value); });
    drawTags();

    /* main picture */
    function drawLead() {
      var box = $('.w-pic');
      if (E.lead) box.innerHTML = '<img src="' + esc(E.lead.url) + '" alt=""><button class="w-link" type="button" id="w-nolead">Remove</button>';
      else if (post.image) box.innerHTML = '<span class="w-picname">' + esc(post.image.replace(/^\/media\//, '')) + '</span><button class="w-link" type="button" id="w-nolead">Remove</button>';
      else box.innerHTML = '';
      var b = $('#w-nolead'); if (b) b.addEventListener('click', function () { E.lead = null; post.image = ''; $('#w-lead').value = ''; drawLead(); changed(); });
    }
    $('#w-lead').addEventListener('change', function (ev) { var f = ev.target.files[0]; if (!f) return; E.lead = { name: pictureName(f), blob: f, url: URL.createObjectURL(f) }; drawLead(); changed(); });
    drawLead();
    if (post.image && E.pr) gh.blob(MEDIA + post.image.replace(/^\/media\//, ''), PREFIX + E.slug).then(function (b) { if (E && !E.lead && post.image) { var s = $('.w-picname'); if (s) s.outerHTML = '<img src="' + URL.createObjectURL(b) + '" alt="">'; } }).catch(function () {});

    $all('#w-sec,#w-author,#w-guest,#w-share,#w-wide,#w-date,#w-slug,input[name="w-when"]').forEach(function (el) { el.addEventListener('input', changed); el.addEventListener('change', changed); });
    $('#w-date').addEventListener('input', function () { $('input[name="w-when"][value="set"]').checked = true; });
    $('#w-save').addEventListener('click', function () { save().catch(function () {}); });
    $('#w-publish').addEventListener('click', askPublish);
    var del = $('#w-discard'); if (del) del.addEventListener('click', askDiscard);
    setState(E.pr ? 'Saved' : '');
    if (E.pr) watchPreview();
    if (!post.title) title.focus();
  }

  function setState(t) { var s = $('.w-state'); if (s) s.textContent = t; }
  function status(html, kind) { var s = $('.w-status'); if (s) { s.innerHTML = html ? '<p class="' + (kind === 'bad' ? 'w-problem' : 'w-flash') + '">' + html + '</p>' : ''; } }
  function changed() {
    if (!E || E.busy) return;
    if (!E.dirty) { E.dirty = true; window.onbeforeunload = function (ev) { ev.preventDefault(); ev.returnValue = ''; return ''; }; }
    setState('Not saved yet');
  }
  function gather() {
    var p = E.post;
    p.title = $('#w-title').value.trim();
    p.sections = $('#w-sec').value ? [$('#w-sec').value] : [];
    p.authors = $('#w-author').value ? [$('#w-author').value] : [];
    p.contributors = $('#w-guest').value ? [$('#w-guest').value] : [];
    p.share_picture = $('#w-share').checked; p.wide = $('#w-wide').checked;
    p.dateAuto = $('input[name="w-when"]:checked').value === 'auto' || !$('#w-date').value;
    if (!p.dateAuto) p.date = isoLocal(new Date($('#w-date').value));
    if ($('#w-slug')) p.slug = slugify($('#w-slug').value);
    if ($('#w-tag').value.trim() && p.tags.length < 4) p.tags.push($('#w-tag').value.trim());
    p.body = E.editor.getMarkdown();
    var miss = [];
    if (!p.title) miss.push('a title');
    if (!p.sections.length) miss.push('a section');
    if (!p.authors.length) miss.push('your name under “Posted by”');
    return miss;
  }
  /* Is this address free? A post already on the site, or another draft, may have it. */
  function freeSlug(want) {
    return gh.drafts().then(function (prs) {
      var taken = prs.map(function (p) { return p.head.ref.slice(PREFIX.length); });
      function tryOne(i) {
        var s = i ? want + '-' + (i + 1) : want;
        if (taken.indexOf(s) >= 0) return tryOne(i + 1);
        if (PRACTICE) return s;
        return fetch(SITE + s + '/', { method: 'HEAD', cache: 'no-store' }).then(function (r) { return r.ok ? tryOne(i + 1) : s; }).catch(function () { return s; });
      }
      return tryOne(0);
    });
  }
  function save(forPublish) {
    if (!E || E.busy) return Promise.reject(new Error('busy'));
    var miss = gather();
    if (miss.length) { status('Before saving, add ' + miss.join(', ').replace(/, ([^,]*)$/, ' and $1') + '.', 'bad'); return Promise.reject(new Error('incomplete')); }
    var p = E.post, first = !E.pr;
    E.busy = true; setState('Saving'); status(''); $('#w-save').disabled = $('#w-publish').disabled = true;
    if (p.dateAuto) p.date = isoLocal(new Date());
    if (forPublish) p.dateAuto = false;
    store.set('byline', p.authors[0]);
    var chain = Promise.resolve();
    if (first) chain = chain.then(function () { return freeSlug(p.slug || slugify(p.title) || 'post'); }).then(function (s) {
      E.slug = s; if (p.slug && p.slug !== s) p.slug = s;
      return gh.mainSha().then(function (sha) { return gh.branch(PREFIX + s, sha); });
    });
    var branch = function () { return PREFIX + E.slug; };
    /* pictures first, the post last, so the draft's newest change is the post itself */
    chain = chain.then(function () {
      var body = realAddresses(p.body, E.pics), todo = Object.keys(E.pics).filter(function (n) { return !E.pics[n].saved && body.indexOf('](/media/' + n + ')') >= 0; });
      p.body = body;
      return todo.reduce(function (c, n) { return c.then(function () { return fileToB64(E.pics[n].blob).then(function (b) { return gh.put(MEDIA + n, b, branch(), 'Add a picture to “' + p.title + '”'); }).then(function () { E.pics[n].saved = true; }); }); }, Promise.resolve());
    }).then(function () {
      if (!E.lead) return;
      return fileToB64(E.lead.blob).then(function (b) { return gh.put(MEDIA + E.lead.name, b, branch(), 'Add the main picture to “' + p.title + '”'); }).then(function () { p.image = '/media/' + E.lead.name; E.lead = null; });
    }).then(function () {
      return gh.put(DIR + E.slug + '.md', textToB64(writePost(p)), branch(), (first ? 'Create Post “' : 'Update Post “') + E.slug + '”', E.fileSha || undefined);
    }).then(function (r) {
      E.fileSha = r.content.sha; E.headSha = r.commit.sha;
      if (first) return gh.openPR('Create Post “' + E.slug + '”', branch()).then(function (pr) { E.pr = pr.number; history.replaceState(null, '', '#/draft/' + encodeURIComponent(E.slug)); var sl = $('#w-slug'); if (sl) sl.closest('.w-field').remove(); });
    }).then(function () {
      E.busy = false; E.dirty = false; window.onbeforeunload = null;
      setState('Saved ' + new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }));
      $('#w-save').disabled = $('#w-publish').disabled = false;
      if (!forPublish) watchPreview(true);
    });
    return chain.catch(function (e) {
      if (E) { E.busy = false; $('#w-save').disabled = $('#w-publish').disabled = false; setState('Not saved'); }
      if (e.message !== 'incomplete') status(e.status === 409 ? 'Someone else saved this draft after you opened it. Copy your text, go back to Drafts and open it again.' : 'Saving did not work: ' + esc(e.message), 'bad');
      throw e;
    });
  }

  /* The preview is a copy of the whole site with this draft in it, built by GitHub after each save. The build writes the
     draft's latest change into version.txt beside the preview, so this page can tell when the preview has caught up. */
  function previewURL() { return SITE + 'preview/pr-' + E.pr + '/' + (E.post.slug || E.slug) + '/'; }
  function watchPreview(fresh) {
    if (!E || !E.pr) return;
    clearInterval(E.poll);
    if (PRACTICE) { status('Saved. On the site, a link to the preview appears here about three minutes after each save.'); return; }
    var want = E.headSha, started = Date.now();
    function ready() { clearInterval(E.poll); status('The preview is ready. <a class="w-btn" href="' + esc(previewURL()) + '" target="_blank" rel="noopener">Open the preview</a>'); }
    function waiting() { status((fresh ? 'Saved. ' : '') + 'The preview is being built, which takes about three minutes. A link appears here when it is ready.'); }
    function check() {
      if (!E) return;
      fetch(SITE + 'preview/pr-' + E.pr + '/version.txt?t=' + Date.now(), { cache: 'no-store' }).then(function (r) { return r.ok ? r.text() : ''; }).then(function (t) {
        if (!E || E.headSha !== want) return;
        if (t.trim() === want) ready();
        else if (Date.now() - started > 12 * 60000) { clearInterval(E.poll); status('The preview is taking longer than usual. <a href="' + esc(previewURL()) + '" target="_blank" rel="noopener">Try the preview</a>, which may still show the earlier version.'); }
      }).catch(function () {});
    }
    waiting(); check(); E.poll = setInterval(check, 15000);
  }

  function askPublish() {
    if (!E || E.busy) return;
    status('Publish this post on the site now? <button class="w-btn w-primary" type="button" id="w-yes">Publish</button> <button class="w-btn" type="button" id="w-no">Not yet</button>');
    $('#w-no').addEventListener('click', function () { status(''); if (E.pr && !E.dirty) watchPreview(); });
    $('#w-yes').addEventListener('click', function () {
      clearInterval(E.poll);
      var title = E.post.title, auto = $('input[name="w-when"]:checked').value === 'auto' || !$('#w-date').value;
      /* A draft that takes its date from the moment of publishing is saved once more, so the date is now. */
      var first = (E.dirty || !E.pr || auto || E.post.dateAuto) ? save(true) : Promise.resolve();
      first.then(function () {
        E.busy = true; setState('Publishing'); $('#w-save').disabled = $('#w-publish').disabled = true;
        var n = E.pr, slug = E.slug, addr = SITE + (E.post.slug || E.slug) + '/';
        return gh.merge(n, 'Publish “' + title + '”').then(function () { return gh.dropBranch(PREFIX + slug).catch(function () {}); }).then(function () {
          current = '#/'; history.replaceState(null, '', '#/');
          showHome('Published: ' + esc(title) + '. It appears on the site in about three minutes' + (PRACTICE ? '.' : ' at <a href="' + esc(addr) + '" target="_blank" rel="noopener">' + esc(addr) + '</a>.'));
        });
      }).catch(function (e) {
        if (E) { E.busy = false; $('#w-save').disabled = $('#w-publish').disabled = false; }
        if (e.message !== 'incomplete' && e.message !== 'busy' && !$('.w-status .w-problem')) status('Publishing did not work: ' + esc(e.message), 'bad');
      });
    });
  }
  function askDiscard() {
    status('Delete this draft? This cannot be undone. <button class="w-btn w-primary" type="button" id="w-yes">Delete the draft</button> <button class="w-btn" type="button" id="w-no">Keep it</button>', 'bad');
    $('#w-no').addEventListener('click', function () { status(''); });
    $('#w-yes').addEventListener('click', function () {
      var n = E.pr, slug = E.slug, title = E.post.title;
      E.busy = true;
      gh.close(n).then(function () { return gh.dropBranch(PREFIX + slug).catch(function () {}); }).then(function () { E.dirty = false; current = '#/'; history.replaceState(null, '', '#/'); showHome('Deleted the draft: ' + esc(title) + '.'); })
        .catch(function (e) { if (E) E.busy = false; status('Deleting did not work: ' + esc(e.message), 'bad'); });
    });
  }

  /* ---------- which view ---------- */
  var current = '';
  function route() {
    if (!gh) return;
    var h = location.hash || '#/';
    if (E && E.dirty && h !== current) {
      if (!window.confirm('This post has changes that are not saved. Leave without saving?')) { history.replaceState(null, '', current); return; }
    }
    if (E && h === '#/draft/' + encodeURIComponent(E.slug)) { current = h; return; }   /* the address changed because the post was saved */
    current = h;
    if (h === '#/new') { leaveEditor(); showEditor(blankPost()); }
    else if (h.indexOf('#/draft/') === 0) openDraft(decodeURIComponent(h.slice(8)));
    else showHome();
  }
  window.addEventListener('hashchange', route);

  if (PRACTICE) start('practice');
  else if (store.get('token')) { root.innerHTML = '<p class="w-note">Signing in.</p>'; start(store.get('token')); }
  else showSignIn();
})();
