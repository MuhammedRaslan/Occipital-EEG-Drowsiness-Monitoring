# Submission package — IEEE Sensors Journal

**Manuscript:** Pro-Active Driver Drowsiness Monitoring Using Two-Channel Occipital EEG
**Authors:** Muhammed Raslan Thalassery, Sulaiman Shiyas Ali, Abhishek Rudra Pal, Ahmed Chemori, G. Murali Mohan
**Affiliations:** School of Mechanical Engineering (SMEC), VIT Chennai, India · LIRMM, Université de Montpellier, CNRS, UMR 5506, France
**Corresponding author:** Dr. Ahmed Chemori (Ahmed.Chemori@lirmm.fr)
**Target venue:** IEEE Sensors Journal
**Status:** Draft v1 — internal review pending before portal upload

This directory contains everything needed to submit the manuscript to the IEEE Sensors Journal ScholarOne portal.

---

## Files in this directory

The folder is split into the **manuscript-side** files (top level) and the **supplementary-side** files (`supplementary/`). Everything that ScholarOne needs is here; nothing outside this folder needs to be touched at submission time.

```
submission/
├── SUBMISSION_MANIFEST.md       # Single-page upload guide — open this beside the browser
├── README.md                    # This file
├── main.tex                     # IEEEtran manuscript source (compiles to main.pdf)
├── references.bib               # BibTeX, 32 entries (~30% 2024-2025)
├── cover_letter.md              # Editor cover letter
├── declarations.md              # CRediT, COI, funding, data/code, ethics, AI disclosure
├── suggested_reviewers.md       # 6 suggested + 1 exclusion
├── graphical_abstract.py        # Source for figures/graphical_abstract.png
├── figures/                     # Manuscript figures (4 PNGs at 200-240 dpi)
│   ├── graphical_abstract.png
│   ├── fig10_v17_roc.png
│   ├── fig11_lead_vs_severity.png
│   └── fig12_live_demo.png
└── supplementary/               # Everything ScholarOne treats as supplementary
    ├── README.md                # What's in supplementary and how to use it
    ├── demo_v20.gif             # Live-system demonstrator (referenced in §V.D)
    ├── reproduce.py             # Single-entry reproducer
    ├── requirements.txt         # Pinned Python dependencies
    ├── results/                 # JSON results behind every headline number
    │   ├── publication_results_v17.json (monitoring F1 = 76.79)
    │   ├── publication_results_v17_roc.json (ROC + 3 operating points)
    │   ├── publication_results_v20.json (advance-prediction Pareto)
    │   ├── publication_results_v20_severity.json (lead-vs-PERCLOS)
    │   ├── publication_results_v10b.json (paired Wilcoxon + Cohen's d)
    │   └── ... (10 more from v11/v12/v14/v15/v16/v18/v19/runtime)
    └── scripts/                 # All analysis scripts called by reproduce.py
        ├── ablation_analysis.py        (v11 — feature-family ablation)
        ├── extended_features.py        (v9 — 50-feature LDA)
        ├── hmm_smoothing.py            (v17 — causal EMA monitoring headline)
        ├── advance_prediction_v20.py   (v20 — pro-active headline)
        ├── pooled_loso.py              (v16 — 31-subject pooled LOSO)
        ├── seed_vig_validation.py      (v12 — cross-dataset transfer)
        ├── eegnet_baseline.py          (v14 — deep-learning baseline)
        ├── personal_calibration.py     (v15 — per-driver calibration)
        ├── extended_coherence.py       (v18 — phase-coh negative ablation)
        ├── ensemble_analysis.py        (v19 — ensemble negative ablation)
        ├── v17_roc.py                  (Tier 1 #1 — monitoring ROC)
        ├── v17_v20_stats.py            (Tier 1 #2 — paired stats)
        ├── v20_lead_vs_severity.py     (Tier 1 #3 — severity envelope)
        ├── live_demo_figure.py         (Tier 1 #4 — programmatic demo)
        └── ... (7 more: publication_analysis, riemannian, nested_cv,
                 advance_prediction, runtime_benchmark, make_figures,
                 extract_O1_O2_channels)
```

---

## Where to compile

The simplest path is **Overleaf**:

1. Sign in at overleaf.com.
2. New Project → Upload Project → upload this `submission/` folder as a `.zip`.
3. Set the compiler to `pdflatex` (Menu → Settings).
4. Click "Recompile". The PDF appears in 5–10 seconds.

Local LaTeX (TeX Live or MiKTeX) also works:

```bash
cd submission/
pdflatex main
bibtex main
pdflatex main
pdflatex main      # second run resolves cross-references
```

The output `main.pdf` is the file you upload to ScholarOne.

---

## Switching from draft to camera-ready

The current `main.tex` line 13 is:

```latex
\documentclass[journal,onecolumn,11pt,draftcls]{IEEEtran}
```

Switch to camera-ready by removing `draftcls` and changing `onecolumn` to leave the IEEEtran default (two-column):

```latex
\documentclass[journal]{IEEEtran}
```

Two-column compresses the page count substantially; expect the manuscript to drop from ~14 pages (one-column draft) to ~9–10 pages (two-column camera-ready). If you exceed the 14-page Sensors limit after that, trim the limitations section first (it is the most compressible).

---

## Pre-flight checklist before submitting to ScholarOne

**Manuscript-level**

