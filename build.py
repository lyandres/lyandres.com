#!/usr/bin/env python3
"""Build lyandres.com from data/site.json and data/papers.json.

    python3 build.py

Writes index.html, research.html and post/<slug>.html (one page per paper)
next to this file. Everything else (assets/, papers/, cv.pdf) is served as-is.
No dependencies beyond Python 3.
"""
import html
import json
import os
import re
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
site = json.load(open(os.path.join(ROOT, "data", "site.json"), encoding="utf-8"))
papers = json.load(open(os.path.join(ROOT, "data", "papers.json"), encoding="utf-8"))
esc = html.escape


# ---------- ordering ----------
def pub_key(p):
    # forthcoming first, then newest first
    if p["detail"] == "forthcoming":
        return (0, 0, 0, p["order"])
    return (1, -(p["year"] or 0), -(p["month"] or 0), p["order"])


working = sorted([p for p in papers if p["status"] == "working"], key=lambda p: p["order"])
published = sorted([p for p in papers if p["status"] == "published"], key=pub_key)


# ---------- placeholder PDFs for papers without a real file yet ----------
def placeholder_pdf(path, title):
    def t(s):
        s = s.encode("latin-1", "replace").decode("latin-1")
        return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")

    words, lines, cur = title.split(), [], ""
    for w in words:
        if len(cur) + len(w) > 52:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    ops = ["BT /F1 20 Tf 72 700 Td 26 TL"]
    ops += ["(%s) Tj T*" % t(l) for l in lines]
    ops += ["/F2 13 Tf 20 TL T*", "(%s) Tj T*" % t(site["name"]), "T*",
            "(Placeholder file. The current draft will be posted here shortly.) Tj T*",
            "(For a copy, please write to %s) Tj" % t(site["email"]), "ET"]
    stream = zlib.compress("\n".join(ops).encode("latin-1"))
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>",
        b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman /Encoding /WinAnsiEncoding >>",
    ]
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offs)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    open(path, "wb").write(out)


# (placeholder_pdf() is no longer called: papers without a file show "PDF coming soon".)


# ---------- shared pieces ----------
LINKEDIN = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5zM3 9.75h4v11.25H3zM9.5 9.75h3.8v1.6h.05c.53-1 1.83-1.9 3.75-1.9 4 0 4.4 2.4 4.4 5.6V21h-4v-5.2c0-1.3-.03-2.9-1.9-2.9s-2.1 1.4-2.1 2.8V21h-4z"/></svg>')
PDF_ICON = ('<svg viewBox="0 0 34 40" aria-hidden="true"><path d="M3 1h19l9 9v29H3z" fill="#fff" stroke="#333" stroke-width="1.5"/>'
            '<path d="M22 1v9h9" fill="none" stroke="#333" stroke-width="1.5"/>'
            '<rect x="0" y="20" width="24" height="11" fill="#e2574c"/>'
            '<text x="12" y="28.5" font-family="Arial,sans-serif" font-size="8" font-weight="700" fill="#fff" text-anchor="middle">PDF</text></svg>')
THEME_ICON = ('<svg class="moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5a8.5 8.5 0 1 0 11 11z"/></svg>'
              '<svg class="sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.5"/>'
              '<path d="M12 1.5v3M12 19.5v3M1.5 12h3M19.5 12h3M4.6 4.6l2.1 2.1M17.3 17.3l2.1 2.1M4.6 19.4l2.1-2.1M17.3 6.7l2.1-2.1" '
              'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>')
profiles = {x["label"]: x["url"] for x in site["profiles"]}


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def stamp(rel):
    """File's modification time, added to image/PDF links so a replaced file is never shown from cache."""
    return "%d" % os.path.getmtime(os.path.join(ROOT, rel))


def journal_cover(p, base=""):
    """<img> of the journal's cover for a published paper, or '' if there is none."""
    logo = "assets/journals/%s.jpg" % slugify(p["journal"]) if p["journal"] else ""
    if p["status"] == "published" and logo and os.path.exists(os.path.join(ROOT, logo)):
        return '<img class="journal-cover" src="%s%s?v=%s" alt="%s" title="%s" loading="lazy">' % (
            base, logo, stamp(logo), esc(p["journal"]), esc(p["journal"]))
    if p["status"] == "working":
        return '<span class="journal-cover wp-cover" title="Working paper" aria-label="Working paper">WP</span>'
    return ""


def thumbs(p, base=""):
    """Light and dark word clouds; CSS shows the one matching the theme."""
    src = "%sassets/thumbs/%s" % (base, p["slug"])
    v = stamp("assets/thumbs/%s.webp" % p["slug"])
    return ('<img class="wc-light" src="%s.webp?v=%s" alt="" width="260" height="195" loading="lazy">'
            '<img class="wc-dark" src="%s-dark.webp?v=%s" alt="" width="260" height="195" loading="lazy">' % (src, v, src, v))


# Changes whenever the stylesheet or script changes, so browsers never show a stale copy.
ASSET_V = "%d" % max(os.path.getmtime(os.path.join(ROOT, "assets", f)) for f in ("style.css", "site.js", "favicon.svg", "favicon-64.png"))


