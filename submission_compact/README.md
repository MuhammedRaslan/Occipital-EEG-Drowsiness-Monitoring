# submission_compact — authored source for the IEEE Sensors Journal submission

**Manuscript:** Inter-Hemispheric Occipital Coherence for Subject-Independent
Driver Drowsiness Monitoring and Advance Prediction
**Authors:** Muhammed Raslan Thalassery, Sulaiman Shiyas Ali, Abhishek Rudra Pal,
Ahmed Chemori, G. Murali Mohan
**Affiliations:** School of Mechanical Engineering (SMEC), VIT Chennai, India ·
LIRMM, Université de Montpellier, CNRS, UMR 5506, France
**Corresponding author:** Dr. Abhishek Rudra Pal (abhishek.rudrapal@vit.ac.in)

This folder is the **authored source**. Nothing here is generated except
`figures/`. The upload package is built from it into `../submission_ready/`.

> **Where to upload, and what goes in each slot:**
> [`../submission_ready/00_UPLOAD_GUIDE.md`](../submission_ready/00_UPLOAD_GUIDE.md).
> The portal is the **IEEE Author Portal**
> (`https://ieee.atyponrex.com/journal/sensors`).

---

## What is in here

```
submission_compact/
├── main.tex                 # IEEEtran journal class, two-column
├── references.bib           # BibTeX, 38 entries
├── cover_letter.md          # → portal_text/cover_letter.txt
├── declarations.md          # → portal_text/declarations.txt (6 sections)
├── suggested_reviewers.md   # → portal_text/suggested_reviewers.txt
├── figures/                 # fig1_…fig5_, PDF (vector) + PNG, generated
├── build/
│   └── live_demo_sidebyside.py   # generator for Fig. 5
└── supplementary/
    ├── demo_v20.gif         # live-system demonstrator (referenced in §V.D)
    ├── reproduce.py         # single-entry reproducer
    ├── requirements.txt     # pinned dependencies
    ├── results/             # JSON behind every headline number
    └── scripts/             # analysis scripts called by reproduce.py
```

The supplementary README that ships to the portal is
`../submission_ready/supplementary/README.txt` — IEEE accepts PDF or TXT there,
not Markdown, so it is not authored here.

## Building

There is no system LaTeX on this machine; the toolchain is Tectonic. Everything
runs from the repository root:

```bash
python submission_ready/preflight_ieee.py     --source submission_compact  # 0 failures
python submission_ready/check_clean_render.py --source submission_compact  # clean-mode damage
python submission_ready/build_package.py      --source submission_compact  # figures, portal text, supplementary
python submission_ready/build_manuscript.py   --source submission_compact  # main.pdf + main_source.zip
```

`build_manuscript.py` exits non-zero if the paper is over the **8-page** limit or
has an undefined reference. That is the gate — the PDF and the source archive it
writes come from one compile, because the portal requires them to match.

## Figures

Every figure is generated. No file in `figures/` is hand-made, and no generator
needs a manual copy-and-rename step: each writes its final `fig1_`…`fig5_` name
straight into this folder, in both PDF (used by `main.tex`) and PNG (for the
portal's per-figure upload slots).

| Printed as | Generator |
|---|---|
| Fig. 1 | `../reviewer_revision_analysis.py` |
| Fig. 2 | `../reviewer_revision_analysis.py` |
| Fig. 3 | `../v17_roc.py` |
| Fig. 4 | `../v20_lead_vs_severity.py` |
| Fig. 5 | `build/live_demo_sidebyside.py` |

The graphical abstract is **not** built here. It is
`../submission_ready/graphical_abstract/gagraphic.png`, 672 × 456 px per IEEE
specification, with its caption beside it.

## Revision markup

`main.tex` defines `\revmode`. `clean` renders the submission PDF; `track` shows
additions highlighted and deletions struck through, for co-author review. It must
be `clean` at submission — `preflight_ieee.py` checks this.
