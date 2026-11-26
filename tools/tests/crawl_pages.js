/* Loads every page of a site at three widths and reports pages wider than the screen, broken pictures, empty pages and
   pages that fail to load. Paste into the browser console on the site's homepage (or run it through the Browser pane),
   then call __startCrawl(['/css/site.css']) and, when __crawl.done is true, __report().
   It starts at the homepage and follows every link on the same site. The stylesheets named are fetched fresh first,
   because a browser's stored copy hid two fixes during the first run (November 26, 2026). */
window.__startCrawl = async function (cssFiles) {
  for (const c of cssFiles) { await fetch(c, { cache: 'reload' }); }
  window.__crawl = { done: false, pages: 0, issues: [] };
  const seen = new Set(['/']), q = ['/'], issues = window.__crawl.issues, widths = [1300, 375, 340];
  function load(url, w) {
    return new Promise(res => {
      const f = document.createElement('iframe');
      f.style.cssText = 'position:fixed;left:-5000px;top:0;width:' + w + 'px;height:900px;border:0';
      f.src = url;
      const t = setTimeout(() => res({ f, timeout: true }), 20000);
      f.onload = () => { clearTimeout(t); setTimeout(() => res({ f }), 500); };
      document.body.appendChild(f);
    });
  }
  async function one(u) {
    for (const w of widths) {
      const { f, timeout } = await load(u, w);
      try {
        const d = f.contentDocument;
        if (timeout || !d) { issues.push({ u, w, k: 'timeout' }); } else {
          const de = d.documentElement, over = de.scrollWidth - de.clientWidth;
          if (over > 1) {
            const bad = [...d.querySelectorAll('body *')].filter(e => e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflowX === 'visible').slice(-1).map(e => (e.tagName + '.' + e.className).slice(0, 50));
            issues.push({ u, w, k: 'overflow', over, el: bad[0] || '' });
          }
          const broken = [...d.images].filter(i => i.complete && i.naturalWidth === 0 && i.getAttribute('src')).map(i => i.getAttribute('src'));
          if (broken.length) issues.push({ u, w, k: 'img', broken: broken.slice(0, 3) });
          if (/404/.test(d.title) || !d.querySelector('h1,h2')) issues.push({ u, w, k: 'empty', t: d.title });
          if (w === 1300) {
            d.querySelectorAll('a[href]').forEach(a => {
              let h; try { h = new URL(a.getAttribute('href'), location.origin + u); } catch (e) { return; }
              if (h.origin !== location.origin) return;
              const p = h.pathname;
              if (!seen.has(p) && !p.startsWith('/admin') && !p.startsWith('/pagefind') && !p.startsWith('/media/') && !p.startsWith('/content/') && !/\.(xml|png|jpe?g|webp|svg|pdf|css|js|gif|docx?|xlsx?|pptx?|zip|mp4|mov|mp3)$/i.test(p)) { seen.add(p); q.push(p); }
            });
          }
        }
      } catch (e) { issues.push({ u, w, k: 'error', m: String(e).slice(0, 120) }); }
      f.remove();
    }
    window.__crawl.pages++;
  }
  async function work() { while (q.length) { await one(q.shift()); } }
  await one(q.shift());
  await Promise.all([work(), work(), work(), work(), work()]);
  window.__crawl.done = true; window.__crawl.total = seen.size;
};
window.__report = function () {
  const c = window.__crawl, by = {};
  c.issues.forEach(i => { const k = i.k + ' ' + i.w + ' ' + (i.el || ''); by[k] = (by[k] || 0) + 1; });
  return { done: c.done, pages: c.pages, total: c.total, by, list: c.issues.slice(0, 14) };
};
