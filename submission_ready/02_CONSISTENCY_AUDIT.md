# Consistency audit — 2026-08-05 21:40

Answers to the three questions, then everything that is inconsistent and what
to do about it.

---

## 1. Did the other session touch the manuscript?

**Not `submission/main.tex`.** It was last written **2026-08-02 13:03:47**,
three days ago, still 67 438 bytes. Nothing in it has moved.

**It created a new tree instead: `submission_compact/`**, at 21:16 today, and
was still editing it at **21:19:46** — minutes before this audit. That is where
the 8-page work is happening.

`submission_compact/` is a byte-identical copy of `submission/` except for three
things:

| Change | Detail |
|---|---|
| `main.tex` | 5 lines. Five table blocks changed `\small` → `\footnotesize`. Nothing else — same 5 figures, same 10 tables, same text. |
| `figures/fig12_live_demo.png` | rebuilt as a wide side-by-side panel: 2864×2300 → **1800×660** |
| `build/live_demo_sidebyside.py` | new script that produces the above |

Everything else — `README.md`, `SUBMISSION_MANIFEST.md`, `cover_letter.md`,
`declarations.md`, `suggested_reviewers.md`, `references.bib`,
`graphical_abstract.py`, `supplementary/` — is identical to `submission/`.

**So the compaction has barely begun.** Five table font reductions and one
reshaped figure will recover well under a page. The manuscript still carries 5
figures and 10 tables against an 8-page limit. Since that session is still live,
treat any figure in `submission_compact/` as provisional.

> **Superseded 2026-08-06.** The two trees have since diverged well beyond those
> three items: all five figures rebuilt and renamed and re-emitted as vector PDF,
> Tables II and III reflowed, `\revmode` set to `clean`, and
> `SUBMISSION_MANIFEST.md`, `graphical_abstract.py`, `figures/graphical_abstract.png`
> and `supplementary/README.md` deleted outright. `submission_compact/` is the
> only live tree. The paragraph above is kept as the record of where this audit
> started.

---

## 2. The title

The manuscript title is set as `\chg{old}{new}`, which renders the **new** one:

> Inter-Hemispheric Occipital Coherence for Subject-Independent Driver
> Drowsiness Monitoring and Advance Prediction

Two places still carry the old title, `Pro-Active Driver Drowsiness Monitoring
Using Two-Channel Occipital EEG`:

| Where | Prints? | Verdict |
|---|---|---|
| `main.tex` line 6, in both copies | No — it is a `%` comment | cosmetic, ignore or tidy |
| **`figures/graphical_abstract.png`, in both copies** | **Yes** | **the real defect** |

The old graphical abstract has the **old title burned into the image**.
`graphical_abstract.py` line 89 was updated to the new title, but the PNG was
never re-rendered from it, so the stale image is what would have been uploaded.
This is exactly the discrepancy you spotted.

**Already resolved.** The replacement `graphical_abstract/gagraphic.png` in this
folder does **not** reproduce the paper title. Its blue band carries a short
descriptive header instead — "Pro-Active Driver Drowsiness Monitoring" over
"Inter-hemispheric occipital coherence from two headrest electrodes".

That is deliberate. The full title is 108 characters; set across the mandated
3.5 in width it renders at roughly 4 pt, which is below anything IEEE accepts,
and Xplore already prints the real title directly beside the graphic. Because
the header paraphrases rather than quotes the title, it cannot fall out of sync
with it the way the old PNG did.

### Final graphical-abstract provenance and checks

Generated externally from the brief in `NANO_BANANA_PROMPT.md`, source kept as
`gagraphic_src.png` (1536 × 1024), fitted by `fit_gagraphic.py`.

