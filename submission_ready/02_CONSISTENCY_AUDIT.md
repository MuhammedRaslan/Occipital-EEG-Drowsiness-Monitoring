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

**Already resolved.** The replacement `graphical_abstract/gagraphic.jpg` in this
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
| File size — IEEE's word is *recommended* | 44.1 kB, under 45 |
| Encoding | JPEG q80, 4:2:0 chroma, no alpha |
| Aspect handling | source was 3:2, 1.8 % off target — squeezed, not cropped |
| Small-text legibility at final size | footer 13 px, checked at 3× zoom, all glyphs clean |
| Greyscale | readable; awake/drowsy separate by amplitude, not colour |
| Numbers proofread at 672 × 456 | 76.8 %, 76.6 %, 66.1 %, +31.7 min, 85.7 %, 56 ms, O1, O2 |
| Electrode placement | occipital, on the lower rim of the head — corrected from the first attempt, which had them mid-scalp |

Chroma subsampling is what bought the size. Glyph sharpness lives in the luma
channel, so 4:2:0 at q80 (44.1 kB) reads better than 4:4:4 at a quality low
enough to hit the same budget. Straight 4:4:4 bottomed out at 54.8 kB.

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

### Inconsistent — needs action

| # | Issue | Where | Fix |
|---|---|---|---|
| 1 | Old title burned into the graphical abstract | `submission/figures/graphical_abstract.png` and the copy in `submission_compact/` | done — use `graphical_abstract/gagraphic.png`; delete or ignore the old PNGs |
| 2 | `\def\revmode{track}` — audit build, with yellow highlights and struck-through deletions | both `main.tex` | set to `clean` before compiling |
| 3 | Figure filenames don't match printed numbers | both `main.tex` | five renames, see `01_FIGURE_NUMBERING.md` |
| 4 | **Fig. 5 is 251 dpi as printed** | `submission_compact/figures/fig12_live_demo.png` | see below |
| 5 | ScholarOne named as the portal, 14 times | `submission_compact/README.md` (6), `SUBMISSION_MANIFEST.md` (5), `supplementary/README.md` (3) | superseded by `00_UPLOAD_GUIDE.md`; the real portal is the IEEE Author Portal |
| 6 | All figures still RGBA in both source trees | `submission*/figures/*.png` | done — the copies in `figures/` here are flattened to RGB |
| 7 | Supplementary README is Markdown | both trees | done — `supplementary/README.txt` here |

### On issue 4, the rebuilt Fig. 5

The new side-by-side `fig12_live_demo.png` is 1800 px wide. It is placed with
`\includegraphics[width=\textwidth]`, so LaTeX scales it to 7.16 in, giving
**251 dpi** — below IEEE's 300 dpi minimum for colour figures. The version it
replaced was 2864 px, i.e. 400 dpi at the same printed width.

It needs re-rendering at **≥ 2148 px wide** (raise the `dpi=` argument in
`submission_compact/build/live_demo_sidebyside.py`). Resampling the existing PNG
upward will not help — the detail is not there. I have not touched that script,
since that session is live.

Figs. 1 and 2 report 296 dpi, a 1.3 % shortfall that comes from being authored
at 3.45 in and printed at 3.50 in. That is immaterial; no action needed.

`build_package.py` now checks effective printed dpi on every run and prints a
warning block, so this cannot pass unnoticed again.

---

## Which source is this package built from?

`submission_ready/` is now built from **`submission_compact/`**, on the
assumption that the compact tree is the one being submitted. If that is wrong:

```
python submission_ready/build_package.py --source submission
```

Rerun the same command against `submission_compact` once the other session
finishes, so the figures here match the final manuscript.
