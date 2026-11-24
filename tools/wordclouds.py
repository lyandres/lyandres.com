#!/usr/bin/env python3
"""Generate the word-cloud thumbnails for every paper, all in one style.

    python3 tools/wordclouds.py            # all papers
    python3 tools/wordclouds.py <slug> ... # only these

For each paper it writes assets/thumbs/<slug>.webp (light theme) and
assets/thumbs/<slug>-dark.webp (dark theme), same layout in both.

Text comes from, in order: the path listed for the slug in tools/sources.json,
the paper's PDF in papers/ (unless it is a placeholder), or the title+abstract.
Needs: pillow, numpy, pypdf.
"""
import json
import os
import random
import re
import sys
import zlib
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "tools", "Montserrat.ttf")
W, H = 780, 585            # 1.5x the 520x390 display size
MAX_WORDS = 150
MAX_FONT, MIN_FONT = 112, 10
THEMES = {
    "": dict(bg="#ffffff", words=["#333333", "#333333", "#5c5c5c", "#858585", "#a8a8a8"], accent="#ff7e33"),
    "-dark": dict(bg="#1b1e23", words=["#f2f2f2", "#f2f2f2", "#c4c7cc", "#9a9ea6", "#767b84"], accent="#ff7e33"),
}

STOP = set("""
a about above after again against all also although am among an and any are as at be because been before being below
between both but by can cannot could did do does doing down during each either et al etc few for from further had has
have having he her here hers him his how however i ie eg if in into is it its itself just let may me might more most
much must my no nor not of off on once one only or other our ours out over own per same she should since so some such
than that the their theirs them then there therefore these they this those through thus to too two under until up upon
us very via was we were what when where whereas whether which while who whom why will with within without would yet you
your paper papers section sections table tables figure figures panel appendix proof lemma proposition corollary theorem
equation equations see note notes show shows shown find finds finding findings result results use uses used using given
first second third three four five six seven eight nine ten also well thus hence respectively following follows case
cases let denote denotes define defined obtain obtained consider considered assume assumed suppose implies imply
university journal review vol doi http https www org com edu pdf ssrn working electronic copy available downloaded
email mail abstract keywords jel classification introduction conclusion conclusions references acknowledgments thank
thanks comments seminar participants conference available online published elsevier informs press rights reserved
article authors author received accepted revised draft version can will may one two new many much larger smaller higher
lower high low large small different similar likely across based related due relative effect effects value values
number total mean median standard error errors deviation observations sample samples variable variables column columns
row rows model models data level levels year years time period periods term terms set since make made makes like even
still around among including include includes included controls control fixed regression regressions estimate
estimates estimated estimation coefficient coefficients significant significance statistically test tests robust
dummy equal equals zero positive negative increase increases increasing decrease decreases decreasing percent
lyandres evgeny yes wiley month months day days log logs uni
onlinelibrary oup article-pdf jlfa xxx xxxx fig figs cambridge emerald sciencedirect january february march april june
july august september october november december terms-and-conditions library aviv tel
coef ficient ficients ficant ficantly signi ciency cient cients dif ferent ference ferences ef fect fects pro
""".split())


def text_for(p, sources):
    path = sources.get(p["slug"])
    if not path and p.get("pdf") and not p.get("placeholder_pdf"):
        path = os.path.join(ROOT, p["pdf"])
    txt = ""
    if path and os.path.exists(os.path.expanduser(path)):
        try:
            from pypdf import PdfReader
            import logging
            logging.disable(logging.CRITICAL)
            reader = PdfReader(os.path.expanduser(path))
            txt = " ".join((pg.extract_text() or "") for pg in reader.pages[:60])
        except Exception as e:  # unreadable PDF: fall back to the abstract
            print("   could not read %s (%s)" % (path, e))
    source = "pdf" if len(txt) > 5000 else "abstract"
    if source == "abstract":
        txt = (p["title"] + ". ") * 3 + p["abstract"]
    return txt, source


