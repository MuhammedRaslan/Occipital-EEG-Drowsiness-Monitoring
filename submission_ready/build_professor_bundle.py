"""
Assemble submission_professor/ -- the manuscript plus the portal upload set,
flat, for sending to a co-author or supervisor to review before submission.

Everything is copied from submission_ready/, which is itself built by
build_package.py and build_manuscript.py. Nothing here is authored, and nothing
is copied by hand: a bundle assembled manually is how the wrong file gets sent,
which is the same failure this project already hit once with figure filenames.

What goes in: the ten files the IEEE Author Portal takes as uploads, plus the
graphical-abstract caption (peer-reviewed as technical content, so it needs
reading alongside the image) and a README naming what is what.

What stays out: build scripts, audits, checklists, figure provenance, and the
PNG twins of the figures -- the manuscript uses the vector PDFs, and shipping
both would leave the reader guessing which is real.

Run:  python submission_ready/build_professor_bundle.py
"""

import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(REPO, "submission_professor")

# (source relative to submission_ready/, portal slot description)
ITEMS = [
    ("manuscript/main.pdf", "1  Main manuscript (PDF)"),
    ("manuscript/main_source.zip", "2  Main manuscript (LaTeX source)"),
    ("figures/fig1_coherence_separation.pdf", "3  Figure 1"),
    ("figures/fig2_ema_raw_vs_smoothed.pdf", "4  Figure 2"),
    ("figures/fig3_roc.pdf", "5  Figure 3"),
    ("figures/fig4_lead_vs_severity.pdf", "6  Figure 4"),
    ("figures/fig5_live_demo.pdf", "7  Figure 5"),
    ("graphical_abstract/gagraphic.png", "8  Graphical abstract"),
    ("graphical_abstract/gagraphic_caption.txt", "8  Graphical abstract caption"),
    ("supplementary/demo_v20.gif", "9  Supplementary -- multimedia"),
    ("supplementary/supplementary_code_and_results.zip",
     "10 Supplementary -- code and results"),
    # Typed into portal fields rather than uploaded, but a co-author has to read
    # and approve them -- the corresponding author signs the cover letter.
    ("portal_text/cover_letter.pdf", "-  Cover letter (portal field)"),
    ("portal_text/declarations.pdf", "-  Declarations (portal fields)"),
    ("portal_text/suggested_reviewers.pdf", "-  Suggested/excluded reviewers"),
]


def pdf_page_count(path):
    """Page count, or None if it cannot be determined.

    Tectonic writes the page tree into compressed object streams, so grepping
    the raw bytes for /Type /Page finds nothing -- an earlier version of this
    function did exactly that and confidently reported 0 pages for an 11-page
    file. Use a real parser, and return None rather than a wrong number if
    none is installed.
    """
    try:
        from pypdf import PdfReader
        return len(PdfReader(path).pages)
    except Exception:
        pass
    try:
        import fitz
        with fitz.open(path) as d:
            return d.page_count
    except Exception:
        pass
    # Uncompressed PDFs only; correct when it matches, silent when it does not.
    n = len(re.findall(rb"/Type\s*/Page[^s]", open(path, "rb").read()))
    return n or None


def check_fresh():
    """Refuse to bundle a package that predates the source it was built from.

    The bundle is a copy, so it goes stale the moment anything upstream is
    rebuilt -- which has already happened once, when a verification run
    recompiled the manuscript after the bundle had been assembled. The two
    PDFs were the same document, but they were not the same file, and nothing
    said so. Compare timestamps and say so.
    """
    pdf = os.path.join(HERE, "manuscript", "main.pdf")
    built = os.path.getmtime(pdf)
    src = os.path.join(REPO, "submission_compact")
    newer = []
    for rel in ["main.tex", "references.bib"]:
        p = os.path.join(src, rel)
        if os.path.getmtime(p) > built:
            newer.append(rel)
    figdir = os.path.join(src, "figures")
    for f in sorted(os.listdir(figdir)):
        if os.path.getmtime(os.path.join(figdir, f)) > built:
            newer.append(f"figures/{f}")
    if newer:
        sys.exit("submission_ready/manuscript/main.pdf is older than its "
                 "source:\n  " + "\n  ".join(newer)
                 + "\n\nRe-run build_package.py and build_manuscript.py first, "
                   "then this script last.")