| Check | Result |
|---|---|
| Dimensions — a **specification** | 672 × 456 px exactly |
| File size — IEEE's word is *recommended* | 35.2 kB, under 45 |
| Encoding | PNG, 256-colour palette, no alpha |
| Aspect handling | source was 3:2, 1.8 % off target — squeezed, not cropped |
| Small-text legibility at final size | footer 13 px, checked at 3× zoom, all glyphs clean |
| Greyscale | readable; awake/drowsy separate by amplitude, not colour |
| Numbers proofread at 672 × 456 | 76.8 %, 76.6 %, 66.1 %, +31.7 min, 85.7 %, 56 ms, O1, O2 |
| Electrode placement | occipital, on the lower rim of the head — corrected from the first attempt, which had them mid-scalp |
| Caption | 26 words, under IEEE's 30 |

Palette quantisation is what bought the size. The art is flat-shaded vector-style
illustration, so 256 indexed colours are lossless to the eye where JPEG at the
same budget put ringing around every glyph edge; the earlier 4:2:0 q80 JPEG was
44.1 kB, this is 35.2 kB and sharper.

**Closed. Accepted as-is by the author on 2026-08-05, and again on 2026-08-06.**
Its two remaining nits — a small-text tier at roughly 6–7 px of ink, and one blue
caption at 3.26:1 contrast — were measured, considered, and consciously declined.
Do not redesign it, and do not restore colour coding: the two-colour scheme is
AAA-contrast and greyscale-safe.

`make_gagraphic.py` still builds a pure-matplotlib alternative from the real
result JSONs and real EEG epochs. It is kept as a fallback, not the shipped
asset.

**One standing caveat.** The EEG waveforms in the shipped graphic are drawn by
the generator, not plotted from the recordings. They carry no axes, units or
scale, so they read as schematic illustration, and the amplitude/frequency
contrast they show is the correct physiological direction. The real epochs from
subject 05M are cached in `ga_trace_cache.npz` if you ever want them composited
in.

Every other file is on the new title and correct: both cover letters, both
`README.md`, `references.bib`, `revision/response_to_review.md`,
`revision/preflight.py`, and `submission_ready/supplementary/README.txt`.

The running head in `\markboth` reads "Inter-Hemispheric Occipital Coherence for
Driver Drowsiness Monitoring and Advance Prediction" — shorter than the full
title. That is intentional and correct; IEEE running heads must fit the header
band.

---

## 3. Cross-file consistency

### Verified consistent

| Fact | Checked across |
|---|---|
| Author order: Thalassery, Ali, Pal, Chemori, Murali Mohan | `main.tex` §author, `cover_letter`, `declarations` §1 |
| Corresponding author: A. R. Pal, abhishek.rudrapal@vit.ac.in | `main.tex` `\thanks`, `cover_letter`, `README` |
| A. R. Pal carries **no** IEEE membership grade | `\chg` on line 116 strips it |
| A. Chemori: Senior Member, IEEE; LIRMM affiliation | `main.tex` line 117/124, `cover_letter` |
| All five ORCIDs | `main.tex` line 125 == `cover_letter` lines 40–47 |
| Date: 2 August 2026 | `\thanks{Manuscript received...}` == `cover_letter` |
| Headline numbers (F1 76.79, AUC 76.62, κ 0.539, pooled 66.13, +8.83/0.0 %, +31.67/9.5 %, 56 ms) | abstract == `cover_letter` == result JSONs == new graphical abstract |
| Abstract length 235 words | IEEE 150–250 |
| Figure and table citation order | every float referenced before definition, in sequence |
| No hard-coded "Fig. 3"/"Table IV" in prose | zero matches |

### Was inconsistent — all closed

