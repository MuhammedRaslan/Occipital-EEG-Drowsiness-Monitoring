---
title: "Response to Review — 15 Comments of 25 July 2026"
---

# Response to Review

**Manuscript:** Inter-Hemispheric Occipital Coherence for Subject-Independent Driver Drowsiness Monitoring and Advance Prediction

**Reviewed draft:** version of 21 June 2026 (4 authors, 5 figures, 26 references)

**Reviewer:** Dr. Ahmed Chemori, LIRMM / CNRS

**Prepared by:** M. R. Thalassery

---

## How to read the accompanying files

| File | What it shows |
|---|---|
| `overleaf_review.zip` | Additions highlighted **yellow**. Easiest read. |
| `overleaf_tracked.zip` | Additions yellow, deletions **red and struck through**. Full audit trail. |
| `overleaf_clean.zip` | No markup. This is the submission copy. |

All three build from one source file. Upload a zip to Overleaf, set the compiler to pdfLaTeX, and recompile.

Two conventions worth knowing before you read the marked copies:

1. **Structural moves are not highlighted.** Comments 4, 7 and 12 merge sections, rename every section, and reorganise the Results. Marking those at character level would turn the whole manuscript yellow and hide the genuine prose changes. Those three are carried by this document instead.
2. **Yellow means new or rewritten text.** Nothing else.

---

## Please read this section first

While addressing comment 3, we verified every reference against Crossref. The result changed the manuscript well beyond a formatting fix, and you should know about it before reading anything else.

**Thirteen of the 33 references were misattributed, and two cited papers do not exist.**

The reference list had been assembled with AI assistance. The failure mode was consistent: correct titles, correct DOIs, mostly correct venues — but author names belonging to other researchers in the field. Examples:

| Key | The draft said | Actually |
|---|---|---|
| `chowdhury2018access` | Chowdhury, M.E.H. *et al.*, **IEEE Access** | A. Chowdhury, Shankaran, Kavakli, Haque, **IEEE Sensors J.** 18(8) |
| `attention2024eeg` | Mehmood *et al.*, **IEEE Sensors Journal** | Divvala & Mishra, **IEEE Sensors *Letters*** 8(3) |
| `hybrid2024simulated` | Cui, Y. *et al.*, vol. 606, 2024 | Lin, Huang, Ma, Tang, vol. 616, 2025 |

A recurring tell was DOI-suffix fragments recorded as page numbers — `pages = {2111}` taken from `s41598-025-02111-x`, `{93765}` from `s41598-025-93765-0`, `{12725}` from `etasr.12725`.

**Two entries could not be found at all**, and both were load-bearing:

- `nguyen2021biomed` — "EEG/fNIRS drowsiness prediction using time-series analysis"
- `lin2020generalised` — "A generalised EEG-based drowsiness prediction framework"

These were the two citations supporting the claim that earlier work reports *"5–10 minute advance windows"* under weak protocols — the claim against which Contribution 4, the paper's central novelty, was positioned. Neither paper exists.

**What we did.** All 13 misattributions are corrected against Crossref with DOIs added. The two non-existent entries are removed and replaced with verified prior work, and the passages citing them are rewritten. The corrected claim is materially different and, we believe, stronger:

> Prior EEG prediction work operates at short horizons — immediately-occurring microsleep events, or microsleep state within the current window — and is evaluated without an independent behavioural anchor, without false-alert control, and without accounting for sessions where one onset never registers. We therefore do not position this work as correcting a previously-claimed minutes-scale lead; to the authors' knowledge no such lead has been reported under a controlled protocol.

One of the replacements, Buriro *et al.* (IEEE TNSRE 2018), predicts microsleep from **inter-channel EEG relationships** — independent published support for the O₁–O₂ coherence result in Section V.A.

A re-runnable verifier (`revision/verify_refs.py`) and the full JSON audit (`revision/ref_verification.json`) are included so this can be repeated before submission.

---

## Point-by-point responses

### 1. The title should be improved; informative and reflecting the content

**Done.**

- Was: *Pro-Active Driver Drowsiness Monitoring Using Two-Channel Occipital EEG*
- Now: *Inter-Hemispheric Occipital Coherence for Subject-Independent Driver Drowsiness Monitoring and Advance Prediction*

The old title named the sensor and the task but none of the three things that make the work publishable: the coherence mechanism, the subject-independent evaluation, and the advance-prediction track. The running head is a shortened variant so it fits the two-column header band.

