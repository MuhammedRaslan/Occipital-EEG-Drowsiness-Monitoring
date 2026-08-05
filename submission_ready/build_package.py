"""
Assemble the IEEE Sensors Journal upload package into submission_ready/.

Everything here is derived from submission/ -- this script never writes to
submission/, and never touches main.tex or references.bib.

What it does:
  1. figures/   copies the five manuscript figures under names that match
                their printed figure numbers, and flattens RGBA -> RGB
                (IEEE production does not want an alpha channel).
  2. supplementary/  copies the demo animation and zips code + results,
                     alongside a plain-text README (IEEE requires the
                     README in PDF or TXT, not Markdown).
  3. portal_text/    strips Markdown out of the cover letter, declarations
                     and reviewer list so each is paste-ready.

The graphical abstract is built separately by
graphical_abstract/make_gagraphic.py.

Run:  python build_package.py
"""

import argparse
import os
import re
import shutil
import zipfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))

ap = argparse.ArgumentParser()
ap.add_argument("--source", default="submission_compact",
                help="folder to build from: submission_compact (the live "
                     "8-page working copy) or submission (the 2026-08-02 base)")
args = ap.parse_args()
SRC = os.path.join(REPO, args.source)
if not os.path.isdir(SRC):
    raise SystemExit(f"no such source folder: {SRC}")
print(f"source: {args.source}/\n")

# IEEE minimums, checked against the width each figure is actually printed at.
IEEE_MIN_DPI = 300
COL_IN, TEXT_IN = 3.5, 7.16

# Printed figure number -> source file. Order taken from the order the
# figure environments appear in main.tex; see 01_FIGURE_NUMBERING.md.
# Source filenames now match the printed figure numbers in submission_compact/;
# the legacy fig10-fig14 names are still what submission/ carries, so both are
# accepted here and resolved in order.
#
# The last field is the width the figure is printed at: \columnwidth for the
# four single-column figures, \textwidth for the full-width live demo.
FIGURE_MAP = [
    (1, ["fig1_coherence_separation.png", "fig13_coherence_separation.png"],
     "fig1_coherence_separation.png", COL_IN),
    (2, ["fig2_ema_raw_vs_smoothed.png", "fig14_ema_raw_vs_smoothed.png"],
     "fig2_ema_raw_vs_smoothed.png", COL_IN),
    (3, ["fig3_roc.png", "fig10_v17_roc.png"], "fig3_roc.png", COL_IN),
    (4, ["fig4_lead_vs_severity.png", "fig11_lead_vs_severity.png"],
     "fig4_lead_vs_severity.png", COL_IN),
    (5, ["fig5_live_demo.png", "fig12_live_demo.png"],
     "fig5_live_demo.png", TEXT_IN),
]


def ensure(*parts):
    p = os.path.join(HERE, *parts)
    os.makedirs(p, exist_ok=True)
    return p


def strip_markdown(text):
    """Markdown -> paste-ready plain text for the portal's text fields."""
    out = []
    for line in text.splitlines():
        if line.strip() == "---":
            out.append("")
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)          # headings
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)    # bold
        line = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*", r"\1", line)   # italic
        line = re.sub(r"`([^`]*)`", r"\1", line)        # inline code
        line = re.sub(r"^\s*[-*]\s+", "  - ", line)     # bullets
        out.append(line.rstrip())
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


# ----------------------------------------------------------------------
# 1. Figures
# ----------------------------------------------------------------------
fig_dir = ensure("figures")
print("figures/")
warnings = []
for num, src_names, dst_name, print_in in FIGURE_MAP:
    cands = [os.path.join(SRC, "figures", n) for n in src_names]
    src = next((p for p in cands if os.path.isfile(p)), None)
    if src is None:
        raise SystemExit(f"Fig. {num}: none of {src_names} found in {SRC}/figures")
    dst = os.path.join(fig_dir, dst_name)
    im = Image.open(src)
    if im.mode in ("RGBA", "LA", "P"):
        flat = Image.new("RGB", im.size, "white")
        rgba = im.convert("RGBA")
        flat.paste(rgba, mask=rgba.split()[-1])
        im = flat
    else:
        im = im.convert("RGB")
    w, h = im.size

    # The dpi tag in the file is whatever the plotting script wrote. What IEEE
    # actually cares about is pixels per printed inch once LaTeX has scaled the
    # figure to \columnwidth or \textwidth, so compute that instead.
    eff_dpi = w / print_in
    im.save(dst, format="PNG", dpi=(eff_dpi, eff_dpi), optimize=True)

    flag = "" if eff_dpi >= IEEE_MIN_DPI else "  << UNDER 300 dpi"
    if flag:
        warnings.append(
            f"Fig. {num} ({dst_name}) is {w}px wide. Printed at {print_in:.2f} in "
            f"that is {eff_dpi:.0f} dpi, below IEEE's {IEEE_MIN_DPI} dpi minimum "
            f"for colour figures. Re-render it at least "
            f"{int(IEEE_MIN_DPI * print_in)}px wide.")
    print(f"  Fig. {num}  {dst_name:34s} {w}x{h}px  "
          f"printed {print_in:.2f}in -> {eff_dpi:5.0f} dpi  "
          f"{os.path.getsize(dst) / 1024:5.0f}kB  RGB{flag}")

# ----------------------------------------------------------------------
# 2. Supplementary
# ----------------------------------------------------------------------
sup_dir = ensure("supplementary")
print("\nsupplementary/")

gif_src = os.path.join(SRC, "supplementary", "demo_v20.gif")
gif_dst = os.path.join(sup_dir, "demo_v20.gif")
shutil.copy2(gif_src, gif_dst)
print(f"  demo_v20.gif  {os.path.getsize(gif_dst) / 1024 / 1024:.1f} MB")

zip_path = os.path.join(sup_dir, "supplementary_code_and_results.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for name in ("reproduce.py", "requirements.txt"):
        z.write(os.path.join(SRC, "supplementary", name), name)
    for sub in ("scripts", "results"):
        root = os.path.join(SRC, "supplementary", sub)
        for f in sorted(os.listdir(root)):
            z.write(os.path.join(root, f), f"{sub}/{f}")
    z.write(os.path.join(sup_dir, "README.txt"), "README.txt")
n = len(zipfile.ZipFile(zip_path).namelist())
print(f"  supplementary_code_and_results.zip  {n} files, "
      f"{os.path.getsize(zip_path) / 1024:.0f} kB")

# ----------------------------------------------------------------------
# 3. Portal text fields
# ----------------------------------------------------------------------
txt_dir = ensure("portal_text")
print("\nportal_text/")
for src_name, dst_name in (("cover_letter.md", "cover_letter.txt"),
                           ("declarations.md", "declarations.txt"),
                           ("suggested_reviewers.md", "suggested_reviewers.txt")):
    raw = open(os.path.join(SRC, src_name), encoding="utf-8").read()
    dst = os.path.join(txt_dir, dst_name)
    open(dst, "w", encoding="utf-8", newline="\r\n").write(strip_markdown(raw))
    print(f"  {dst_name:26s} {os.path.getsize(dst) / 1024:.1f} kB")

print("\nPackage assembled under submission_ready/.")
if warnings:
    print("\n" + "!" * 70)
    for w in warnings:
        print("! " + w)
    print("!" * 70)