- [ ] Replace `[TODO]` ORCID placeholders in `main.tex` and `cover_letter.md` with real ORCIDs (orcid.org → register, 5 min each).
- [ ] Verify all author email addresses with the institution.
- [ ] Run a final spell-check (Grammarly free tier or Word's built-in is fine for a first pass).
- [ ] Compile `main.tex` and read the PDF cold from start to finish at 100 % zoom. Look for: missing references (`?` in citations), broken figures, table overflow, equation alignment.
- [ ] Verify every numbered figure is referenced in the body text in the order it appears.
- [ ] Verify every numbered table is referenced in the body text in the order it appears.
- [ ] Check that every claim with a numerical value has a citation or a section reference where the value is computed.
- [ ] Run iThenticate or Turnitin (if available via VIT) to ensure < 20 % similarity overall and < 3 % from any single source. The capstone DOCX text rewritten for IEEE format should be safe; verify.

**Repository-level**

- [ ] Make `https://github.com/MuhammedRaslan/Pro-Active-Driver-Monitoring-System-Using-EEG` public.
- [ ] Tag the commit you used for the paper: `git tag -a paper-submission-v1 -m "Snapshot for IEEE Sensors submission"; git push origin paper-submission-v1`.
- [ ] Link Zenodo to your GitHub account (zenodo.org → Sign in with GitHub → enable the repository).
- [ ] Create a release on GitHub from the tag → Zenodo automatically mints a DOI → copy the DOI into `main.tex` (Reproducibility section) and re-compile.
- [ ] Add a clean root-level `README.md` to the repo that explains: what the project does, how to install dependencies (`pip install -r requirements.txt`), and how to reproduce numbered results (`python reproduce.py --list`).

**Portal-level (ScholarOne, mc.manuscriptcentral.com/sensors-ieee)**

- [ ] Create or sign in to your IEEE author account. Use the corresponding author's institutional email if available.
- [ ] Start a new submission, manuscript type = "Regular Paper".
- [ ] Upload `main.pdf` as the manuscript, `main.tex` and `references.bib` as source, every PNG in `figures/` separately.
- [ ] Paste the cover-letter text into the cover-letter field.
- [ ] Paste each declaration paragraph from `declarations.md` into the corresponding portal field.
- [ ] Enter all author metadata: full name, email, institution, country, ORCID, role.
- [ ] Suggest 4 reviewers from the SUGGEST list in `suggested_reviewers.md`.
- [ ] Add 1 exclusion (P. L. Nunez, per the patent-conflict note).
- [ ] Pick keywords from the IEEE Thesaurus (search "EEG", "driver", "drowsiness", "sensors" — pick 4–6 matching terms).
- [ ] Choose **Traditional (no fee)** at the open-access prompt unless you change your mind.
- [ ] Submit.

**After submission**

You will receive a manuscript ID by email within 24 hours. Do not contact the editor unless 4 months pass without a decision.

---

## Word-count and page targets

| Section | Target words | Target pages (two-column) |
|---|---|---|
| Abstract | 200–250 | 0.25 |
| Introduction | 600–800 | 1.0–1.25 |
| Related Work | 350–450 | 0.5–0.75 |
| Methods | 800–1000 | 1.25–1.5 |
| Results | 1500–2000 | 2.5–3.0 |
| Discussion + Limitations | 700–900 | 1.0–1.25 |
| Conclusion | 100–150 | 0.25 |
| References | n/a | 1.0 |
| Figures + Tables | n/a | 1.5–2.0 |
| **Total** | **~4500** | **~9–10** |

The current draft is at the upper edge of these targets to give room for cutting during internal review. Plan one round of compression after your guide reads it.

---

## Things to update in the next iteration (before submission)

1. **ORCID placeholders** — see `main.tex` lines 30, 34 and `cover_letter.md` lines 5, 78–80.
2. **Acknowledgements** — `main.tex` line ~end-of-Conclusion has a `% [TODO]` marker.
3. **Funding statement** — confirm "no external funding" is correct; update if your guide has used a VIT internal grant for the work.
4. **Reviewer email verification** — `suggested_reviewers.md` warns to verify emails on each candidate's faculty page; do this 24 hours before the portal submission, not earlier (academic emails change).
5. **Zenodo DOI** — add to `main.tex` Reproducibility section once the GitHub release is created.
6. **Title bar metadata** — `main.tex` line 51 uses placeholder `Vol.~XX, No.~X, Month~2026`; the IEEE production team replaces this at acceptance, so you can ignore it for submission.

---

## Internal review process (recommended before submitting)

1. **Self-review.** Read the compiled PDF cold, twice, three days apart.
2. **Co-author review.** S. S. Ali reads it as a critical reader; both students agree on every numerical claim.
3. **Guide review.** Dr. Pal, Dr. Chemori and Dr. G. Murali Mohan read as the senior authors; resolve any disagreements before submission. Dr. Chemori is the corresponding author and signs the cover letter.
4. **External reader (optional but recommended).** A friend in CS / ECE who has not seen the work — they catch unclear sentences your familiarity hides.
5. **One sleep before submitting.** Do not click "submit" the same day you finalise. One overnight gap catches more typos than another full read-through.

A reasonable internal-review timeline from where we are now: 1 week to address any guide feedback, 3 days for ORCID/Zenodo plumbing, 1 day for portal upload. That puts a realistic submit date approximately 10 working days after this draft is complete.
