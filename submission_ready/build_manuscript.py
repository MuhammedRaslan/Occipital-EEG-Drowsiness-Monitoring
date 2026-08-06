"""
Compile the manuscript with tectonic and stage the two files the IEEE Author
Portal needs: main.pdf and main_source.zip.

Tectonic is a single self-contained binary that pulls TeX packages on demand,
so there is no MiKTeX or TeX Live install behind this. If it is missing, the
script says where to get it rather than silently doing nothing.

The Portal requires the PDF and the source to match exactly, so both are
produced from one compile in one run -- never separately.

Usage:
    python build_manuscript.py [--source submission_compact]
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(HERE, "manuscript")

TECTONIC = os.path.join(os.environ.get("LOCALAPPDATA", ""), "tectonic", "tectonic.exe")
PAGE_LIMIT = 8
OVERLENGTH_USD = 175

# Overlength was measured and then decided, on 2026-08-06, rather than assumed.
#
# The 8-page figure is IEEE's charging threshold, not a submission cap. Getting
# under it is not achievable here: removing Tables III, VI and IX -- the three
# that duplicate a figure or belong in supplementary -- changes the printed
# page count by zero, removing all ten tables reaches 10 pages, and removing
# every one of the fifteen floats still leaves 9. Only deleting all floats AND
# the Limitations subsection reaches 8, which is not a paper any more.
#
# So 11 pages is accepted deliberately, at $525. This gate no longer fails on
# being over the limit -- it fails if the manuscript grows PAST the length that
# was signed off, which is the thing that could still happen by accident.
ACCEPTED_PAGES = 11

ap = argparse.ArgumentParser()
ap.add_argument("--source", default="submission_compact")
args = ap.parse_args()
SRC = os.path.join(REPO, args.source)

if not os.path.isfile(TECTONIC):
    sys.exit(f"tectonic not found at {TECTONIC}\n"
             "Get the single-binary release from\n"
             "  https://github.com/tectonic-typesetting/tectonic/releases\n"
             f"and unzip tectonic.exe into {os.path.dirname(TECTONIC)}")

os.makedirs(OUT, exist_ok=True)
build = tempfile.mkdtemp(prefix="ieee_build_")
for item in ("main.tex", "references.bib", "figures"):
    s = os.path.join(SRC, item)
    d = os.path.join(build, item)
    (shutil.copytree if os.path.isdir(s) else shutil.copy2)(s, d)

print(f"compiling {args.source}/main.tex ...")
r = subprocess.run([TECTONIC, "-X", "compile", os.path.join(build, "main.tex"),
                    "--outdir", build, "--keep-intermediates", "--keep-logs"],
                   capture_output=True, text=True)
if r.returncode != 0:
    print(r.stderr[-3000:])
    sys.exit("compile FAILED")

log = open(os.path.join(build, "main.log"), encoding="utf-8", errors="replace").read()

m = re.search(r"Output written on .*?\((\d+) pages?", log)
pages = int(m.group(1)) if m else 0

undef = len(re.findall(r"(?:Citation|Reference) `[^']+' .*? undefined", log))
overfull = [float(x) for x in re.findall(r"Overfull \\hbox \((\d+\.?\d*)pt", log)]

# float numbering and placement, straight out of the .aux
aux = open(os.path.join(build, "main.aux"), encoding="utf-8", errors="replace").read()
floats = re.findall(r"\\newlabel\{(fig|tab):([^}]+)\}\{\{([^}]*)\}\{(\d+)\}", aux)
ROMAN = {r: i for i, r in enumerate(
    ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
     "XI", "XII", "XIII", "XIV", "XV"], start=1)}


def in_order(kind):
    seq = [(ROMAN.get(n, int(n) if n.isdigit() else 0), int(pg))
           for k, _, n, pg in floats if k == kind]
    seq.sort(key=lambda t: t[0])
    pgs = [pg for _, pg in seq]
    return pgs == sorted(pgs), seq


print(f"\n  pages                 {pages}   (limit {PAGE_LIMIT}, "
      f"accepted {ACCEPTED_PAGES})")
if pages > PAGE_LIMIT:
    over = pages - PAGE_LIMIT
    print(f"  overlength            {over} page(s) -> "
          f"${over * OVERLENGTH_USD} at acceptance"
          + ("  (accepted 2026-08-06)" if pages <= ACCEPTED_PAGES else ""))
if pages > ACCEPTED_PAGES:
    print(f"  GREW                  {pages - ACCEPTED_PAGES} page(s) past the "
          f"{ACCEPTED_PAGES} signed off -> "
          f"${(pages - PAGE_LIMIT) * OVERLENGTH_USD}, not "
          f"${(ACCEPTED_PAGES - PAGE_LIMIT) * OVERLENGTH_USD}")
print(f"  undefined refs/cites  {undef}")
print(f"  overfull hboxes       {len(overfull)}"
      + (f"  (worst {max(overfull):.1f}pt)" if overfull else ""))
for kind, name in (("fig", "figures"), ("tab", "tables")):
    ok, seq = in_order(kind)
    print(f"  {name} print in order  {'yes' if ok else 'NO'}   "
          + " ".join(f"{n}->p{p}" for n, p in seq))

shutil.copy2(os.path.join(build, "main.pdf"), os.path.join(OUT, "main.pdf"))

zip_path = os.path.join(OUT, "main_source.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    z.write(os.path.join(SRC, "main.tex"), "main.tex")
    z.write(os.path.join(SRC, "references.bib"), "references.bib")
    # .bbl so the Portal can typeset the bibliography without running BibTeX
    z.write(os.path.join(build, "main.bbl"), "main.bbl")
    # Only the files main.tex actually includes. Every figure is generated as
    # both a vector PDF (what the manuscript uses) and a PNG (for the Portal's
    # per-figure upload slots); shipping the unused PNGs inside the source
    # archive would just invite a copy-editor to typeset the raster one.
    figdir = os.path.join(SRC, "figures")
    included = set(re.findall(r"includegraphics\[[^\]]*\]\{([^}]+)\}",
                              open(os.path.join(SRC, "main.tex"),
                                   encoding="utf-8").read()))
    for f in sorted(included):
        z.write(os.path.join(figdir, f), f"figures/{f}")

print(f"\n  wrote {OUT}\\main.pdf          "
      f"{os.path.getsize(os.path.join(OUT, 'main.pdf')) / 1024:.0f} kB")
print(f"  wrote {OUT}\\main_source.zip   "
      f"{os.path.getsize(zip_path) / 1024:.0f} kB, "
      f"{len(zipfile.ZipFile(zip_path).namelist())} files")
shutil.rmtree(build, ignore_errors=True)
sys.exit(1 if (undef or pages > ACCEPTED_PAGES) else 0)
