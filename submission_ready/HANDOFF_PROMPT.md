# Handoff prompt — bring `submission_compact/` and `submission_ready/` to perfect submission readiness

> ## EXECUTED 2026-08-06 — historical record, do not run again
>
> This prompt was carried out in full. Read
> [`03_IEEE_SENSORS_CHECKLIST.md`](03_IEEE_SENSORS_CHECKLIST.md) and
> [`00_UPLOAD_GUIDE.md`](00_UPLOAD_GUIDE.md) for current state instead — they
> are dated against a real run. Two things below turned out to be **wrong**, and
> re-running them would undo work:
>
> 1. **Phase 2's page-cut estimate is false.** "Estimated recovery from 1–3
>    alone: about 2 pages" — measured by compiling every candidate cut, Tables
>    III + VI + IX are worth **zero printed pages**, and deleting all fifteen
>    floats still leaves **nine**. The paper is prose-bound, not float-bound.
>    Eleven pages at $525 was accepted on 2026-08-06 rather than gutting the
>    paper. `build_manuscript.py` now gates on growth past 11.
> 2. **Phase 0 and Phase 1 are done.** The six stale files are deleted, the
>    figures are vector PDF with embedded TrueType, and the generator seam is
>    closed. Re-running Phase 0's deletions is harmless; re-applying Phase 1's
>    "point `\includegraphics` at PDF" is not, since it is already done.
>
> Everything else below — the specs table, the traps list, the DO NOTs — is
> still accurate and still worth reading.

---

## ROLE

You are finishing an IEEE Sensors Journal submission. Two folders must end up
flawless:

- **`submission_compact/`** — the authored source. `main.tex`, `references.bib`,
  `figures/`, `build/`, and the `.md` side documents. This is what gets zipped
  as the LaTeX source upload.
- **`submission_ready/`** — the built upload package. Everything here is
  derived; nothing is authored here except the docs and build scripts.

Correct **file formats** are an explicit requirement of this task, not an
afterthought. See the format table below.

Work is verified by running scripts, not by asserting. Every claim you make
about a file must come from having measured it.

---

## CURRENT STATE (measured 2026-08-06, trust but re-verify)

Run this first — it is the ground truth:

```bash
python submission_ready/preflight_ieee.py --source submission_compact
python submission_ready/build_manuscript.py --source submission_compact
```

Expected right now: **51 pass / 2 warn / 0 fail**, and a compile reporting
**11 pages, 0 undefined refs, 0 overfull boxes, floats in citation order**.

### Already done — do not redo

| Item | State |
|---|---|
| `\revmode` | `clean` |
| Figure filenames | `fig1_`…`fig5_`, matching printed numbers |
| Figure resolution | 315 / 315 / 394 / 394 / 314 dpi — all clear 300 |
| Figure colour | RGB, no alpha, in `submission_ready/figures/` |
| Table II & III overflow | fixed, 0 overfull boxes, no statistic changed |
| Graphical abstract | `gagraphic.png`, 672×456, 35.2 kB, 26-word caption — **CLOSED, accepted as-is by the user. Do not redesign it.** |
| Supplementary README | `README.txt`, all seven IEEE sections |
| `main.pdf` + `main_source.zip` | staged, built from one compile |
| GitHub | public; tag `paper-submission-v1` → `9ea36b7`, pushed |
| Float order | figures and tables both print in citation order |

### The one hard blocker

**11 pages against an 8-page limit = $525 in overlength charges** at $175/page.
This is the main work. See PHASE 2.

---

## AUTHORITATIVE SPECS

From the IEEE Sensors Council *Guide for Authors* and *Graphical Abstract
Instructions*, and the IEEE Author Center. Portal is the **IEEE Author Portal**
(`https://ieee.atyponrex.com/journal/sensors`) — **not** ScholarOne.

| Requirement | Value | Binding? |
|---|---|---|
| Regular paper length | 8 pages, double column | yes — $175/page over |
| Manuscript upload | PDF **and** source, content matching exactly | yes |
| Upload cap | 40 MB per submission | yes |
| Figure resolution | > 300 dpi colour/greyscale, > 600 dpi line art | yes |
| Figure width | 3.5 in single column, 7.16 in double | yes |
| Figure formats | PS, EPS, PDF, PNG, TIF | yes |
| Graphical abstract | 672 × 456 px, filename `gagraphic` | yes — specification |
| Graphical abstract size | < 45 kB | **"Recommended"**, not a limit |
| GA caption | ≤ 30 words | yes |
| Abstract | 150–250 words | IEEE general guidance |
| Supplementary README | PDF or TXT only | yes |
| Video supplementary | MP4/MOV/WMV/AVI, ≤ 100 MB | yes |
| ORCID | compulsory for submitting author | yes |
| Filenames | no spaces | yes |