### 2. Add me to the list of authors; I am an IEEE Senior Member

**Done.** You are the fourth author, with `Senior Member, IEEE`, affiliated to LIRMM, Université de Montpellier, CNRS, UMR 5506. Dr. Pal remains the corresponding author, as in the reviewed draft. The manuscript is now an India–France collaboration, and the cover letter says so.

Propagated to `main.tex` (author block, affiliation `\thanks`, Author Contributions), `cover_letter.md`, `declarations.md` (CRediT, funding), `SUBMISSION_MANIFEST.md` and `README.md`.

While making this change we found that **Dr. Pal's `Member, IEEE` grade was incorrect** — he is not an IEEE member, and the grade had appeared in every draft since April. It has been removed. No grade is claimed for Dr. G. Murali Mohan either. Yours is now the only membership grade in the paper.

**Three items still need you:** your ORCID; your CRediT contribution statement; and confirmation of whether CNRS/LIRMM requires a funding or institutional acknowledgement. All three are marked `[TODO]` in the source.

### 3. Bibliography style is not homogeneous; all references should follow IEEE style

**Done, and it turned out to be more serious than a style problem** — see the section above.

Worth noting: the *style file* was never wrong. `\bibliographystyle{IEEEtran}` was already correct. The inconsistency was in the data fed to it. Fixed without external lookups:

- Same journal under two names unified (`Sensors` vs `Sensors (MDPI)`)
- `{IEEE}` brace-protected consistently across all journal names
- Abbreviation spacing unified
- `who2023road` retyped `@article` → `@techreport` (a WHO report was printing with "WHO Geneva" italicised as a journal)
- `seeingmachines2024` institution corrected (it held the report *type*)
- Stray `note` field removed from `zheng2017seedvig`, which was printing as a trailing clause

Fixed with verification: 13 misattributed entries, DOIs added throughout, and truncated author lists restored where IEEE style requires full lists (up to six names, then *et al.*).

### 4. Better to merge Sections I and II

**Done.** They are now one section, *Introduction: Why Occipital EEG for Pro-Active Driver Monitoring*, ordered: problem → EEG rationale → prior work → contributions. Related Work became a subsection; the Contributions list moved after it.

We also deleted the *"remainder of the paper is organised as follows"* paragraph. With six sections and informative headings it was redundant, and removing it recovered the space that the new nomenclature and reference material consume.

### 5. Related Work should cover all methodologies; room for more references

**Done. 26 → 36 printed references.**

New coverage: sensor form factor (behind-the-ear, ear-module SoC, in-ear EEG), cross-subject domain adaptation, multimodal drowsiness corpora, and short-horizon microsleep prediction. Four references that were already in the `.bib` but never cited have been brought into the text.

Every added reference was verified against Crossref before citing. We deliberately did not pad the count with weak sources.

### 6. Add an introductory sentence to Section E, Evaluation Protocols

**Done.** A short paragraph now precedes the two tracks, stating that they differ in labels, time constants and success criteria, and previewing what each measures before the protocols are given.

### 7. Rework section names; avoid single-word names

**Done.** Twelve renamed. Your three examples specifically:

| Was | Now |
|---|---|
| Methods | Data, Signal Processing, and Evaluation Design |
| Results | Experimental Results |
| Datasets | Two Public Drowsiness Corpora: DROZY and SEED-VIG |

Also renamed: Discussion → *Interpretation, Limitations, and Deployment*; Conclusion → *Conclusion and Future Work*; Signal Processing, Feature Set, Classifier and Smoother, Evaluation Protocols, Monitoring Track, Cross-Dataset and Pooled LOSO, Negative Ablations, Pro-Active Track.

### 8. Rework Fig. 2 to avoid overlap between the curves and the legend

**Done.** Your diagnosis was exact. The legend sat at `center left`, directly on the data — the 0.5 threshold line and the EMA curve were striking through the label text.

It is now a two-column legend in reserved headroom above the traces (y-limit raised to 1.34), with a frame. Nothing overlaps any plotted element. The 0.5 threshold also gained its own legend entry, which it previously lacked.

### 9. Rework the curve line style of Fig. 3 for better visibility, and avoid overlapping the text

**Done**, and this uncovered a reproducibility problem worth reporting.

