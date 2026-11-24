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
// The search box narrows the list further: every term typed must appear in the
// paper's title, reference, co-authors, tags or abstract. Terms also match their
// synonyms (SYNONYMS below), and a word found nowhere is treated as a typo and
// matched to the closest words instead.
(function () {
  var menus = document.querySelector('.tagmenus');
  if (!menus) return;

  // Each line is a group of interchangeable search terms (lower case).
  var SYNONYMS = [
    ['defi', 'decentralized finance', 'decentralised finance'],
    ['dex', 'dexes', 'decentralized exchange', 'decentralised exchange'],
    ['cex', 'centralized exchange', 'centralised exchange', 'crypto exchange'],
    ['amm', 'amms', 'automated market mak'],
    ['lp', 'lps', 'liquidity provider', 'liquidity provision'],
    ['jit', 'just-in-time', 'just in time'],
    ['m&a', 'm&as', 'merger', 'mergers', 'acquisition', 'acquisitions', 'takeover', 'takeovers'],
    ['ipo', 'ipos', 'initial public offering', 'going public', 'going-public'],
    ['seo', 'seos', 'seasoned equity'],
    ['ico', 'icos', 'initial coin offering', 'token sale', 'token offering'],
    ['vc', 'venture capital'],
    ['private equity', 'buyout'],
    ['llm', 'llms', 'large language model', 'language model', 'gpt'],
    ['ai', 'artificial intelligence', 'machine learning'],
    ['blockchain', 'distributed ledger', 'dlt'],
    ['crypto', 'cryptocurrency', 'cryptocurrencies', 'digital asset', 'digital assets'],
    ['r&d', 'research and development'],
    ['buyback', 'buybacks', 'repurchase', 'share repurchase'],
    ['bankruptcy', 'default', 'insolvency', 'financial distress'],
    ['leverage', 'capital structure'],
    ['convertible', 'convertibles', 'convertible debt', 'convertible bond'],
    ['competition', 'competitive', 'rivalry', 'rivals'],
    ['automation', 'robot', 'robots'],
    ['supply chain', 'supplier', 'suppliers'],
    ['trade credit', 'accounts payable', 'supplier financing'],
    ['soccer', 'football'],
    ['hack', 'hacks', 'exploit', 'security breach'],
    ['wash trading', 'volume manipulation', 'fake volume', 'inflated trading volume'],
    ['experiment', 'experimental', 'laboratory', 'lab'],
    ['theory', 'theoretical'],
    ['empirical', 'empirics'],
    ['working paper', 'wp', 'draft', 'unpublished'],
    ['patent', 'patents', 'innovation'],
    ['diversification', 'conglomerate', 'diversified']
  ];
  var ESC = /[.*+?^${}()|[\]\\]/g;

  // Damerau-Levenshtein distance, stopping early once it exceeds max.
  function distance(a, b, max) {
    if (Math.abs(a.length - b.length) > max) return max + 1;
    var prev2 = null, prev = [], cur, i, j;
    for (j = 0; j <= b.length; j++) prev[j] = j;
    for (i = 1; i <= a.length; i++) {
      cur = [i];
      var best = i;
      for (j = 1; j <= b.length; j++) {
        var cost = a.charAt(i - 1) === b.charAt(j - 1) ? 0 : 1;
        cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost);
        if (prev2 && i > 1 && j > 1 && a.charAt(i - 1) === b.charAt(j - 2) && a.charAt(i - 2) === b.charAt(j - 1))
          cur[j] = Math.min(cur[j], prev2[j - 2] + 1);
        if (cur[j] < best) best = cur[j];
      }
      if (best > max) return max + 1;
      prev2 = prev; prev = cur;
    }
    return prev[b.length];
  }
  // One spelling of a term against one card: short terms match the start of a word, longer ones anywhere.
  function has(card, alt) {
    if (alt.length > 3 || alt.indexOf(' ') !== -1) return card.text.indexOf(alt) !== -1;
    for (var i = 0; i < card.words.length; i++) if (card.words[i].lastIndexOf(alt, 0) === 0) return true;
    return false;
  }
  function close(card, word) {          // typo tolerance: 1 slip, 2 for long words
    var max = word.length >= 9 ? 2 : 1;
    for (var i = 0; i < card.words.length; i++) {
      var w = card.words[i];
      if (w.length < 4) continue;
      if (distance(word, w, max) <= max) return true;
      if (w.length > word.length && distance(word, w.slice(0, word.length), max) <= max) return true;
    }
    return false;
  }
  // Split what was typed into terms; each term lists the spellings that satisfy it.
  function parse(q, index) {
    var terms = [], rest = ' ' + q.toLowerCase().replace(/\s+/g, ' ').trim() + ' ';
    var phrases = [];
    SYNONYMS.forEach(function (g) { g.forEach(function (p) { phrases.push([p, g]); }); });
    phrases.sort(function (a, b) { return b[0].length - a[0].length; });
    phrases.forEach(function (pg) {
      var re = new RegExp(' ' + pg[0].replace(ESC, '\\$&') + '(?= )');
      if (re.test(rest)) { rest = rest.replace(re, ' '); terms.push({ alts: pg[1] }); }
    });
    rest.split(' ').filter(Boolean).forEach(function (w) {
      var known = index.some(function (c) { return has(c, w); });
      terms.push({ alts: [w], fuzzy: !known && w.length >= 4 });
    });
    return terms;
  }
  var cards = Array.prototype.slice.call(document.querySelectorAll('.card'));
  var links = Array.prototype.slice.call(menus.querySelectorAll('a[data-tag]'));
  var note = document.getElementById('filter-note');
  var box = document.getElementById('paper-search');
  var index = cards.map(function (c) {   // searchable text of each card, and its distinct words
    var text = c.dataset.search, seen = {}, words = [];
    text.split(/[^a-z0-9&-]+/).forEach(function (w) { if (w && !seen[w]) { seen[w] = 1; words.push(w); } });
    return { text: text, words: words };
  });

  function current() {
    var m = /^#tag=(.*)$/.exec(location.hash);
    return m ? decodeURIComponent(m[1]) : '';
  }
  function apply() {
    var tag = current(), shown = 0;
    var q = box.value.trim(), terms = q ? parse(q, index) : [];
    var approx = terms.some(function (t) { return t.fuzzy; });
    cards.forEach(function (c, n) {
      var ok = !tag || c.dataset.tags.split('|').indexOf(tag) !== -1, card = index[n];
      for (var i = 0; ok && i < terms.length; i++) {
        var t = terms[i];
        ok = t.fuzzy ? close(card, t.alts[0]) : t.alts.some(function (a) { return has(card, a); });
      }
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
      note.textContent = [tag, q ? '“' + q + '”' + (approx ? ' (closest matches)' : '') : ''].filter(Boolean).join(' + ') +
        ': ' + shown + (shown === 1 ? ' paper' : ' papers');
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
