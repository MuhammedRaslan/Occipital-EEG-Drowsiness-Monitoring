"""
Automated pre-flight against the IEEE Sensors Journal requirements.

Covers every item in 03_IEEE_SENSORS_CHECKLIST.md that can be decided from the
files themselves. Items needing a LaTeX compile (page count, printed float
order), a network call (reviewer emails, Zenodo), or a human read are listed at
the end as MANUAL rather than silently passing.

There is no TeX toolchain on this machine, so bibliography and cross-reference
integrity are checked by static analysis of main.tex against references.bib --
which catches undefined citations and duplicate labels without compiling.

Usage:
    python preflight_ieee.py                       # checks submission_compact
    python preflight_ieee.py --source submission
"""

import argparse
import os
import re
import sys
import zipfile
from datetime import date

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))

ap = argparse.ArgumentParser()
ap.add_argument("--source", default="submission_compact")
args = ap.parse_args()
SRC = os.path.join(REPO, args.source)

B = chr(92) * 2                      # a literal backslash inside a regex
PASS, FAIL, WARN, MANUAL = [], [], [], []


def sec(t):
    print(f"\n{'=' * 74}\n{t}\n{'=' * 74}")


def ck(cond, ok, bad, hard=True):
    if cond:
        print(f"  PASS  {ok}")
        PASS.append(ok)
    else:
        print(f"  {'FAIL' if hard else 'WARN'}  {bad}")
        (FAIL if hard else WARN).append(bad)
    return cond


def manual(item):
    MANUAL.append(item)


tex_path = os.path.join(SRC, "main.tex")
bib_path = os.path.join(SRC, "references.bib")
tex = open(tex_path, encoding="utf-8").read()
bib = open(bib_path, encoding="utf-8").read()

# strip comments so they cannot produce false hits
tex_nc = re.sub(r"(?<!\\)%.*", "", tex)

# ======================================================================
sec("A. Manuscript file and format")
# ======================================================================
ck(re.search(B + r"documentclass\[[^\]]*journal[^\]]*\]\{IEEEtran\}", tex_nc)
   is not None,
   "IEEEtran journal class (double-column)",
   "not using the IEEEtran double-column journal class")

ck("onecolumn" not in tex_nc and "draftcls" not in tex_nc,
   "no onecolumn/draftcls leftovers",
   "documentclass still carries onecolumn or draftcls")

m = re.search(B + r"def" + B + r"revmode\{(\w+)\}", tex_nc)
ck(m and m.group(1) == "clean",
   f"revision markup off (revmode={m.group(1) if m else '?'})",
   f"revmode={m.group(1) if m else 'missing'} -- submission PDF would carry "
   "highlighted additions and struck-through deletions")

ck("[TODO]" not in tex and "TODO" not in tex_nc,
   "no TODO placeholders left in the manuscript",
   "a TODO placeholder is still in main.tex")

# ======================================================================
sec("B. Manuscript content")
# ======================================================================
abst = re.search(B + r"begin\{abstract\}(.*?)" + B + r"end\{abstract\}", tex, re.S)
if abst:
    a = re.sub(B + r"del\{[^{}]*\}", "", abst.group(1))
    n = len(re.sub(B + r"[a-zA-Z]+|[{}]", " ", a).split())
    ck(150 <= n <= 250, f"abstract length {n} words (150-250)",
       f"abstract is {n} words, outside the 150-250 guidance", hard=False)
    ck(B.replace(chr(92) * 2, chr(92)) + "cite" not in abst.group(1)
       and "\\cite" not in abst.group(1),
       "abstract carries no citations",
       "abstract contains a citation; IEEE wants it self-contained")

ck(re.search(B + r"begin\{IEEEkeywords\}", tex_nc) is not None,
   "index terms present", "no IEEEkeywords block")

# --- submission date -------------------------------------------------------
# Two dates are authored and must agree with each other and with the day the
# paper is actually sent: the \thanks{Manuscript received ...} line, which IEEE
# production overwrites at acceptance but an editor still reads, and the cover
# letter's own date, which is a letter dated to the day it is sent.
#
# The date in declarations.md is deliberately NOT checked here -- it records
# when the funding position was confirmed, which is a past event and must not
# be moved forward.
MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}


def parse_dates():
    out = {}
    m = re.search(r"Manuscript received (\w+)\s+(\d{1,2}),\s*(\d{4})", tex_nc)
    if m and m.group(1) in MONTHS:
        out["main.tex"] = date(int(m.group(3)), MONTHS[m.group(1)],
                               int(m.group(2)))
    cl = os.path.join(SRC, "cover_letter.md")
    if os.path.isfile(cl):
        m = re.search(r"\*\*Date:\*\*\s*(\d{1,2})\s+(\w+)\s+(\d{4})",
                      open(cl, encoding="utf-8").read())
        if m and m.group(2) in MONTHS:
            out["cover_letter.md"] = date(int(m.group(3)), MONTHS[m.group(2)],
                                          int(m.group(1)))
    return out


