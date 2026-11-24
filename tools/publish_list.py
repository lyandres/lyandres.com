#!/usr/bin/env python3
"""Print every file the built site actually uses (one path per line).

Only these files are published; drafts, old copies and leftovers in the folder are not.
"""
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
papers = json.load(open("data/papers.json", encoding="utf-8"))
pages = ["index.html", "research.html", "404.html"] + ["post/%s.html" % p["slug"] for p in papers]
files = set(pages) | {"sitemap.xml", "robots.txt", "cv.pdf", "CNAME", ".nojekyll", ".gitignore", "README.md",
                      "favicon.ico", "build.py", "data/site.json", "data/papers.json", "assets/portrait.jpg"}
files |= {"tools/" + f for f in os.listdir("tools") if not f.startswith(("__", "."))}
for page in pages:
    text = open(page, encoding="utf-8").read()
    for ref in re.findall(r'(?:href|src)="([^"#]+)', text):
        ref = html.unescape(ref).split("?")[0]
        if ref.startswith(("http", "mailto:", "tel:")):
            continue
        path = ref.lstrip("/") if ref.startswith("/") else os.path.normpath(os.path.join(os.path.dirname(page), ref))
        files.add(path)
css = open("assets/style.css", encoding="utf-8").read()
files |= {os.path.normpath(os.path.join("assets", u)) for u in re.findall(r"url\(([^)]+)\)", css)}
for f in sorted(files):
    if os.path.exists(f):
        print(f)
