r"""Generate the three Overleaf-ready archives from the single canonical source.

There is exactly one manuscript source, submission/main.tex. It carries the
revision markup (\add, \del, \chg) and a mode switch, \def\revmode{...}. This
script writes three copies with the switch preset and zips each with the
bibliography and figures, so each archive can be dropped straight into
Overleaf and compiled with pdfLaTeX.

    overleaf_review.zip    additions highlighted yellow, deletions hidden
    overleaf_tracked.zip   additions yellow, deletions red and struck through
    overleaf_clean.zip     no markup at all -- the submission copy

The archives are generated artifacts. Never hand-edit them: edit
submission/main.tex and re-run this script.

    python revision/build_variants.py
"""
from __future__ import annotations

import io
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUB = os.path.join(ROOT, "submission")
OUT = os.path.join(ROOT, "revision")

MODES = {
    "review":  "additions highlighted yellow; deletions hidden",
    "tracked": "additions yellow; deletions red and struck through",
    "clean":   "no markup - the submission copy",
}
# \revmode value used inside main.tex for each archive
REVMODE = {"review": "review", "tracked": "track", "clean": "clean"}

SWITCH = re.compile(r"\\def\\revmode\{[a-z]+\}")


def build(mode: str) -> str:
    tex = io.open(os.path.join(SUB, "main.tex"), encoding="utf-8").read()

    new_switch = "\\def\\revmode{%s}" % REVMODE[mode]
    # lambda replacement, not a string: re treats backslashes in a replacement
    # string as template escapes, and "\d" in "\def" would raise bad escape.
    tex, n = SWITCH.subn(lambda _m: new_switch, tex, count=1)
    if n != 1:
        sys.exit("ERROR: could not find the \\def\\revmode{...} switch in main.tex")

    banner = (
        "%% ================================================================\n"
        "%% GENERATED FILE - do not edit.\n"
        "%% Produced by revision/build_variants.py from submission/main.tex.\n"
        "%% Variant: %s (%s)\n"
        "%% ================================================================\n"
    ) % (mode, MODES[mode])
    tex = banner + tex

    zip_path = os.path.join(OUT, "overleaf_%s.zip" % mode)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("main.tex", tex)
        z.write(os.path.join(SUB, "references.bib"), "references.bib")
        figdir = os.path.join(SUB, "figures")
        for f in sorted(os.listdir(figdir)):
            if f.lower().endswith((".png", ".pdf", ".jpg")):
                z.write(os.path.join(figdir, f), "figures/" + f)
    return zip_path


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    print("Building Overleaf archives from submission/main.tex\n")
    for mode in MODES:
        p = build(mode)
        with zipfile.ZipFile(p) as z:
            n = len(z.namelist())
        print("  %-22s %6.2f MB  %2d files   (%s)"
              % (os.path.basename(p), os.path.getsize(p) / 1048576, n, MODES[mode]))
    print("\nUpload each to Overleaf: New Project -> Upload Project -> select the zip.")
    print("Set the compiler to pdfLaTeX, then Recompile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