dates = parse_dates()
ck(len(dates) == 2, f"submission date found in both files ({len(dates)}/2)",
   f"could not parse the submission date from {2 - len(dates)} file(s); "
   f"found {sorted(dates)}", hard=False)
if len(dates) == 2:
    vals = set(dates.values())
    ck(len(vals) == 1,
       f"manuscript and cover letter agree on {sorted(vals)[0].isoformat()}",
       f"date mismatch: " + ", ".join(f"{k}={v.isoformat()}"
                                      for k, v in sorted(dates.items())))
    if vals:
        age = (date.today() - sorted(vals)[0]).days
        ck(age <= 7,
           f"submission date is {age} day(s) old, still current",
           f"submission date is {sorted(vals)[0].isoformat()}, {age} days ago "
           f"-- set it to the day you actually submit "
           f"(main.tex \\thanks, and cover_letter.md **Date:**), then rebuild",
           hard=False)

# citation integrity -- what a compile would report as "?"
cited = set()
for g in re.findall(r"cite\{([^}]+)\}", tex_nc):
    cited.update(x.strip() for x in g.split(",") if x.strip())
defined = set(re.findall(r"^@\w+\{([^,]+),", bib, re.M))
missing = sorted(cited - defined)
ck(not missing, f"all {len(cited)} citations resolve in references.bib",
   f"undefined citations (would print as '?'): {missing}")
unused = sorted(defined - cited)
ck(not unused, f"no unused bib entries ({len(defined)} defined)",
   f"{len(unused)} bib entries never cited: {unused}", hard=False)

# label / ref integrity
labels = re.findall(r"" + B + r"label\{([^}]+)\}", tex_nc)
dups = sorted({x for x in labels if labels.count(x) > 1})
ck(not dups, f"all {len(labels)} labels unique", f"duplicate labels: {dups}")
refs = set(re.findall(r"" + B + r"ref\{([^}]+)\}", tex_nc))
dangling = sorted(refs - set(labels))
ck(not dangling, f"all {len(refs)} \\ref targets exist",
   f"\\ref to undefined labels: {dangling}")

# hard-coded float numbers
hard_nums = re.findall(r"(?:Fig(?:ure)?\.?|Table)~?\s*(?:[0-9]+|[IVX]{1,5})\b", tex_nc)
ck(not hard_nums, "no hard-coded figure/table numbers in the prose",
   f"hard-coded float numbers found: {set(hard_nums)}")

# citation order = definition order
def order(kind):
    defs = [m.group(1) for m in
            re.finditer(r"" + B + r"label\{(" + kind + r":[^}]+)\}", tex_nc)]
    firsts = []
    for lab in defs:
        m = re.search(r"" + B + r"ref\{" + re.escape(lab) + r"\}", tex_nc)
        firsts.append(m.start() if m else 10 ** 9)
    return defs, firsts == sorted(firsts)

for kind, name in (("fig", "figures"), ("tab", "tables")):
    defs, ok = order(kind)
    ck(ok, f"{len(defs)} {name} first referenced in definition order",
       f"{name} are referenced out of order in the source")

# ======================================================================
sec("C. Figures")
# ======================================================================
COL_IN, TEXT_IN, MIN_DPI = 3.5, 7.16, 300
inc = re.findall(r"includegraphics\[width=" + B + r"(\w+)\]\{([^}]+)\}", tex_nc)
ck(len(inc) == 5, f"{len(inc)} figures included",
   f"expected 5 included figures, found {len(inc)}", hard=False)


def media_box_in(path):
    """Authored width of a single-page PDF, in inches, from /MediaBox."""
    m = re.search(rb"/MediaBox\s*\[\s*([\d.+-]+)\s+[\d.+-]+\s+([\d.+-]+)\s+"
                  rb"[\d.+-]+\s*\]", open(path, "rb").read())
    return None if not m else (float(m.group(2)) - float(m.group(1))) / 72.0


