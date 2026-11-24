// Light / dark theme switch; the choice is remembered in this browser.
(function () {
  var b = document.getElementById('theme-toggle');
  if (!b) return;
  b.addEventListener('click', function () {
    var next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('theme', next); } catch (e) {}
  });
})();

// Research page: clicking a tag (area, method, journal, status, topic, co-author)
// shows only the papers carrying it. The choice is kept in the URL (#tag=...).
// The search box narrows the list further: every word typed must appear in the
// paper's title, reference, co-authors, tags or abstract.
(function () {
  var menus = document.querySelector('.tagmenus');
  if (!menus) return;
  var cards = Array.prototype.slice.call(document.querySelectorAll('.card'));
  var links = Array.prototype.slice.call(menus.querySelectorAll('a[data-tag]'));
  var note = document.getElementById('filter-note');
  var box = document.getElementById('paper-search');

  function current() {
    var m = /^#tag=(.*)$/.exec(location.hash);
    return m ? decodeURIComponent(m[1]) : '';
  }
  function apply() {
    var tag = current(), shown = 0;
    var q = box.value.trim(), words = q.toLowerCase().split(/\s+/).filter(Boolean);
    cards.forEach(function (c) {
      var ok = !tag || c.dataset.tags.split('|').indexOf(tag) !== -1;
      for (var i = 0; ok && i < words.length; i++) ok = c.dataset.search.indexOf(words[i]) !== -1;
      c.hidden = !ok;
      if (ok) shown++;
    });
    links.forEach(function (a) {
      var on = a.dataset.tag === tag, grp = a.closest('.grp');
      a.classList.toggle('on', on);
      if (on) grp.open = true;   // make sure the active filter's group is visible
    });
    Array.prototype.forEach.call(menus.querySelectorAll('.grp'), function (g) {
      g.classList.toggle('has-on', !!g.querySelector('a.on'));
    });
    note.innerHTML = '';
    if (tag || q) {
      note.textContent = [tag, q ? '“' + q + '”' : ''].filter(Boolean).join(' + ') + ': ' + shown + (shown === 1 ? ' paper' : ' papers');
      var b = document.createElement('button');
      b.type = 'button';
      b.textContent = 'Show all';
      b.onclick = function () { box.value = ''; history.replaceState(null, '', location.pathname); apply(); };
      note.appendChild(b);
    }
  }
  menus.addEventListener('click', function (e) {
    var a = e.target.closest('a[data-tag]');
    if (!a) return;
    e.preventDefault();
    if (a.dataset.tag === current()) history.replaceState(null, '', location.pathname);
    else history.replaceState(null, '', '#tag=' + encodeURIComponent(a.dataset.tag));
    apply();
    // bring the top of the list into view if it has scrolled away
    var res = document.getElementById('results');
    if (res.getBoundingClientRect().top < 0 || res.getBoundingClientRect().top > window.innerHeight * 0.6) res.scrollIntoView();
  });
  box.addEventListener('input', apply);
  window.addEventListener('hashchange', apply);
  apply();
})();
