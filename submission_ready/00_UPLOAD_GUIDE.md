# IEEE Sensors Journal — upload guide

Open this beside the browser. Everything referenced here is in this folder.

**Portal:** IEEE Author Portal — `https://ieee.atyponrex.com/journal/sensors`

Not ScholarOne. `SUBMISSION_MANIFEST.md` and `README.md` in both source trees
map files to ScholarOne field names that no longer apply; use this file instead.

**Article type:** Regular Paper · **ORCID:** compulsory for the submitting author

**Built from:** `submission_compact/` — the live 8-page working copy. Rerun
`python build_package.py --source submission_compact` after that session
finishes, so the figures here match the final manuscript. See
`02_CONSISTENCY_AUDIT.md` for what differs between the two source trees.

---

## What to upload, in order

| # | Portal designation | File | Status |
|---|---|---|---|
| 1 | Main manuscript (PDF) | `manuscript/main.pdf` | **you compile** — see below |
| 2 | Main manuscript (LaTeX source) | `manuscript/main_source.zip` | **you build** — see below |
| 3 | Figure 1 | `figures/fig1_coherence_separation.png` | ready |
| 4 | Figure 2 | `figures/fig2_ema_raw_vs_smoothed.png` | ready |
| 5 | Figure 3 | `figures/fig3_roc.png` | ready |
| 6 | Figure 4 | `figures/fig4_lead_vs_severity.png` | ready |
| 7 | Figure 5 | `figures/fig5_live_demo.png` | ready |
| 8 | Graphical abstract | `graphical_abstract/gagraphic.png` | ready |
| 9 | Supplementary — multimedia | `supplementary/demo_v20.gif` | ready |
| 10 | Supplementary — file | `supplementary/supplementary_code_and_results.zip` | ready |

Total upload is about 8 MB. The Portal's per-submission cap is 40 MB.

## Text pasted into portal fields

| Portal field | Source |
|---|---|
| Cover letter | `portal_text/cover_letter.txt` |
| Author contributions (CRediT) | `portal_text/declarations.txt` §1 |
| Conflicts of interest | `portal_text/declarations.txt` §2 |
| Funding | `portal_text/declarations.txt` §3 |
| Data / code availability | `portal_text/declarations.txt` §4 |
| Ethics | `portal_text/declarations.txt` §5 |
| AI-assistance disclosure | `portal_text/declarations.txt` §6 |
| Graphical abstract caption | `graphical_abstract/gagraphic_caption.txt` |
| Suggested reviewers | `portal_text/suggested_reviewers.txt` — pick 3 from the SUGGEST list |
| Excluded reviewers | same file, EXCLUDE list |
| Keywords | 3–6 from the Portal dropdown, **plus** one category from the journal's editorial keyword list (a separate mandatory classification) |

---

## The two files you still have to make

`main.tex` was left untouched — it is being edited in another session. Once it
is final:

**1. Set the revision mode to clean.** In `main.tex`:

```latex
\def\revmode{clean}
```

It is currently `track`, which renders additions highlighted yellow and
deletions struck through in red. That is the audit copy, not the submission
copy.

**2. Apply the five figure renames** listed in `01_FIGURE_NUMBERING.md`.

**3. Compile** (Overleaf, compiler = pdfLaTeX):

```
pdflatex main ; bibtex main ; pdflatex main ; pdflatex main
```

Put the resulting `main.pdf` in `manuscript/`.

**4. Build the source zip** containing `main.tex`, `references.bib`, `main.bbl`
and the five renamed figures. Include the `.bbl` so the Portal can typeset the
bibliography without running BibTeX. Name it `manuscript/main_source.zip`.

The PDF and the source must match exactly — the Portal checks this.

---

## Specs these files were built against

| Item | Requirement | This package |
|---|---|---|
| Page limit | 8 pages double-column; **$175/page** beyond that | see warning below |
| Figure resolution | >300 dpi colour, >600 dpi line art | 296–394 dpi — **Fig. 5 is 251 dpi, see below** |
| Figure width | 3.5 in single column, 7.16 in double | 3.5 in ×4, 7.16 in ×1 |
| Figure colour mode | no alpha channel | flattened to RGB |
| Graphical abstract size | 672 × 456 px — **specification** | exactly 672 × 456 |
| Graphical abstract file size | < 45 kB — IEEE's word is *recommended* | 35.2 kB |
| Graphical abstract file type | JPG, PNG and others accepted; all converted to JPG | PNG, 256-colour palette, no artifacts |
| Graphical abstract filename | must be `gagraphic` | `gagraphic.png` |
| Graphical abstract caption | ≤ 30 words | 26 words |
| Graphical abstract content | peer-reviewed as technical content | all eight printed values proofread at final size |
| Graphical abstract legibility | small labels must stay readable | **8 of 16 lines below the 9 px floor — fix before upload** |
| Supplementary README | PDF or TXT, not Markdown | `README.txt`, inside the zip |
| Abstract length | 150–250 words | 235 |
| Filenames | no spaces | underscores throughout |

**Fig. 5 is under-resolution.** The rebuilt side-by-side
`fig12_live_demo.png` is 1800 px wide and prints at 7.16 in, i.e. 251 dpi
against IEEE's 300 dpi minimum. Re-render it at ≥ 2148 px wide by raising the
`dpi=` argument in `submission_compact/build/live_demo_sidebyside.py`, then
rebuild this package. Upscaling the existing file will not recover the detail.

**Page-count warning.** The manuscript still carries 5 figures and 10 tables.
The compaction so far is five table font reductions and one reshaped figure,
which recovers well under a page against a 9–10 page estimate and an 8-page
limit — $175/page beyond it. Check the compiled page count before submitting.

## At acceptance, not now

- IEEE Copyright Form (eCF) — completed in-portal after acceptance.
- Overlength page charges, $175 per page past 8.
- Open access is optional: US$2,800, with a 5% IEEE-member / 20% society
  discount. Choosing traditional publication costs nothing.

## Still open from the earlier checklist

- [ ] Make the GitHub repository public.
- [ ] Tag `paper-submission-v1` and push it.
- [ ] Mint the Zenodo DOI from that release, then add it to the manuscript's
      Reproducibility section and recompile.
- [ ] Verify each suggested reviewer's email on their faculty page, 24 h before
      submitting.
- [ ] Run iThenticate if VIT has access; confirm overall similarity < 20%.