for i, (width, fname) in enumerate(inc, start=1):
    p = os.path.join(SRC, "figures", fname)
    if not os.path.isfile(p):
        ck(False, "", f"Fig. {i}: file missing -- {fname}")
        continue
    printed = TEXT_IN if width == "textwidth" else COL_IN

    if fname.lower().endswith(".pdf"):
        # Vector. Counting pixels is meaningless, so the resolution test is
        # replaced by two that are not: the fonts must be embedded and must not
        # be Type 3 (a standard IEEE production reject), and the authored width
        # must be close to the printed width, because the ratio between them
        # multiplies every font size in the figure.
        blob = open(p, "rb").read()
        ck(b"/Type3" not in blob and b"/FontFile" in blob,
           f"Fig. {i} {fname}: vector, fonts embedded, no Type 3",
           f"Fig. {i} {fname}: Type-3 or unembedded fonts -- set "
           f"matplotlib.rcParams['pdf.fonttype'] = 42 and re-render")
        box = media_box_in(p)
        if ck(box is not None, f"Fig. {i} {fname}: /MediaBox readable",
              f"Fig. {i} {fname}: no readable /MediaBox"):
            scale = printed / box
            ck(0.70 <= scale <= 1.10,
               f"Fig. {i} {fname}: authored {box:.2f}in, printed "
               f"{printed:.2f}in = {scale:.2f}x",
               f"Fig. {i} {fname}: authored {box:.2f}in but printed "
               f"{printed:.2f}in, a {scale:.2f}x rescale of every font in it")
    else:
        im = Image.open(p)
        eff = im.size[0] / printed
        ck(eff >= MIN_DPI,
           f"Fig. {i} {fname}: {im.size[0]}px at {printed:.2f}in = {eff:.0f} dpi",
           f"Fig. {i} {fname}: {eff:.0f} dpi at {printed:.2f}in, under {MIN_DPI}; "
           f"needs >= {int(MIN_DPI * printed)}px wide")

    ck(fname.startswith(f"fig{i}_"),
       f"Fig. {i} filename matches its printed number",
       f"Fig. {i} is named {fname}, which does not match figure {i}", hard=False)
    ck(" " not in fname, f"Fig. {i} filename has no spaces",
       f"Fig. {i} filename contains a space")

    # The Portal takes one image per figure in its own upload slots, so each
    # vector figure must have a raster twin on the same stem.
    if fname.lower().endswith(".pdf"):
        twin = os.path.join(SRC, "figures", fname[:-4] + ".png")
        if ck(os.path.isfile(twin),
              f"Fig. {i} has a PNG twin for the Portal's upload slot",
              f"Fig. {i}: no PNG twin beside {fname} for the Portal slot"):
            eff = Image.open(twin).size[0] / printed
            ck(eff >= MIN_DPI,
               f"Fig. {i} PNG twin: {eff:.0f} dpi at {printed:.2f}in",
               f"Fig. {i} PNG twin: {eff:.0f} dpi at {printed:.2f}in, "
               f"under {MIN_DPI}")

# packaged raster copies must be RGB with no alpha
pkg = os.path.join(HERE, "figures")
if os.path.isdir(pkg):
    bad = [f for f in sorted(os.listdir(pkg))
           if f.lower().endswith((".png", ".tif", ".tiff", ".jpg", ".jpeg"))
           and Image.open(os.path.join(pkg, f)).mode not in ("RGB", "L")]
    ck(not bad, "packaged figures are RGB with no alpha channel",
       f"packaged figures still carry alpha/palette: {bad}")

# ======================================================================
sec("D. Graphical abstract")
# ======================================================================
ga_dir = os.path.join(HERE, "graphical_abstract")
ga = next((os.path.join(ga_dir, f) for f in
           ("gagraphic.png", "gagraphic.jpg", "gagraphic.jpeg", "gagraphic.tif")
           if os.path.isfile(os.path.join(ga_dir, f))), None)
if ck(ga is not None, "graphical abstract present (mandatory)",
      "no gagraphic.* found -- the graphical abstract is mandatory"):
    im = Image.open(ga)
    ck(im.size == (672, 456), f"dimensions {im.size[0]}x{im.size[1]} px",
       f"dimensions {im.size[0]}x{im.size[1]}, specification is 672x456")
    kb = os.path.getsize(ga) / 1024
    ck(kb < 45, f"file size {kb:.1f} kB (< 45 kB recommended)",
       f"file size {kb:.1f} kB, over the 45 kB recommendation", hard=False)
    ck(os.path.basename(ga).startswith("gagraphic"),
       f"filename {os.path.basename(ga)}", "filename must be gagraphic.*")
    ck("A" not in im.mode, "no alpha channel", "graphical abstract has alpha")

    cap = os.path.join(ga_dir, "gagraphic_caption.txt")
    if ck(os.path.isfile(cap), "caption file present", "no gagraphic_caption.txt"):
        body = [l for l in open(cap, encoding="utf-8").read().splitlines()
                if l.strip() and not l.strip().startswith("[")]
        w = len(" ".join(body).split())
        ck(w <= 30, f"caption {w} words (<= 30)",
           f"caption is {w} words, over the 30-word limit")

    # Legibility. NOTE: this measures the ink extent of each row band, which is
    # not the same as point size -- a word with a descender ("drowsy") measures
    # taller than the same-size word without one ("awake"). Treat it as a rough
    # tier indicator, not a font-size readout.
    #
    # The current graphic was reviewed against this and ACCEPTED as-is on
    # 2026-08-05: its small-text tier sits at roughly 6-7 px cap height, which
    # is small but legible, and it meets every mandatory IEEE requirement. This
    # stays a warning so a future re-export is still measured.
    a = np.asarray(im.convert("RGB")).astype(int)
    dark = (a.min(axis=2) < 150)
    runs, start, heights = [], None, []
    rows = dark.any(axis=1)
    for i, d in enumerate(rows):
        if d and start is None:
            start = i
        elif not d and start is not None:
            runs.append(i - start); start = None
    heights = [h for h in runs if 3 <= h <= 60]
    tiny = [h for h in heights if h < 9]
    ck(not tiny,
       f"all {len(heights)} text bands >= 9 px of ink",
       f"{len(tiny)} of {len(heights)} text bands under 9 px of ink "
       f"(smallest {min(heights) if heights else 0} px) -- ink extent, not "
       f"point size; reviewed and ACCEPTED as-is 2026-08-05",
       hard=False)