---

## FILE FORMAT TARGET — this is the "formats must be perfect" requirement

The single biggest remaining format defect: **all five figures are raster PNG,
but every one of them is a matplotlib vector plot.** IEEE's own guidance says
"PS, EPS, and PDF are excellent for creating graphics that require resizing" and
warns that raster cannot be enlarged without quality loss. Shipping a rasterised
vector plot is a real, avoidable quality loss.

| Asset | Current | Target | Why |
|---|---|---|---|
| `figures/fig1..fig5` | PNG raster | **PDF vector** | matplotlib line/box plots; PDF is resolution-independent, usually smaller, and IEEE-preferred |
| `gagraphic` | PNG 672×456 | **keep PNG** | the spec is in pixels; raster is correct here |
| `main.pdf` | PDF | keep | |
| `main_source.zip` | zip with tex/bib/**bbl**/figures | keep | `.bbl` lets the Portal typeset without BibTeX |
| `supplementary/README` | TXT | keep TXT (or PDF) | Markdown is not accepted |
| `demo_v20.gif` | GIF, 6.9 MB | **consider MP4** | IEEE lists video as MP4/MOV/WMV/AVI; GIF is only accepted as an *image*. MP4 is smaller and unambiguous |
| `portal_text/*.txt` | TXT | keep | paste-ready, no Markdown syntax |
| `supplementary_code_and_results.zip` | zip | keep | |

**Vector figure conversion is the main format task.** All five generators are
matplotlib, so it is a `savefig(...pdf)` change, not a redraw:

**Beware the seam: only one generator writes where you think it does.** Three of
the four still emit *legacy filenames* into *other directories*, and someone
copies them across by hand. Re-run a generator and nothing in
`submission_compact/figures/` changes — that has already confused one session.

| Printed as | Generator | Writes to | Then must be copied to |
|---|---|---|---|
| Fig 1 | `reviewer_revision_analysis.py` | `submission/figures/fig13_coherence_separation.png` | `submission_compact/figures/fig1_coherence_separation.png` |
| Fig 2 | `reviewer_revision_analysis.py` | `submission/figures/fig14_ema_raw_vs_smoothed.png` | `…/fig2_ema_raw_vs_smoothed.png` |
| Fig 3 | `v17_roc.py` | `publication_figures_v5/fig10_v17_roc.png` | `…/fig3_roc.png` |
| Fig 4 | `v20_lead_vs_severity.py` | `publication_figures_v5/fig11_lead_vs_severity.png` | `…/fig4_lead_vs_severity.png` |
| Fig 5 | `submission_compact/build/live_demo_sidebyside.py` | `submission_compact/figures/fig5_live_demo.png` | — writes direct, already correct |

**Close this seam as part of Phase 1.** Point every generator at
`submission_compact/figures/` with its final `fig1_`…`fig5_` name, the way
`live_demo_sidebyside.py` already does. A build step that needs a human to copy
and rename files is how the wrong figure gets shipped.

Emit **both** `.pdf` and `.png` from each generator. Use the PDF in `main.tex`
and in the source zip; keep the PNG for the Portal's per-figure upload slots if
its uploader rejects PDF (it should not — PDF is on the accepted list).

Two vector-specific traps:
- **Fonts must be embedded.** Set `matplotlib.rcParams["pdf.fonttype"] = 42`
  (TrueType) so glyphs survive. Type-3 fonts are a common IEEE reject reason.
- **Check the PDF file size.** A scatter with tens of thousands of points can
  produce a huge vector PDF. `fig5_live_demo` draws long EEG traces — if its PDF
  exceeds roughly 2 MB, rasterise just the trace artists with
  `ax.plot(..., rasterized=True)` and `savefig(dpi=400)`, keeping text vector.

---

## THE PLAN

### PHASE 0 — clean out the traps (do first, 10 min)

These stale files can cause a *wrong file to be uploaded*. Delete or fix:

1. **`submission_compact/figures/graphical_abstract.png`** — 188 kB, 2667×1064.
   This is the OLD graphical abstract with the **superseded title burned into
   the image** ("Pro-Active Driver Drowsiness Monitoring Using Two-Channel
   Occipital EEG"). It is not referenced by `main.tex`. **Delete it.** The live
   one is `submission_ready/graphical_abstract/gagraphic.png`.
2. **`submission_compact/graphical_abstract.py`** — generates the above. Delete,
   or add a header comment marking it superseded.
3. **`submission_compact/SUBMISSION_MANIFEST.md`** and
   **`submission_compact/README.md`** — 11 references to **ScholarOne**, the
   wrong portal, with field names that no longer exist. Rewrite to point at
   `submission_ready/00_UPLOAD_GUIDE.md`, or delete.
4. **`submission_compact/supplementary/README.md`** — 3 more ScholarOne refs,
   and it is Markdown where IEEE requires TXT/PDF. The correct file is
   `submission_ready/supplementary/README.txt`.
5. **`submission_ready/manuscript/PUT_COMPILED_FILES_HERE.txt`** — obsolete;
   `main.pdf` and `main_source.zip` now exist. Delete.
6. **`submission_ready/01_FIGURE_NUMBERING.md`** — describes work already
   applied. Fold anything still true into `02_CONSISTENCY_AUDIT.md`, delete it.

Verify after: `python submission_ready/preflight_ieee.py` still 0 fail.

### PHASE 1 — vector figures (see format table above)

1. Add `pdf.fonttype = 42` and a `savefig(..., format="pdf")` alongside each
   existing PNG save, in all four generators.
2. Re-run each generator. **Confirm every number it prints is unchanged** —
   these scripts recompute results, and a changed number means something
   broke, not that the format worked.
3. Point `\includegraphics` at the `.pdf` files. IEEEtran + pdfLaTeX handles
   PDF figures natively; drop the extension in `\includegraphics` so the
   engine picks the best available.
4. Update `build_package.py`'s `FIGURE_MAP` to accept `.pdf`, and extend its
   dpi check: for vector PDFs the dpi test is meaningless, so assert instead
   that the PDF's MediaBox width matches the intended printed width.
5. Recompile and re-run preflight.

### PHASE 2 — the 11 → 8 page problem (the real work)

Current page map, measured:

| Pages | Content |
|---|---|
| 1–3 | Intro, related work, methods — 2,361 words, no floats |
| 4–9 | Results — **all 15 floats** (10 tables, 5 figures) |
| 10 | Discussion tail + conclusion |
| 11 | References (36 entries) |

Six of eleven pages exist to carry floats. Cut there first, in this order —
**each of these needs the user's approval before you do it**, because removing
content from a paper is their decision, not yours:

1. **Table III** duplicates **Fig. 1** — both present the awake-vs-drowsy
   coherence analysis, the figure showing distributions and stating the
   Mann-Whitney result, the table giving the same numbers. Cutting the table
   loses nothing.
2. **Table IX** duplicates **Fig. 4** — same lead-vs-severity sweep, one as a
   curve and one as a table.
3. **Table VI** (per-subject F1/AUC/κ across 10 subjects, full width) is
   textbook supplementary material. Move it to the supplementary zip and
   reference it.
4. If still over: compress §IV Limitations subsections — the most compressible
   prose in the paper.

Estimated recovery from 1–3 alone: about 2 pages, with no argument touched.

After each cut: `python submission_ready/build_manuscript.py` and read the new
page count. The loop is about two minutes. **Do not cut blind — measure after
every change.** Cutting content you did not need to cut is worse than paying.

Also re-check float order after any float is removed; the compile reports it.

### PHASE 3 — final verification

```bash
python submission_ready/preflight_ieee.py --source submission_compact
python submission_ready/check_clean_render.py --source submission_compact
python submission_ready/build_package.py --source submission_compact
python submission_ready/build_manuscript.py --source submission_compact
```

All four must exit 0. `build_manuscript.py` exits non-zero while the paper is
over 8 pages — that is the gate.

Then update `03_IEEE_SENSORS_CHECKLIST.md` statuses to match the run, and
re-tag the repo (see traps).

---

## TRAPS — hard-won, do not rediscover these

1. **Effective dpi is `saved_dpi × authored_width ÷ printed_width`,** not the
   dpi tag in the file. A figure authored 9.0 in and placed at `\textwidth`
   = 7.16 in loses 20 % of its resolution. This bit two figures already.
2. **`.gitignore` has a `build/` rule** (intended for Python build dirs) that
   silently swallows `submission_compact/build/live_demo_sidebyside.py`. Use
   `git add -f` for it. It also excludes `*.pdf` and `*.zip` — deliberate
   project policy, but it means `main.pdf` is not in the repo.
3. **The manuscript's Reproducibility section names the git tag
   `paper-submission-v1` explicitly.** If you change the tree, re-tag, or the
   paper cites a snapshot that does not match. Verify with the GitHub API, not
   by assuming.
4. **`main` is still the default branch and is stale.** Work is on
   `revision-chemori`. The tag resolves correctly either way, but the repo
   homepage shows old content. Ask before merging.
5. **Never reduce a reported statistic's precision to fix a layout problem.**
   A p-value mantissa was shortened to fix a table overflow, then found
   unnecessary once the headers were shortened instead. Fix layout with layout.
6. **Deprecated numbers.** Never cite 89.54 %, 91.32 %, "1.95 % drop", or the
   Phase-D single-subject "27 critical detections / 9.5 % false alarms". Those
   came from a leaked train/test split. The v20 SEED-VIG "9.5 % per-session
   false alerts" is a *different* and legitimate number — do not confuse them.
   Authoritative values live in `publication_results_v*.json` and the abstract.
7. **GA colour quantisation must measure the *source*,** not the downscaled
   image — Lanczos legitimately invents edge tones, which reads as grain and
   wrongly triggers denoising that blurs clean art.
8. **IEEEtran defers full-width `table*` floats** and numbers them on placement,
   so printed order can diverge from citation order. Currently fine; re-verify
   after any float change. `build_manuscript.py` reports it.
9. **There is no system LaTeX.** Tectonic 0.17.0 lives at
   `%LOCALAPPDATA%\tectonic\tectonic.exe` (not in winget; fetched from GitHub
   releases). `build_manuscript.py` finds it there.

---

## DO NOT

- **Do not redesign the graphical abstract.** The user reviewed and accepted it.
  Its remaining nits (small-text tier, one blue caption at 3.26:1) were
  considered and consciously declined.
- **Do not restore colour coding** to the graphical abstract. Measured and
  found unnecessary; the two-colour scheme is AAA-contrast and greyscale-safe.
- **Do not cut manuscript content without explicit approval.** Measure, propose
  with page savings attached, then wait.
- **Do not commit or push** without being asked.
- **Do not edit `submission/`** — it is the 2026-08-02 base, kept for reference.
  All work happens in `submission_compact/`.

---

## DEFINITION OF DONE

- [ ] `preflight_ieee.py` — 0 failures
- [ ] `check_clean_render.py` — 0 issues
- [ ] `build_manuscript.py` — exits 0, meaning **≤ 8 pages**, 0 undefined
      references, 0 overfull boxes, floats in citation order
- [ ] All five figures are vector PDF with embedded TrueType fonts
- [ ] No stale file anywhere that could be uploaded by mistake — in particular
      the old wrong-title `graphical_abstract.png` is gone
- [ ] No document in either folder names ScholarOne
- [ ] `main.pdf` and `main_source.zip` regenerated from the *same* compile
- [ ] Total upload payload ≤ 40 MB
- [ ] `03_IEEE_SENSORS_CHECKLIST.md` statuses match a real run, dated
- [ ] Every figure generator writes its final filename straight into
      `submission_compact/figures/` — no manual copy-and-rename step survives
- [ ] Repo re-tagged and the tag verified live via the GitHub API

---

## STILL THE USER'S CALL, NOT YOURS

Surface these; do not decide them.

1. **Pay $525 or cut 3 pages.** Both are legitimate. Cutting is described in
   Phase 2; paying needs no work at all.
2. **`nunez2025patent`** — titled "Headrest-integrated real-time alertness
   prediction system" — sits in `references.bib` uncited, while the paper's
   stated novelty is a headrest EEG form factor. 36 of 38 entries are cited, so
   this is not an accident, but it should be a deliberate choice.
   `toyota2021patent` is the same question, more weakly.
3. **Merging `revision-chemori` into `main`.**
4. **Portal-form items** they must do themselves: the mandatory category from
   the journal's editorial keyword list, three suggested reviewers with emails
   verified 24 h out, and the open-access election (traditional is free;
   open access is US$2,800 with 5 % IEEE-member / 20 % society discount).