Three visual changes: the title no longer overflows the axes (it was clipped mid-word in your copy — *"…causal EMA (tau=6C"*), τ renders as a proper glyph; the ROC curve is heavier and the chance diagonal darker with a distinct dash pattern; and the three operating-point labels have moved off the legend onto the curve with leader lines, into empty plot area.

**The reproducibility problem:** the figure shipped in `figures/` had been hand-edited to fix the title, but `v17_roc.py` still emitted the broken version at a different size. Running `reproduce.py` silently overwrote the fix. Script and artifact now agree, and re-running reproduces the published numbers exactly (AUC = 76.62 %, F1 = 77.48 / 77.32 / 75.68).

### 10. Add future work in Section VI

**Done.** Section VI is now *Conclusion and Future Work*, with a paragraph covering five directions: prospective in-car validation; dry-electrode contact characterisation at hair-bearing occipital sites; an electrode-count study to test whether the coherence advantage scales; online per-driver adaptation replacing the fixed cold-start calibration; and fusion with camera-based DMS.

### 11. Why is "IEEE Sensors" among the index terms?

**Removed.** It was a venue name, not a topic — an error. Replaced with the IEEE Thesaurus terms *vigilance* and *real-time systems*.

### 12. The Results section structure should be reworked for readability

**Done.** The hierarchy was badly unbalanced: Section IV.A carried five subsubsections while IV.B, IV.C and IV.E carried none, and one subsection bundled two unrelated topics ("Causal smoother **and** ROC").

Smoothing/operating-point selection and statistical validation are now their own subsections, each with two subsubsections. No subsection exceeds two.

### 13. Cite at least two papers published in IEEE Sensors Journal

**Done — and the original count was zero, not one.**

The draft appeared to cite one IEEE Sensors Journal paper, but that entry (`attention2024eeg`) is in IEEE Sensors **Letters**, a different publication. Meanwhile `chowdhury2018access` *is* an IEEE Sensors Journal paper that had been misfiled as IEEE Access.

Two now appear and are cited substantively:

- A. Chowdhury *et al.*, IEEE Sensors J. **18**(8):3055–3067, 2018
- H. T. Nguyen *et al.*, "Behind-the-ear EEG-based wearable driver drowsiness detection," IEEE Sensors J. **23**(19):23875–23892, 2023

### 14. All mathematical symbols should be defined at first use

**Done**, and this surfaced two symbol collisions:

| Symbol | Conflict | Resolution |
|---|---|---|
| α | EMA coefficient in Eq. (1) **and** the 8–13 Hz alpha band | coefficient → **λ** |
| θ | 4–8 Hz theta band **and** the decision threshold in Table VIII | threshold → **η** |

First-use definitions added for *p*<sub>t</sub>, *p̃*<sub>t</sub>, Δ*t*, τ, λ, η, κ, *d*, *U* and *n*.

### 15. Add a list of acronyms at the beginning of the paper

**Done.** A Nomenclature section with 25 entries follows the index terms.

---

## Changes not requested, made for correctness

1. **Dr. Pal's IEEE membership grade removed** (see comment 2). A false membership claim on a paper submitted to an IEEE journal is an integrity matter.
2. **Cover letter novelty paragraph rewritten.** It still asserted the prior-literature claim removed from the manuscript, and would have reached the editor contradicting the paper.
3. **Cover letter hardware claim corrected.** It stated the headrest form factor "avoids direct scalp-electrode contact with hair." This is backwards — O₁ and O₂ sit on hair-bearing occipital scalp, so contact through hair is the central hardware problem for this design. It also contradicted the new future-work paragraph.
4. **`v17_roc.py` reproducibility desync repaired** (see comment 9).

---

## Outstanding

**Needs Dr. Chemori:** ORCID · CRediT contribution statement · confirmation of CNRS/LIRMM funding acknowledgement.

**Needs a compile.** No LaTeX toolchain was available on the machine used for this revision, so all validation was static: 26/26 cross-references resolve, 36/36 citation keys resolve, no duplicate labels, braces and environments balanced, and all 15 items traced. What static analysis cannot check is package interaction (`soul` + `ulem` + `hyperref`), overfull boxes, float placement and page count. **The first Overleaf build is the real test** and may need one cleanup round.

**Deferred by decision.** The manuscript is currently one-column draft format. The switch to the two-column camera-ready layout is still owed, and will require the figures to be resized — in two-column, `\columnwidth` is roughly half, so figures authored at 7–9 inches will shrink to 36–49 % and their labels with them. Figures 2 and 5 will likely need promotion to full-width `figure*`.
