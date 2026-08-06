# IEEE Sensors Journal — full submission checklist

Compiled 2026-08-05 from the IEEE Sensors Council *Guide for Authors*, the
Council's *Graphical Abstract Instructions*, and the IEEE Author Center pages
on figures and supplementary materials. Project status is as of this date.

**Portal:** IEEE Author Portal — `https://ieee.atyponrex.com/journal/sensors`
**Not** ScholarOne. Submissions must not be emailed to the Editor-in-Chief or
any Associate Editor.

Status key: **OK** done and verified · **OPEN** still to do · **FAIL** currently
violates a requirement · **?** cannot be checked from here

> **Run `python preflight_ieee.py` to re-check every automatable item.**
> As of **2026-08-06** it reports **72 passed, 1 warning, 0 failures**, plus 9
> items it correctly refuses to auto-pass. `build_manuscript.py` reports 11
> pages, 0 undefined references, 0 overfull boxes, floats in citation order, and
> exits 0. `check_clean_render.py` reports 0 candidate issues. Statuses below are
> from that run.

---

## A. Manuscript file and format

| ✓ | Requirement | Detail | Status |
|---|---|---|---|
| ☐ | Article type | Regular Paper | OPEN — select in portal |
| ☐ | Template | IEEE **double-column** style template. `\documentclass[journal]{IEEEtran}` | OK — set in `main.tex` |
| ☑ | PDF supplied | Compiled `main.pdf`, 296 kB | **OK** — `manuscript/main.pdf` |
| ☑ | Source supplied | LaTeX source **and** PDF are both required, and their content must match exactly | **OK** — both from one compile, `build_manuscript.py` |
| ☑ | Source archive contents | `main.tex`, `references.bib`, **`main.bbl`**, all five figures | **OK** — 8 files, 177 kB |
| ☑ | Total upload size | ≤ 40 MB per submission | OK — 8.4 MB |
| ☑ | Filenames | No spaces; use underscores | OK |
| ☑ | Revision markup off | `\def\revmode{clean}` | **OK** — set 2026-08-05 |
| ☑ | Page limit | **8 pages** double-column for a Regular Paper | **11 pages — over, deliberately. See the measurement below.** |
| ☑ | Overlength budgeted | **$175 per page** beyond 8, mandatory at acceptance | **$525 — accepted 2026-08-06** |

## B. Manuscript content

| ✓ | Requirement | Detail | Status |
|---|---|---|---|
| ☐ | Abstract present | Required for all papers | OK |
| ☐ | Abstract length | 150–250 words (IEEE general guidance) | OK — 235 |
| ☐ | Abstract self-contained | No abbreviations, footnotes, citations or references | OPEN — verify on final read |
| ☐ | Index terms | Present after the abstract | OK |
| ☐ | Units | SI, IEEE standard abbreviations | OPEN — verify |
| ☐ | Maths legible | Equations readable at final size | OPEN — verify in PDF |
| ☐ | Every figure cited in text | And in the order it appears | OK — verified in source |
| ☐ | Every table cited in text | And in the order it appears | OK in source; **?** in the compiled PDF, see D-note |
| ☐ | No broken references | No `?` in the compiled PDF | OPEN — check after compiling |
| ☐ | No hard-coded float numbers | All via `\ref{}` | OK — zero literal "Fig. 3"/"Table IV" found |
| ☐ | Conference-paper expansion | Only if it contains substantial new material; declare it | N/A — capstone thesis is not prior publication under IEEE policy |
| ☐ | Not under review elsewhere | Duplicate submission → immediate reject, withdrawal of your other manuscripts, **and a 1-year submission ban** | OK — stated in cover letter |

## C. Figures