| # | Issue | Where | Resolution |
|---|---|---|---|
| 1 | Old title burned into the graphical abstract | `submission/figures/graphical_abstract.png` and the copy in `submission_compact/` | **closed 2026-08-06** — `graphical_abstract/gagraphic.png` is the live asset; the `submission_compact/` copy and its generator `graphical_abstract.py` are deleted |
| 2 | `\def\revmode{track}` — audit build, with yellow highlights and struck-through deletions | both `main.tex` | closed — set to `clean`; `preflight_ieee.py` check A enforces it |
| 3 | Figure filenames don't match printed numbers | both `main.tex` | closed — see *Figure numbering* below |
| 4 | **Fig. 5 was 251 dpi as printed** | `submission_compact/figures/fig5_live_demo.png` | closed — re-rendered at 2250 px = **314 dpi** at 7.16 in |
| 5 | ScholarOne named as the portal, 14 times | `submission_compact/README.md` (6), `SUBMISSION_MANIFEST.md` (5), `supplementary/README.md` (3) | **closed 2026-08-06** — `README.md` rewritten to point at `00_UPLOAD_GUIDE.md`; the other two deleted. The real portal is the IEEE Author Portal, `https://ieee.atyponrex.com/journal/sensors` |
| 6 | All figures still RGBA in both source trees | `submission*/figures/*.png` | closed — the copies in `figures/` here are flattened to RGB |
| 7 | Supplementary README is Markdown | both trees | closed — `supplementary/README.txt` here; the Markdown original is deleted |

`submission/` is the 2026-08-02 base and is deliberately left untouched, so its
own copies of these defects survive there. Nothing is built from it.

---

## Figure numbering

*(folded in from the former `01_FIGURE_NUMBERING.md`, 2026-08-06)*

The printed numbers were never the problem. Every float is referenced through
`\ref{}` and every `\label` is unique, so LaTeX assigns the numbers and they
cannot drift from the text. There is no literal `Fig. 3` or `Table IV` typed into
the prose anywhere — searched, zero matches, and `preflight_ieee.py` re-checks it
every run.

The problem was the **filenames**: legacy analysis-pipeline names (`fig10`–`fig14`)
left over from before some figures were dropped. `fig13` printed as Fig. 1,
`fig10` as Fig. 3. The Author Portal takes figures as individual files in figure
order and IEEE production staff match file to figure by name, so a file called
`fig10` sitting in the Figure 3 slot is exactly how figures get transposed in the
proofs.

| Printed as | `\label` | Legacy filename | Now |
|---|---|---|---|
| Fig. 1 | `fig:coh` | `fig13_coherence_separation.png` | `fig1_coherence_separation` |
| Fig. 2 | `fig:ema` | `fig14_ema_raw_vs_smoothed.png` | `fig2_ema_raw_vs_smoothed` |
| Fig. 3 | `fig:roc` | `fig10_v17_roc.png` | `fig3_roc` |
| Fig. 4 | `fig:severity` | `fig11_lead_vs_severity.png` | `fig4_lead_vs_severity` |
| Fig. 5 | `fig:demo` | `fig12_live_demo.png` | `fig5_live_demo` |

**The generator seam is closed as of 2026-08-06.** Renaming the files was only
half the fix: four of the five generators still wrote *legacy* names into *other*
directories (`submission/figures/`, `publication_figures_v5/`), and a human
copied them across by hand. Re-running a generator changed nothing in
`submission_compact/figures/`, which confused one session outright. Every
generator now writes its final `fig1_`…`fig5_` name straight into
`submission_compact/figures/`, in both `.pdf` and `.png`. No manual
copy-and-rename step survives anywhere in the build.

## Full-width table placement

Six of the ten tables are `table*` (full-width) floats. In IEEEtran's two-column
mode a `table*` can only be set at the top of a page, so LaTeX often defers it
past one or more single-column floats — and a float is numbered when it is
*placed*, not where it is defined. A deferred `table*` can therefore end up
numbered after a single-column `table` defined below it.

The `\ref`s stay correct either way, so no claim in the text becomes wrong. What
breaks is IEEE's expectation that floats *appear* in citation order, which a
copy-editor will flag. `build_manuscript.py` now reads this straight out of the
`.aux` and prints the placement of every float on every compile, so it is checked
rather than assumed. **Re-read that line after adding or removing any float.**

---

## Which source is this package built from?

`submission_ready/` is built from **`submission_compact/`** — the live tree.
`submission/` is the 2026-08-02 base, kept for reference only; do not edit it and
do not build from it.