def frequencies(txt, extra_stop=()):
    txt = txt.replace("ﬁ", "fi").replace("ﬂ", "fl").replace("ﬀ", "ff").replace("ﬃ", "ffi").replace("ﬄ", "ffl")
    txt = re.sub(r"uni[0-9A-Fa-f]{4,8}", " ", txt)    # glyph names leaked from figure fonts
    txt = txt.replace("\u200b", "")
    # publishers' download stamps and their boilerplate must not end up in the cloud
    txt = re.sub(r"Downloaded from.{0,700}?(Creative Commons License|core/terms\.?|\bon \d{1,2} \w+ \d{4}|\[\d\d/\d\d/\d{4}\])",
                 " ", txt, flags=re.S)
    txt = re.sub(r"(https?://|www\.)\S+", " ", txt)
    txt = re.sub(r"-\s*\n\s*", "", txt)          # re-join words hyphenated at line ends
    words = re.findall(r"[a-z][a-z'’\-]{2,}", txt.lower())
    words = [w.strip("-'’").replace("’s", "").replace("'s", "") for w in words]
    c = Counter(w for w in words if len(w) > 2 and w not in STOP and w not in extra_stop)
    for w in list(c):                            # fold simple plurals into the singular
        if w.endswith("s") and w in c and w[:-1] in c:   # keep whichever form is more common
            keep, drop = (w, w[:-1]) if c[w] > c[w[:-1]] else (w[:-1], w)
            c[keep] += c.pop(drop)
    return c.most_common(MAX_WORDS)


def layout(freqs, seed):
    """Place words largest first on a free spot found with an integral image."""
    rnd = random.Random(seed)
    occ = np.zeros((H, W), dtype=np.uint8)
    probe = ImageDraw.Draw(Image.new("L", (W, H)))
    top = freqs[0][1]
    placed, size = [], MAX_FONT
    for i, (word, n) in enumerate(freqs):
        size = min(size, int(MAX_FONT * (n / top) ** 0.55) + 4)
        vertical = rnd.random() < 0.12 and len(word) < 12
        while size >= MIN_FONT:
            font = ImageFont.truetype(FONT, size)
            font.set_variation_by_name("SemiBold")
            l, t, r, b = probe.textbbox((0, 0), word, font=font)
            bw, bh = r - l + 5, b - t + 5
            if vertical:
                bw, bh = bh, bw
            if bw < W and bh < H:
                ii = np.pad(occ.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
                free = ii[bh:, bw:] - ii[:-bh, bw:] - ii[bh:, :-bw] + ii[:-bh, :-bw]
                ys, xs = np.nonzero(free == 0)
                if len(ys):
                    k = rnd.randrange(len(ys))
                    x, y = int(xs[k]), int(ys[k])
                    occ[y:y + bh, x:x + bw] = 1
                    placed.append((word, size, x + 3, y + 3, l, t, vertical, i, r - l, b - t))
                    break
            size -= max(1, size // 12)
        size = max(size, MIN_FONT)   # did not fit: skip it, keep trying the smaller words
    return placed


def render(placed, theme, seed):
    rnd = random.Random(seed)
    img = Image.new("RGB", (W, H), theme["bg"])
    draw = ImageDraw.Draw(img)
    for word, size, x, y, l, t, vertical, rank, tw, th in placed:
        colour = theme["accent"] if rank in (0, 3, 7) else rnd.choice(theme["words"])
        font = ImageFont.truetype(FONT, size)
        font.set_variation_by_name("SemiBold")
        if vertical:
            tile = Image.new("L", (tw + 2, th + 2), 0)
            ImageDraw.Draw(tile).text((1 - l, 1 - t), word, font=font, fill=255)
            tile = tile.rotate(90, expand=True)
            img.paste(Image.new("RGB", tile.size, colour), (x, y), tile)
        else:
            draw.text((x - l, y - t), word, font=font, fill=colour)
    return img


def main():
    papers = json.load(open(os.path.join(ROOT, "data", "papers.json"), encoding="utf-8"))
    src_file = os.path.join(ROOT, "tools", "sources.json")
    sources = json.load(open(src_file, encoding="utf-8")) if os.path.exists(src_file) else {}
    only = set(sys.argv[1:])
    os.makedirs(os.path.join(ROOT, "assets", "thumbs"), exist_ok=True)
    for p in papers:
        if only and p["slug"] not in only:
            continue
        txt, source = text_for(p, sources)
        names = {w.lower() for a in p["coauthors"] for w in a.split()}   # keep co-author names out
        freqs = frequencies(txt, names)
        seed = zlib.crc32(p["slug"].encode())
        placed = layout(freqs, seed)
        for suffix, theme in THEMES.items():
            out = os.path.join(ROOT, "assets", "thumbs", p["slug"] + suffix + ".webp")
            render(placed, theme, seed).save(out, "WEBP", quality=82, method=6)
        print("%-8s %3d words  top: %-40s %s" % (source, len(placed), ", ".join(w for w, _ in freqs[:5]), p["slug"][:40]))


if __name__ == "__main__":
    main()
