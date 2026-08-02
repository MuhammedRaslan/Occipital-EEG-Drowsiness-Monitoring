# Handoff prompt — final submission pass

Paste everything below the line into a fresh Claude Code session opened in this
repository. Written 2026-07-31, at commit `6c95b9c` on branch `revision-chemori`.

---

You are a senior engineer helping me finish an IEEE Sensors Journal submission.
Read this fully before touching anything, then confirm the state matches before
you start work.

## The project

Two-channel occipital EEG (O1/O2) driver-drowsiness pipeline, headrest-oriented.
Ten lean features (sample + permutation entropy ×2, aperiodic 1/f slope ×2, PAF
delta, O1–O2 magnitude-squared coherence in θ/α/β) → shrinkage LDA (lsqr +
Ledoit–Wolf) → causal EMA smoother → threshold. Strict LOSO throughout.

Headline numbers — these are the only correct ones:

- DROZY LOSO weighted F1 **76.79 %** (v17, smoothed), 62.08 % unsmoothed (v11)
- AUC 76.62 %, Cohen's κ 0.539, paired Wilcoxon p = 0.005, d = 1.11
- Pooled 31-subject DROZY ∪ SEED-VIG F1 **66.13 %**; cross-dataset 64.93 %
- Pro-active lead **+8.83 min** (0 % per-session FA, mild) to **+31.67 min**
  (9.5 % FA, severe)

**Never cite 89.54 %, 91.32 %, "1.95 % drop", "27 critical", or "9.5 % FA" from
the old README or engineering diary.** Those came from a leaked-split evaluation
and are deprecated.

## Where things stand

The manuscript has been through a full revision answering all 15 comments from
Dr. Ahmed Chemori (LIRMM/CNRS), who joined as fourth author. That work is done,
compiled, and verified against the rendered PDFs. `revision/preflight.py`
reports 0 failures.

Deliverables live in `revision/`:

- `overleaf_review.zip` — additions highlighted yellow
- `overleaf_tracked.zip` — additions yellow, deletions red + struck through
- `overleaf_clean.zip` — no markup, the submission copy
- `response_to_review.docx` — point-by-point reply to Chemori

All three zips are generated from the single `submission/main.tex` by
`revision/build_variants.py`, which presets `\def\revmode{review|track|clean}`.
Never hand-edit a zip. The zips are gitignored; the script is tracked.

## Decisions already made — do not re-litigate

- **Corresponding author is Dr. A. R. Pal**, not Chemori. This flipped to
  Chemori and then back. Because the reviewed draft already named Pal, the
  corresponding-author line carries **no revision markup** — marking it would
  claim a change that isn't happening. Chemori is fourth author only.
- **Dr. Pal is not an IEEE member.** Drafts through June printed
  `\IEEEmembership{Member,~IEEE}` for him; that was false and is removed.
  Chemori's `Senior Member, IEEE` is the only grade in the paper.
- **Author order:** Thalassery, Ali, Pal, Chemori, G. Murali Mohan.
- **Title** (chosen from a shortlist): *Inter-Hemispheric Occipital Coherence for
  Subject-Independent Driver Drowsiness Monitoring and Advance Prediction*.
- **36 references**, all verified against Crossref.

## What remains for final submission

1. **Fill three `[TODO]` placeholders** — five ORCIDs, Chemori's CRediT
   contribution statement, and whether CNRS/LIRMM requires a funding or
   institutional acknowledgement. I am chasing these; ask me before inventing
   anything.
2. **Regenerate Figure 5.** It ships with real text collisions — the two onset
   labels overprint each other and the panel title ("PEMedian-lead case",
   "PERCILOSronset"). `live_demo_figure.py` is **already fixed** but could not be
   run because SEED-VIG raw data was absent from this machine. If the dataset is
   now present: `python live_demo_figure.py && python revision/build_variants.py`,
   then recompile all three variants. Verify the fix visually — it has never been
   executed.
3. **Two-column camera-ready conversion.** The manuscript is still one-column
   draft format (24 pages). In two-column `\columnwidth` roughly halves, so every
   figure authored at 7–9 inches will shrink to 36–49 % and its labels with it.
   Figures 2 and 5 will likely need promoting to full-width `figure*`. Expect
   ~10–11 two-column pages; IEEE Sensors Journal charges overlength above 8, so
   flag the count once it compiles.
4. **Compile all three variants and read the PDFs.** Static checks have already
   caught what they can; only a real build finds package interaction, overfull
   boxes and float placement.

## Landmines — these have each already bitten once

- **`soul`'s `\hl` cannot re-typeset inline math, `\cite`, or `\ref`.** Any of
  those inside `\add{} \del{} \chg{}` must be wrapped in `\mbox{}` or it prints
  as a solid black box. All current cases are wrapped; new markup must be too.
- **Use `\DeclareRobustCommand`, never `\newcommand`, for the markup macros.**
  They appear inside `\title{}` and `\section{}` — moving arguments — and a
  fragile command there fails with "Argument of `\@sect` has an extra }".
- **`\add{}` must not span a paragraph break, sit inside a `\caption{}`, or
  appear inside an `equation` environment.** `preflight.py` checks all three.
- **The bibliography was originally AI-assembled and was badly wrong** — 13 of 33
  entries misattributed, 2 cited papers did not exist at all. It is now clean and
  verified. **Never invent or guess bibliographic data.** If a new citation is
  needed, verify it against the Crossref REST API first;
  `revision/verify_refs.py` does this and is re-runnable.
- **Bash heredocs and `python -c` mangle backslashes here** — `\ref` becomes a
  carriage return, `\d` raises `bad escape`. Write a script file and run it
  instead. This wasted several cycles.
- **No LaTeX toolchain on this machine.** pandoc 3.9 is present but there is no
  PDF engine. Overleaf is the compile path; I upload the zips manually.

## Verification

Run these after any edit to `submission/`:

```bash
python revision/preflight.py        # 0 failures expected; 1 known benign warning
python revision/build_variants.py   # regenerates all three zips
```

`preflight.py` checks LaTeX integrity, markup safety, bibliography health,
cross-file consistency across `main.tex` / `cover_letter.md` /
`declarations.md` / `README.md` / `SUBMISSION_MANIFEST.md`, figure presence, and
traceability of all 15 review items. It asserts Pal is the corresponding author,
so it will catch a regression on that.

## Known and deliberately unfixed

Two substantive methodology issues were found during a deep review and **parked
by my explicit decision** — they are not defects in the revision work, and I do
not want them reopened unless I ask:

1. The pro-active alarm fires inside its own 300-second calibration window for
   19 of 21 subjects (median onset 240 s), so the rule is not causal at
   deployment as written.
2. §II.D claims the per-subject z-score is "equivalent to a 60-second pre-drive
   alert calibration." Measured, a real 60-second calibration gives v11 57.49 /
   v17 69.10 against the published 62.08 / 76.79, so the claim is false as
   stated.

Both are verified and real. Chemori's review did not touch either. They are the
most likely things a journal referee will find. If you think either must be
addressed before submission, say so once and let me decide.

Start by running `preflight.py` and `git log --oneline -8`, tell me what state
you find, and wait for my go-ahead before changing anything.
