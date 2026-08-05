# Submission manifest — what to upload where

This is the single-page reference for the ScholarOne portal upload session. Print or open beside the browser when you fill the form.

## ScholarOne fields → file mapping

| ScholarOne field name | What to upload | File in this folder |
|---|---|---|
| **Manuscript** | Compiled PDF of the main paper | `main.pdf` (compile from `main.tex`) |
| **Manuscript source** | LaTeX source archive | `main.tex` + `references.bib` (zip together) |
| **Figure 1** ... **Figure 5** | High-resolution PNG, one per upload slot, in manuscript order | `figures/fig13_coherence_separation.png` (Fig 1), `figures/fig14_ema_raw_vs_smoothed.png` (Fig 2), `figures/fig10_v17_roc.png` (Fig 3), `figures/fig11_lead_vs_severity.png` (Fig 4), `figures/fig12_live_demo.png` (Fig 5) |
| **Graphical abstract** | The pipeline-summary single-pane figure | `figures/graphical_abstract.png` |
| **Cover letter** | Letter to editor-in-chief | paste body of `cover_letter.md` |
| **Supplementary multimedia** | Animated demo | `supplementary/demo_v20.gif` |
| **Supplementary file 1** | Reproducer + scripts archive | zip `supplementary/reproduce.py` + `supplementary/requirements.txt` + `supplementary/scripts/` |
| **Supplementary file 2** | Headline result JSONs | zip `supplementary/results/` |
| **Author contributions** field | CRediT statement | paste section "1." of `declarations.md` |
| **Conflicts of interest** field | COI statement | paste section "2." of `declarations.md` |
| **Funding** field | Funding statement | paste section "3." of `declarations.md` |
| **Data/code availability** field | Reproducibility statement | paste section "4." of `declarations.md` |
| **Ethics** field | Human-subjects statement | paste section "5." of `declarations.md` |
| **AI-assistance disclosure** field (if shown) | AI-tool disclosure | paste section "6." of `declarations.md` |
| **Suggested reviewers** (4–6 entries) | One name per slot | from `suggested_reviewers.md` SUGGEST list |
| **Excluded reviewers** (1–2 entries) | One name per slot | from `suggested_reviewers.md` EXCLUDE list |
| **Keywords** (4–6 terms) | IEEE Thesaurus terms | "Electroencephalography", "Driver behavior", "Sensor systems and applications", "Pattern classification", "Real-time systems", "Vigilance" |

## Pre-submission action list (fill in before opening the portal)

- [x] Replace `[TODO]` placeholders in `main.tex` with **five** real ORCIDs. *(Done. All five validated: ISO 7064 MOD 11-2 check digit correct and the public ORCID record resolves to the named author.)*
- [x] Replace `[TODO]` ORCIDs in `cover_letter.md`. *(Done, same five.)*
- [x] Insert the submission date in `cover_letter.md` and update `\thanks{Manuscript received ...}` in `main.tex`. *(Both set to 2 August 2026.)*
- [x] Obtain A. Chemori's CRediT contribution statement (`main.tex` Author Contributions, `declarations.md` §1). *(Methodology guidance; writing — review & editing.)*
- [x] Confirm the funding statement with A. Chemori — CNRS/LIRMM may require an acknowledgement. *(Confirmed 2026-08-02: none required. "No external funding was received for this work" stands, and now carries no revision markup because it is unchanged from the reviewed draft.)*
- [x] Acknowledgements finalised — dataset contributors plus VIT Chennai (`main.tex` Acknowledgements).
- [ ] Corresponding author remains **A. R. Pal** (abhishek.rudrapal@vit.ac.in) — the ScholarOne account and all editor correspondence stay with him. A. Chemori joins as fourth author only.
- [ ] Make `https://github.com/MuhammedRaslan/Pro-Active-Driver-Monitoring-System-Using-EEG` public.
- [ ] `git tag -a paper-submission-v1 -m "IEEE Sensors v1"; git push origin paper-submission-v1`.
- [ ] Mint Zenodo DOI from the tag (zenodo.org → enable repo → create release).
- [ ] Update `main.tex` Reproducibility section with the Zenodo DOI; recompile.
- [ ] Verify each suggested reviewer's email on their faculty page (24 h before submission, not earlier).
- [ ] Run iThenticate (if VIT has access) on the compiled PDF; confirm overall similarity < 20 %.
- [ ] Read the compiled `main.pdf` cold, twice, with at least one overnight gap between reads.
- [ ] Verify every cited reference resolves (no `[?]` in PDF).
- [ ] Verify every figure is referenced and appears in the order it is referenced.
- [ ] Spell-check (Word / Grammarly / `aspell`).

## Compile instructions

**Overleaf (recommended):**
1. Zip the contents of this `submission/` folder (excluding `supplementary/` to keep the upload small).
2. New Project → Upload → drop the zip.
3. Compiler = pdfLaTeX. Click "Recompile".
4. Download `main.pdf`.

**Local (TeX Live or MiKTeX):**
```
cd submission
pdflatex main
bibtex main
pdflatex main
pdflatex main
```

## Switching to camera-ready

In `main.tex`, change line 13 from:
```latex
\documentclass[journal,onecolumn,11pt,draftcls]{IEEEtran}
```
to:
```latex
\documentclass[journal]{IEEEtran}
```
This drops the draft watermark and switches to the IEEE two-column production layout. Expect the paper to drop from ~14 pages (one-column draft) to ~9–10 pages (two-column camera-ready).

If page count is too high after that, trim the §V Limitations subsections first (most compressible content).

## After submission

- Manuscript ID arrives by email within 24 h.
- Status pages: ScholarOne shows "Under Review" once the editor accepts the assignment (typically within 2 weeks).
- Do NOT email the editor unless ≥ 4 months have passed without a decision.
- If a desk-reject arrives within 2 weeks, the cause is almost always: scope mismatch, page-limit violation, missing graphical abstract, or iThenticate flag. Address and resubmit (the system supports a re-upload of the same manuscript ID once).