| ✓ | Requirement | Detail | Status |
|---|---|---|---|
| ☑ | Uploaded individually | One file per figure, in figure order | OK — `figures/fig1…fig5`, PDF and PNG on each stem |
| ☑ | Accepted formats | PS, EPS, PDF, PNG, TIF | **OK — vector PDF** (PNG twins kept for the Portal's slots) |
| ☑ | Resolution, colour/greyscale | **> 300 dpi** at printed size | **N/A — vector.** PNG twins are 315 / 315 / 394 / 394 / 314 dpi |
| ☑ | Resolution, line art | > 600 dpi | **N/A — vector**, i.e. unbounded |
| ☑ | Fonts embedded, no Type 3 | Type 3 is a standard production reject | **OK** — all Type0/TrueType, `pdf.fonttype = 42`, checked per figure |
| ☑ | Column width | 3.5 in single column; **7.16 in** double column | OK — authored 3.45 in ×4 (1.01× on placement), 9.00 in ×1 (0.80×) |
| ☑ | No alpha channel | Flatten to RGB | OK — PNG twins flattened in `build_package.py` |
| ☑ | Filenames match figure numbers | `fig1_`…`fig5_` | **OK** — and every generator now writes that name directly |
| ☐ | Greyscale-safe | Distinguish by shape/position, not colour alone | OPEN — verify by eye |

**Vector conversion (2026-08-06).** All five figures are matplotlib line, box
and violin plots, so shipping them as raster was an avoidable quality loss —
IEEE's own guidance prefers PS/EPS/PDF precisely because they resize without
degrading. Each generator now emits `.pdf` and `.png` on the same stem;
`main.tex` includes the PDF.

- Fonts: `pdf.fonttype = 42` in all four generators, so glyphs embed as TrueType
  rather than matplotlib's default Type 3.
- Size: the vector files are *smaller*, not larger — 21–38 kB each against
  96–229 kB for the PNGs. `main.pdf` fell from 871 kB to 296 kB and
  `main_source.zip` from 735 kB to 177 kB. Fig. 5 was the size risk (long EEG
  traces) and came out at 37 kB, so no rasterising of trace artists was needed.
- Correctness: all three result JSONs were re-diffed after re-running the
  generators and are identical apart from timestamps. F1 = 76.79, AUC = 76.62,
  κ = 0.539, lead +8.83 → +31.67 min all unchanged.

**The generator seam is closed (2026-08-06).** Three of the four generators used
to write *legacy* filenames into *other* directories, and a human copied them
across by hand — so re-running a generator changed nothing in
`submission_compact/figures/`, which confused a previous session outright. Every
generator now writes its final `fig1_`…`fig5_` name straight into the
manuscript's figure directory. No manual copy-and-rename step survives.

**Table float order — checked on every compile.** As of 2026-08-06 figures land
1→p5, 2→p5, 3→p5, 4→p8, 5→p9 and tables I→p4, II→p4, III→p4, IV→p6, V→p6,
VI→p7, VII→p7, VIII→p7, IX→p8, X→p8. Both ascend monotonically, so the
full-width `table*` deferral warned about earlier has not materialised.
`build_manuscript.py` reads this out of the `.aux` and reports it every run, so
it is verified rather than assumed. **Re-read that line after touching any
float.**

**Compile is reproducible.** `python build_manuscript.py` compiles with tectonic
(a single self-contained binary in `%LOCALAPPDATA%\tectonic`, no MiKTeX), stages
`manuscript/main.pdf` and `manuscript/main_source.zip` from the *same* compile so
they cannot drift apart, and reports page count, undefined references, overfull
boxes and float order. It exits non-zero on an undefined reference, or if the
manuscript grows past the 11 pages signed off.

## D. Graphical abstract — mandatory

Peer-reviewed as technical content, not decoration.

| ✓ | Requirement | Spec | Status |
|---|---|---|---|
| ☐ | Supplied at all | Mandatory for IEEE Sensors Journal | OK |
| ☐ | Dimensions | **672 × 456 px (3.5 in × 2.38 in)** — a specification | OK — exact |
| ☐ | File size | **< 45 kB** — IEEE's word is *Recommended* | OK — 35.2 kB |
| ☐ | Filename | must be **`gagraphic`** | OK — `gagraphic.png` |
| ☐ | Accepted formats | JPG, TIFF, PNG, GIF, Word, PDF, PS, EPS, BMP. All are converted to JPG on ingest. | OK |
| ☐ | Caption | **≤ 30 words** | OK — 26, in `gagraphic_caption.txt` |
| ☐ | Content | "A visual highlight of the main point… a microcosm of the full article" | OK |
| ☑ | Legible at final size | 9 px minimum ink height as a working floor | 3 of 10 text bands measure 6–8 px of **ink extent** — reviewed and **ACCEPTED as-is**, see below |
| ☐ | Numbers correct | Peer-reviewed claims, not typography | OK — all eight verified at 672 × 456 |
| ☐ | Greyscale-readable | IEEE converts to JPG; some readers print mono | OK |
| ☐ | No fabricated data | Generated charts are invented data | OK — all values are printed text; waveforms are schematic, no axes or units |

**Do not redesign the graphical abstract.** It was reviewed and accepted twice
(2026-08-05, re-confirmed 2026-08-06). Both remaining nits — the small-text tier
and one blue caption at 3.26 : 1 — were measured and consciously declined. If it
is ever reopened for some other reason: on the 2688 × 1824 master the 9 px floor
is **36 px**; scale small text 1.3–1.5× and take the room from panel padding,
not panel size.

Multimedia variants, if ever needed: video abstract → `gavideo`, audio →
`gaaudio`, still cover for either → `gacovergraphic`.

## E. Supplementary material

| ✓ | Requirement | Detail | Status |
|---|---|---|---|
| ☐ | Labelled supplementary | Uploaded as separate files, marked as such | OPEN — at upload |
| ☐ | Text formats | TXT, DOC, DOCX, PDF | OK |
| ☐ | Image formats | JPG, TIF, PNG, GIF, PDF, PS, EPS, BMP | OK |
| ☐ | Video formats | MP4, MOV, WMV, AVI — **≤ 100 MB** | N/A — GIF, 6.9 MB |
| ☐ | Audio | MP3, AIFF, MOV, RA, WAV — < 3 MB recommended | N/A |
| ☐ | **README required** | For every dataset and multimedia object, in **PDF or TXT** — never Markdown | OK — `supplementary/README.txt` |
| ☐ | README contents | Contents, total size, platform/environment, component descriptions, setup, run instructions, expected output, contact | OK — all seven sections present |
| ☐ | Referenced in the paper | Supplementary must be cited in the text | OK |
| ☐ | No redistributed data | DROZY and SEED-VIG are under third-party use agreements | OK — neither is redistributed |

## F. Portal metadata and fields

| ✓ | Field | Requirement | Source |
|---|---|---|---|
| ☐ | ORCID | **Compulsory** for the submitting author | all five verified |
| ☐ | Author metadata | Name, email, institution, country, ORCID, role — each author | `main.tex` `\thanks` |
| ☐ | Keywords | Portal dropdown, typically 3–6 — confirm count in the portal | see `00_UPLOAD_GUIDE.md` |
| ☐ | **Category classification** | **One** category from the journal's own editorial keyword list — separate and mandatory | OPEN |
| ☐ | Cover letter | Not mandatory, standard practice | OK — `portal_text/cover_letter.txt` |
| ☐ | Suggested reviewers | 3 recommended; may expedite review. Not co-authors, collaborators, family, or same institution. | OK — 7 candidates, pick 3–4 |
| ☐ | Excluded reviewers | Optional | OK — P. L. Nunez, patent conflict |
| ☐ | Author contributions | CRediT | OK — `declarations.txt` §1 |
| ☐ | Conflicts of interest | | OK — §2 |
| ☐ | Funding | | OK — §3, none |
| ☐ | Data/code availability | | OK — §4 |
| ☐ | Ethics | | OK — §5 |
| ☐ | AI-assistance disclosure | Per IEEE's generative-AI guidance | OK — §6 |
| ☐ | Open access election | US$2,800; 5 % IEEE-member, 20 % society discount. Traditional is free. | OPEN — decide |

## G. Pre-submission verification

| ✓ | Action | Status |
|---|---|---|
| ☑ | Set `\revmode{clean}` and recompile | **OK** — 2026-08-05, enforced by preflight check A |
| ☑ | Apply the five figure renames | **OK** — 2026-08-05, and the generator seam closed 2026-08-06 |
| ☑ | Re-render Fig. 5 at ≥ 2148 px | **OK** — 2250 px PNG twin, and the manuscript copy is vector |
| ☑ | Convert the five figures to vector PDF with embedded TrueType | **OK** — 2026-08-06 |
| ☑ | Graphical abstract | **CLOSED** — accepted as-is; 256-colour export already in place |
| ☑ | Rebuild package: `python build_package.py --source submission_compact` | **OK** — 2026-08-06 |
| ☑ | Decide the page count against the 8-page limit | **OK** — measured, 11 pages accepted at $525, 2026-08-06 |
| ☑ | Check table numbers appear in citation order | **OK** — reported every compile; monotonic |
| ☑ | Confirm no `?` citations in the PDF | **OK** — 0 undefined refs/cites |
| ☑ | Fix two overfull tables | **OK** — 0 overfull hboxes, no statistic reduced in precision |
| ☑ | Delete stale files that could be uploaded by mistake | **OK** — 2026-08-06; wrong-title `graphical_abstract.png` and its generator, `SUBMISSION_MANIFEST.md`, `supplementary/README.md`, `PUT_COMPILED_FILES_HERE.txt`, `01_FIGURE_NUMBERING.md` all gone |
| ☑ | No document names ScholarOne | **OK** — `submission_compact/README.md` rewritten; only `submission/` (the frozen base) still mentions it |
| ☑ | Decide the two uncited patents | **OK** — both now cited in Related Work, 2026-08-06 |
| ☑ | Make the GitHub repository public | **OK** — verified public via the GitHub API 2026-08-05 |
| ☑ | Tag `paper-submission-v1` and push | **OK** — re-tagged 2026-08-06 onto the vector-figure commit and verified live via the GitHub API |
| ☐ | Mint the Zenodo DOI | **optional** — `main.tex` contains no DOI and no placeholder, so nothing is broken without it. Nice to have, not required. |
| ☐ | Verify reviewer emails on faculty pages — **24 h before submitting**, not earlier | OPEN |
| ☐ | Select the mandatory editorial category in the portal | OPEN |
| ☐ | Elect traditional vs open access | OPEN |
| ☐ | iThenticate if VIT has access; overall similarity < 20 % | OPEN |
| ☐ | Spell-check | OPEN |
| ☐ | Read the compiled PDF cold, twice, with a night in between | OPEN |
| ☑ | Confirm PDF and source archive match exactly | **OK** — both written from one compile by `build_manuscript.py` |

## H. At acceptance, not now

| ✓ | Item | Detail |
|---|---|---|
| ☐ | IEEE Copyright Form (eCF) | Completed in-portal after acceptance |
| ☐ | Overlength page charges | $175 per page past 8 |
| ☐ | Open access fee | Only if elected |
| ☐ | Final Zenodo DOI | If not already added |

## I. After submission

- Manuscript ID arrives by email, typically within 24 h.
- Status moves to "Under Review" once an editor accepts the assignment,
  usually within about two weeks.
- **Do not contact the editor unless four months pass with no decision.**
- A desk reject inside two weeks usually means scope mismatch, page-limit
  violation, a missing graphical abstract, or an iThenticate flag.

---

## Status after the 2026-08-05 implementation pass

**Cleared:**

1. ~~`\revmode{track}`~~ → `clean`.
2. ~~Fig. 5 at 251 dpi~~ → 314 dpi.
3. ~~Figs. 1–2 at 296 dpi~~ → 315 dpi.
4. ~~Figure filenames~~ → renamed `fig1_`…`fig5_` in the source tree, with
   `\includegraphics` and `live_demo_sidebyside.py` updated to match.
5. ~~Reviewer-exclusion rationale cited "patent [13]"~~ → the Nunez patent is
   not cited, so it has no number; [13] is an unrelated in-ear EEG paper. Now
   named by title.

**Graphical abstract: CLOSED, accepted as-is 2026-08-05.**

It meets every mandatory requirement — 672 × 456 px, 35.2 kB, `gagraphic.png`,
26-word caption, no alpha, all eight printed values verified correct, readable
in greyscale, no compression artifacts.

Two cosmetic points were reviewed and deliberately not actioned:

1. *Small-text tier sits at roughly 6–7 px cap height* — small but legible at
   the display size. Note the preflight measures **ink extent, not point size**,
   so words lacking descenders ("awake") flag while the same-size word with one
   ("drowsy") does not. It is a tier indicator, not a font-size readout.
2. *"O1-O2 coherence falls with drowsiness" is blue at 3.26 : 1*, which fails
   WCAG AA for normal text. If the file is ever reopened, recolouring it to the
   body brown takes it to 9.78 : 1 and costs nothing. Not worth reopening for.

If a re-export ever happens: on the 2688 × 1824 master the 9 px floor is 36 px;
scale small text 1.3–1.5× and take the room from panel padding.

**Colour coding is *not* required — do not spend time restoring it.** Measured
WCAG contrast of the four colours in the current export, against the
`#F9FBFD` background:

| Colour | Used for | Contrast | Verdict |
|---|---|---|---|
| `#5F381E` | all body text | **9.78 : 1** | AAA — better than needed |
| `#658CD0` | band, pills, small caption, traces | **3.26 : 1** | large text only |
| `#C3CFE2` | panel borders | 1.52 : 1 | non-text, fine |

The 4-colour export lost the teal/vermilion channel and state coding, but that
coding was redundant: awake vs drowsy is carried by its two text labels and a
large amplitude difference, and O1 vs O2 by the labelled electrodes directly
above the traces. IEEE's own graphics guidance asks for meaning to be carried by
"both color and shape" and for figures to survive greyscale — which a two-colour
design satisfies by construction, and the greyscale render confirms.

The blue at 3.26 : 1 is fine behind the large band and pill type, but **fails AA
for normal-size text**, which is exactly what the small blue caption is. Making
it brown takes it to 9.78 : 1. That is less colour, not more.

**Patents — decided 2026-08-06.** `references.bib` holds 38 entries and now
cites all 38. `nunez2025patent` ("Headrest-integrated real-time alertness
prediction system") and `toyota2021patent` ("Drowsiness estimation device") were
previously uncited while the paper's stated novelty is a headrest EEG form
factor. Leaving the nearest prior art of that description unmentioned was judged
to read as evasive — particularly since P. L. Nunez is already on the reviewer
EXCLUDE list for a patent conflict. Both are now cited in Related Work
(Section~II-A), in a sentence that acknowledges the commercial interest in the
placement and distinguishes this work: a patent is not an evaluation, and
neither disclosure comes with a subject-independent benchmark on public data
against a behavioural anchor.

---

## Status after the 2026-08-06 pass

**Measured, then decided — the page count.** The previous plan was to cut
Tables III, VI and IX for "about 2 pages". Compiled and measured, that cut is
worth **zero printed pages**. The full ladder:

| Cut | Printed pages | Overlength |
|---|---|---|
| nothing (current) | 11 | $525 |
| Tables III + VI + IX | **11** | $525 |
| + Table IV | 11 | $525 |
| + Table VII (five tables gone) | 10 | $350 |
| all ten tables | 10 | $350 |
| all ten tables + one figure | 9 | $175 |
| **all fifteen floats** | **9** | $175 |
| all fifteen floats + the Limitations subsection | 8 | $0 |

The paper is prose-bound, not float-bound: 5,562 words of body text plus a
36-entry bibliography occupy 9 pages before a single float is placed. Reaching
8 pages therefore means deleting every figure, every table, *and* a discussion
subsection. **11 pages at $525 was accepted** rather than gutting the paper for
$525, and `build_manuscript.py` now gates on growth past 11 instead of on the
8-page limit — which is the failure that can still happen by accident.

**Also cleared this pass:** all five figures converted to vector PDF with
embedded TrueType fonts; the figure-generator seam closed so no manual
copy-and-rename step survives; six stale files deleted; `submission_compact/`
rewritten free of ScholarOne; both patents cited; repository re-tagged.

**Verification run 2026-08-06** — `preflight_ieee.py` 72 passed / 1 warning /
0 failures · `check_clean_render.py` 0 issues · `build_package.py` clean ·
`build_manuscript.py` 11 pages, 0 undefined refs, 0 overfull boxes, floats in
citation order, exit 0. The single warning is the graphical-abstract text-band
measurement, which is closed and accepted.