def page(title, desc, active, body, base=""):
    def nav(href, label, key):
        return '<li><a href="%s%s"%s>%s</a></li>' % (base, href, ' class="active"' if key == active else "", label)

    sub = "".join('<li><a href="%s">%s (%s)</a></li>' % (esc(l["url"]), esc(l["menu"]), esc(l["short"]))
                  for l in site["links"])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{site['domain']}/assets/portrait.jpg">
<script>try{{var t=localStorage.getItem('theme');if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
<link rel="icon" href="{base}assets/favicon.svg?v={ASSET_V}" type="image/svg+xml">
<link rel="icon" href="{base}assets/favicon-64.png?v={ASSET_V}" type="image/png" sizes="64x64">
<link rel="apple-touch-icon" href="{base}assets/apple-touch-icon.png?v={ASSET_V}">
<link rel="stylesheet" href="{base}assets/style.css?v={ASSET_V}">
</head>
<body>
<div class="page">
<header class="site-header">
  <a class="brand" href="{base}index.html">{esc(site['name'])}</a>
  <ul class="nav">
    {nav('index.html', 'Home', 'home')}
    <li><a href="{base}cv.pdf" target="_blank" rel="noopener">CV</a></li>
    {nav('research.html', 'Research', 'research')}
    <li><span tabindex="0">Useful links</span><ul class="sub">{sub}</ul></li>
  </ul>
  <button class="theme-toggle" type="button" id="theme-toggle" aria-label="Switch between light and dark theme" title="Light / dark theme">{THEME_ICON}</button>
</header>
<main>
{body}
</main>
<footer class="site-footer">
  <span class="copy">&copy; {esc(site['name'])}</span>
  <a href="{base}cv.pdf" target="_blank" rel="noopener">CV</a>
  <a href="{esc(profiles['Google Scholar'])}">Google Scholar</a>
  <a href="{esc(profiles['SSRN'])}">SSRN</a>
  <a href="{esc(profiles['LinkedIn'])}" aria-label="LinkedIn">{LINKEDIN}</a>
</footer>
</div>
<script src="{base}assets/site.js?v={ASSET_V}"></script>
</body>
</html>
"""


def ref_text(p):
    """Line under the title, as on the old site: journal reference or 'working paper'."""
    if p["journal"]:
        return "%s%s" % (p["journal"], (", forthcoming" if p["detail"] == "forthcoming" else " " + p["detail"]))
    if p["status"] == "working":
        return "working paper" + (", " + p["note"] if p.get("note") else "")
    return ""


def all_tags(p):
    status = "Published" if p["status"] == "published" else "Working"
    return [status] + p["method"] + p["area"] + p["topics"] + p["coauthors"]


def card_tags(p):
    """Everything a card can be filtered by: the tags plus the journal (or 'Working paper')."""
    return all_tags(p) + [p["journal"] or "Working paper"]


def search_text(p):
    return " ".join([p["title"], ref_text(p), p["abstract"]] + card_tags(p)).lower()


# ---------- home ----------
news = "".join("<li><b>%s:</b> %s</li>" % (esc(n["date"]), n["text"]) for n in site["news"])
home = f"""
<section class="hero">
  <img src="assets/portrait.jpg" alt="Portrait of {esc(site['name'])}" width="220" height="282">
  <div>
    <h1>{esc(site['name'])}</h1>
    <p>{'<br>'.join(esc(r) for r in site['roles'])}</p>
    <p>{'<br>'.join(esc(a) for a in site['affiliation'])}</p>
  </div>
  <p class="contact">Phone: <a href="tel:{site['phone'].replace(' ', '')}">{esc(site['phone'])}</a><br>
  Email: <a href="mailto:{site['email']}">{site['email']}</a></p>
</section>
<div class="columns">
  <section class="bio">
    <h2 class="big">Bio</h2>
    <p>{esc(' '.join(site['bio']))}</p>
  </section>
  <section>
    <h2 class="big">Latest News</h2>
    <ul class="news">{news}</ul>
  </section>
</div>
"""
desc = "%s is %s at the %s, %s." % (site["name"], site["roles"][0], site["affiliation"][0], site["affiliation"][1])
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(
    page("%s - %s" % (site["name"], site["roles"][0]), desc, "home", home))


# ---------- research ----------
def menu(title, values, cls=""):
    def count(v):
        n = sum(1 for p in papers if v in card_tags(p))
        return "" if (cls == "co" and n == 1) else " (%d)" % n  # old site: co-author counts only above 1

    items = "".join('<li><a href="#tag=%s" data-tag="%s">%s%s</a></li>' % (esc(v), esc(v), esc(v), count(v))
                    for v in values)
    # collapsed by default; site.js opens the group that holds the active filter
    return '<details class="grp %s"><summary>%s</summary><ul>%s</ul></details>' % (cls, title, items)


def uniq(key, sort=None):
    vals = {v for p in papers for v in p[key]}
    return sorted(vals, key=sort or str.lower)


AREAS = ["Corporate finance", "Asset pricing", "Industrial org", "Blockchain/crypto"]
METHODS = ["Theory", "Empirics", "Experimental", "Editorial"]
journals = sorted({p["journal"] for p in papers if p["journal"]}, key=str.lower) + ["Working paper"]
areas = [a for a in AREAS if a in uniq("area")] + [a for a in uniq("area") if a not in AREAS]
methods = [m for m in METHODS if m in uniq("method")] + [m for m in uniq("method") if m not in METHODS]
cards = "".join(f"""<a class="card" href="post/{p['slug']}.html" data-tags="{esc('|'.join(card_tags(p)))}" data-search="{esc(search_text(p))}">
  {thumbs(p)}
  <div class="jc">{journal_cover(p)}</div>
  <div class="txt"><h3>{esc(p['title'])}</h3><p>{esc(ref_text(p))}</p></div>
</a>
""" for p in working + published)   # working papers first, then published: forthcoming, then newest first
research = f"""
<h1 class="sr-only">Research</h1>
<div class="research">
  <aside class="tagmenus">
    <label class="search"><span class="sr-only">Search papers</span>
      <input type="search" id="paper-search" placeholder="Search papers" autocomplete="off"></label>
    {menu('Area', areas)}
    {menu('Method', methods)}
    {menu('Journal', journals)}
    {menu('Status', ['Published', 'Working'])}
    {menu('Topic', uniq('topics'))}
    {menu('Co-authors', uniq('coauthors', sort=lambda n: n.split()[-1].lower()), 'co')}
  </aside>
  <div class="results" id="results">
    <p class="filter-note" id="filter-note"></p>
    <div class="cards">
{cards}    </div>
  </div>
</div>
"""
open(os.path.join(ROOT, "research.html"), "w", encoding="utf-8").write(
    page("RESEARCH | %s" % site["name"], "Published and working papers by %s." % site["name"], "research", research))


# ---------- one page per paper ----------
os.makedirs(os.path.join(ROOT, "post"), exist_ok=True)
for p in papers:
    meta = []
    if p["coauthors"]:
        meta.append("with " + ", ".join(esc(c) for c in p["coauthors"]))
    if ref_text(p):
        if p["journal"]:
            rest = ", forthcoming" if p["detail"] == "forthcoming" else " " + esc(p["detail"])
            meta.append("<em>%s</em>%s" % (esc(p["journal"]), rest))
        else:
            meta.append(esc(ref_text(p)))
    file_box = '<div class="file soon">%s<div><b>PDF coming soon</b></div></div>' % PDF_ICON
    if p["pdf"]:
        size = os.path.getsize(os.path.join(ROOT, p["pdf"]))
        nice = "%.2fMB" % (size / 1e6) if size >= 1e6 else "%dKB" % round(size / 1e3)
        file_box = '<a class="file" href="../%s?v=%s">%s<div><b>%s</b><span>Download PDF &bull; %s</span></div></a>' % (
            esc(p["pdf"]), stamp(p["pdf"]), PDF_ICON, esc(p["title"]), nice)
    cover = journal_cover(p, "../")
    tags = "".join('<a href="../research.html#tag=%s">%s</a>' % (esc(t), esc(t))
                   for t in all_tags(p) + ([p["journal"]] if p["journal"] else []))
    body = f"""
<article class="post">
  <a class="back" href="../research.html">&larr; All research</a>
  <div class="post-head">
    <div>
      <h1>{esc(p['title'])}</h1>
      <p class="meta">{'<br>'.join(meta)}</p>
    </div>
    {cover}
  </div>
  {('<p class="abstract">%s</p>' % esc(p['abstract'])) if p['abstract'] else ''}
  {file_box}
  <div class="tags">Tags: {tags}</div>
</article>
"""
    open(os.path.join(ROOT, "post", p["slug"] + ".html"), "w", encoding="utf-8").write(
        page("%s | %s" % (p["title"], site["name"]),
             p["abstract"][:200] or "%s, by %s%s." % (p["title"], site["name"],
                                                      (" with " + ", ".join(p["coauthors"])) if p["coauthors"] else ""),
             "research", body, base="../"))


# ---------- 404 page, sitemap, robots ----------
open(os.path.join(ROOT, "404.html"), "w", encoding="utf-8").write(page(
    "Page not found | %s" % site["name"], "Page not found.", "",
    '<article class="post"><h1>Page not found</h1><p class="abstract">The page you are looking for does not exist. '
    'Try the <a href="/index.html">home page</a> or the <a href="/research.html">research list</a>.</p></article>',
    base="/"))
urls = ["", "research.html"] + ["post/%s.html" % p["slug"] for p in papers]
open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join("  <url><loc>%s/%s</loc></url>\n" % (site["domain"], u) for u in urls) + "</urlset>\n")
open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8").write(
    "User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % site["domain"])

print("Built index.html, research.html and %d paper pages (%d published, %d working)" % (
    len(papers), len(published), len(working)))