# ======================================================================
sec("E. Supplementary")
# ======================================================================
sup = os.path.join(HERE, "supplementary")
rd = os.path.join(sup, "README.txt")
if ck(os.path.isfile(rd), "README present in TXT (IEEE requires PDF or TXT)",
      "supplementary README missing, or not in PDF/TXT"):
    r = open(rd, encoding="utf-8").read().lower()
    need = {"contents": "contents", "size": "size", "platform": "platform",
            "setup": "setup", "run": "run", "expected output": "expected output",
            "contact": "contact"}
    absent = [k for k, v in need.items() if v not in r]
    ck(not absent, "README covers all seven required sections",
       f"README missing required sections: {absent}")

gif = os.path.join(sup, "demo_v20.gif")
if os.path.isfile(gif):
    mb = os.path.getsize(gif) / 1048576
    ck(mb <= 100, f"multimedia {mb:.1f} MB (<= 100 MB)",
       f"multimedia is {mb:.1f} MB, over the 100 MB limit")

z = os.path.join(sup, "supplementary_code_and_results.zip")
if os.path.isfile(z):
    names = zipfile.ZipFile(z).namelist()
    ck(not any(" " in n for n in names), f"zip has {len(names)} files, no spaces",
       "some filenames inside the zip contain spaces")

# ======================================================================
sec("F. Package totals")
# ======================================================================
total = sum(os.path.getsize(os.path.join(dp, f))
            for dp, _, fs in os.walk(HERE) for f in fs
            if not f.endswith((".py", ".md", ".npz")) and "_src" not in f)
ck(total / 1048576 <= 40, f"upload payload {total / 1048576:.1f} MB (<= 40 MB)",
   f"upload payload {total / 1048576:.1f} MB, over the 40 MB portal cap")

for f in ("portal_text/cover_letter.txt", "portal_text/declarations.txt",
          "portal_text/suggested_reviewers.txt"):
    ck(os.path.isfile(os.path.join(HERE, f)), f"{f} present", f"{f} missing")

decl = os.path.join(HERE, "portal_text", "declarations.txt")
if os.path.isfile(decl):
    d = open(decl, encoding="utf-8").read()
    for n, kw in ((1, "contribution"), (2, "Conflict"), (3, "Funding"),
                  (4, "availability"), (5, "Ethics"), (6, "AI-assistance")):
        ck(kw.lower() in d.lower(), f"declarations section {n} ({kw}) present",
           f"declarations section {n} ({kw}) missing")

# ======================================================================
for item in (
    "Page count: 11, accepted at $525 overlength on 2026-08-06 after measuring "
    "that 8 pages is unreachable (removing all 15 floats still leaves 9). "
    "build_manuscript.py now gates on growth past 11, not on the 8-page limit",
    "Confirm tables PRINT in citation order -- six are full-width table* floats "
    "that IEEEtran numbers on placement (build_manuscript.py reports this)",
    "Confirm the PDF and the source archive match exactly (build_manuscript.py "
    "writes both from one compile, so this holds unless they are built apart)",
    "Select the mandatory category from the journal's editorial keyword list",
    "Verify each suggested reviewer's email, 24 h before submitting",
    "Make the GitHub repository public and push the paper-submission-v1 tag",
    "Mint the Zenodo DOI and add it to the Reproducibility section",
    "Run iThenticate; overall similarity < 20 %",
    "Spell-check, and read the compiled PDF cold twice",
):
    manual(item)

sec("SUMMARY")
print(f"  passed : {len(PASS)}")
print(f"  warned : {len(WARN)}")
print(f"  failed : {len(FAIL)}")
for f in FAIL:
    print(f"    FAIL  {f}")
for w in WARN:
    print(f"    WARN  {w}")
print(f"\n  cannot be automated ({len(MANUAL)}):")
for m in MANUAL:
    print(f"    - {m}")

sys.exit(1 if FAIL else 0)