def main():
    missing = [s for s, _ in ITEMS if not os.path.isfile(os.path.join(HERE, s))]
    if missing:
        sys.exit("not built yet -- run build_package.py and build_manuscript.py "
                 "first.\nmissing:\n  " + "\n  ".join(missing))
    check_fresh()

    # The bundle is derived in full, so rebuild it from empty rather than
    # letting a file removed upstream survive here from a previous run.
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    total = 0
    rows = []
    for src, slot in ITEMS:
        dst = os.path.join(OUT, os.path.basename(src))
        shutil.copy2(os.path.join(HERE, src), dst)
        size = os.path.getsize(dst)
        total += size
        rows.append((slot, os.path.basename(src), size))

    pages = pdf_page_count(os.path.join(OUT, "main.pdf"))
    if pages is None:
        shutil.rmtree(OUT)
        sys.exit("could not read main.pdf's page count -- install pypdf. The "
                 "README states the length and the charge, so it must not "
                 "guess; no bundle written.")
    write_readme(rows, total, pages)

    print(f"submission_professor/  ({len(rows) + 1} files, "
          f"{total / 1048576:.2f} MB)\n")
    for slot, name, size in rows:
        print(f"  {slot:36s} {name:38s} {size / 1024:8.1f} kB")
    print(f"  {'':36s} {'README.txt':38s} "
          f"{os.path.getsize(os.path.join(OUT, 'README.txt')) / 1024:8.1f} kB")
    print(f"\n  main.pdf is {pages} pages")
    if pages != 11:
        print(f"  NOTE: expected 11 pages, got {pages} -- the manuscript "
              f"changed length, re-read the overlength decision")


def write_readme(rows, total, pages):
    # Width from the data, so a longer label can never shunt the filename
    # column out of alignment.
    w = max(len(slot) for slot, _, _ in rows)
    listing = "\n".join(f"  {slot:{w}s}  {name}" for slot, name, _ in rows)
    over = max(0, pages - 8)
    charge = over * 175
    text = f"""IEEE Sensors Journal submission -- review copy
==============================================

Inter-Hemispheric Occipital Coherence for Subject-Independent Driver
Drowsiness Monitoring and Advance Prediction

M. R. Thalassery, S. S. Ali, A. R. Pal, A. Chemori, G. Murali Mohan
Corresponding author: Dr. Abhishek Rudra Pal <abhishek.rudrapal@vit.ac.in>

Start with main.pdf ({pages} pages). Items 1-10 are the files uploaded to the
portal, in upload order. The three marked "-" are not uploaded as files -- their
text is typed into portal fields -- but they need reading and approving, and the
corresponding author signs the cover letter.

{listing}

Total {total / 1048576:.2f} MB, against a 40 MB portal cap that applies to
items 1-10 only.

Portal: IEEE Author Portal, https://ieee.atyponrex.com/journal/sensors
(not ScholarOne). Article type: Regular Paper.


One thing to be aware of before you read
----------------------------------------
The manuscript is {pages} pages against IEEE's 8-page threshold, which means
$175/page x {over} = ${charge} in overlength charges at acceptance. That is a
deliberate choice, not an oversight.

Getting under 8 pages was tested by compiling every candidate cut rather than
estimating. Removing the three tables that duplicate a figure or belong in
supplementary (Tables III, VI, IX) changes the printed page count by zero.
Removing all ten tables reaches 10 pages. Removing every one of the fifteen
figures and tables still leaves 9. Only deleting all floats AND the Limitations
subsection reaches 8.

The paper is prose-bound, not float-bound: the body text plus a 36-entry
bibliography occupies 9 pages before a single figure or table is placed. So the
options were to pay $525 or to gut the paper, and paying was chosen.

The 8-page figure is IEEE's charging threshold, not a submission cap.


State of the package
--------------------
Verified by script, not by assertion:

  - 0 undefined references, 0 overfull boxes
  - figures and tables both print in citation order
  - all five figures are vector PDF with embedded TrueType fonts
    (Type 3 fonts are a standard IEEE production reject)
  - graphical abstract is exactly 672 x 456 px, 35.2 kB, 26-word caption
  - the PDF and the source archive come from one compile, as the portal requires
  - revision markup is off -- this renders as the clean submission copy, with no
    highlighted additions or struck-through deletions

Source and full build tooling:
https://github.com/MuhammedRaslan/Pro-Active-Driver-Monitoring-System-Using-EEG
tagged paper-submission-v1


What still needs a decision before submitting
---------------------------------------------
  - the mandatory category from the journal's editorial keyword list
  - which reviewers to name. The portal takes 3-5 suggestions and 0-2
    exclusions; suggested_reviewers.pdf lists 7 candidates and recommends
    picking 4, plus 1 exclusion. Verify each email on the candidate's faculty
    page 24 h beforehand, not earlier -- academic addresses change.
  - open access (US$2,800, 5%% IEEE-member / 20%% society discount) versus
    traditional publication, which is free
  - approval of the cover letter and the six declaration statements, which are
    included here as PDFs
"""
    open(os.path.join(OUT, "README.txt"), "w", encoding="utf-8",
         newline="\r\n").write(text.replace("%%", "%"))


if __name__ == "__main__":
    main()
