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
> As of 2026-08-05 22:10 it reports **51 passed, 2 warnings, 0 failures**, plus
> 9 items it correctly refuses to auto-pass. Statuses below are from that run.

---

## A. Manuscript file and format

| ✓ | Requirement | Detail | Status |
|---|---|---|---|
| ☐ | Article type | Regular Paper | OPEN — select in portal |
| ☐ | Template | IEEE **double-column** style template. `\documentclass[journal]{IEEEtran}` | OK — set in `main.tex` |
| ☑ | PDF supplied | Compiled `main.pdf`, 871 kB | **OK** — `manuscript/main.pdf` |
| ☑ | Source supplied | LaTeX source **and** PDF are both required, and their content must match exactly | **OK** — both from one compile, `build_manuscript.py` |
| ☑ | Source archive contents | `main.tex`, `references.bib`, **`main.bbl`**, all five figures | **OK** — 8 files, 735 kB |
| ☑ | Total upload size | ≤ 40 MB per submission | OK — ~9 MB |
| ☑ | Filenames | No spaces; use underscores | OK |
| ☑ | Revision markup off | `\def\revmode{clean}` | **OK** — set 2026-08-05 |
| ☐ | Page limit | **8 pages** double-column for a Regular Paper | **FAIL — 11 pages, measured** |
| ☐ | Overlength budgeted | **$175 per page** beyond 8, mandatory at acceptance | **$525** — decide trim vs pay |

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
| ☐ | Uploaded individually | One file per figure, in figure order | OK — `figures/fig1…fig5` |
| ☐ | Accepted formats | PS, EPS, PDF, PNG, TIF | OK — PNG |
| ☑ | Resolution, colour/greyscale | **> 300 dpi** at printed size | **OK** — 315 / 315 / 394 / 394 / 314 dpi |
| ☑ | Resolution, line art | > 600 dpi | N/A — all figures are colour raster |
| ☑ | Column width | 3.5 in single column; **7.16 in** double column | OK |
| ☑ | No alpha channel | Flatten to RGB | OK — done in `build_package.py` |
| ☑ | Filenames match figure numbers | `fig1_`…`fig5_` | **OK** — renamed in source, `\includegraphics` updated |
| ☐ | Greyscale-safe | Distinguish by shape/position, not colour alone | OPEN — verify by eye |

**How the dpi failures were cleared (2026-08-05).**

- **Fig. 5** was 1800 px → 251 dpi. `live_demo_sidebyside.py` saved at `dpi=200`,
  but the figure is authored 9.0 in wide and placed at `\textwidth` = 7.16 in,
  so effective dpi is `dpi × 7.16/9.0`. Raised to `dpi=250` → 2250 × 825 px →
  **314 dpi**. Point sizes are unaffected, and the page-cost saving the compact
  rebuild was made for is preserved (5.95 col-in, down from 12.20).
- **Figs. 1–2** were 1035 px → 296 dpi, a 1.3 % shortfall from being authored at
  3.45 in and printed at 3.50 in. `reviewer_revision_analysis.py` raised from
  `dpi=300` to `dpi=320` → 1104 × 816 px → **315 dpi**. Re-run confirmed every
  number unchanged (F1 = 76.79, AUC = 76.62, κ = 0.539).

**Table float order — resolved, no problem.** Compiled 2026-08-05 with
tectonic. Figures land 1→p4, 2→p5, 3→p5, 4→p8, 5→p9 and tables I→p4, II→p4,
III→p5, IV→p6, V→p6, VI→p7, VII→p7, VIII→p7, IX→p7, X→p9. Both ascend
monotonically, so the full-width `table*` deferral I warned about did not
materialise. Printed order matches citation order.

**Compile is now reproducible.** `python build_manuscript.py` compiles with
tectonic (a single self-contained binary in `%LOCALAPPDATA%\tectonic`, no
MiKTeX), stages `manuscript/main.pdf` and `manuscript/main_source.zip` from the
*same* compile so they cannot drift apart, and reports page count, undefined
references, overfull boxes and float order. It exits non-zero while the paper is
over the page limit.

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
| ☐ | Legible at final size | 9 px minimum ink height as a working floor | **FAIL** — 8 of 16 lines are 6–8 px |
| ☐ | Numbers correct | Peer-reviewed claims, not typography | OK — all eight verified at 672 × 456 |
| ☐ | Greyscale-readable | IEEE converts to JPG; some readers print mono | OK |
| ☐ | No fabricated data | Generated charts are invented data | OK — all values are printed text; waveforms are schematic, no axes or units |

**To clear the legibility failure:** on the 2688 × 1824 master the 9 px floor is
**36 px**. Scale anything currently 24–28 px up by 1.3–1.5× and recover the room
from panel padding, not from panel size.

**Also worth fixing:** the current export quantised to a 4-colour palette, so
body text is brown `#5F381E` rather than near-black, O2 lost its teal green, and
"drowsy" lost its vermilion. Not a compliance failure — contrast is strong and
two colours are inherently colour-blind safe — but it loses the channel and
state coding. Export at 256 colours; it costs nothing at this file size.

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
| ☐ | Set `\revmode{clean}` and recompile | **OPEN** |
| ☐ | Apply the five figure renames | **OPEN** |
| ☐ | Re-render Fig. 5 at ≥ 2148 px | **OPEN** |
| ☐ | Fix graphical-abstract type sizes and re-export at 256 colours | **OPEN** |
| ☐ | Rebuild package: `python build_package.py --source submission_compact` | OPEN |
| ☐ | Check compiled page count against the 8-page limit | OPEN |
| ☐ | Check table numbers appear in citation order | OPEN |
| ☐ | Confirm no `?` citations in the PDF | OPEN |
| ☑ | Make the GitHub repository public | **OK** — verified public via the GitHub API 2026-08-05 |
| ☐ | Tag `paper-submission-v1` and push | **BLOCKER** — tag does not exist; only `milestone-v20-pre-tier1` and `milestone-tier1-submission-ready` do. `main.tex` §Reproducibility cites `paper-submission-v1` by name. Last push was 2026-07-25, so none of today's fixes are on the remote either. |
| ☐ | Mint the Zenodo DOI | **optional** — `main.tex` contains no DOI and no placeholder, so nothing is broken without it. Nice to have, not required. |
| ☐ | Fix two overfull tables | **BLOCKER** — Table II overflows its column by 40.77 pt (~0.56 in), Table III by 25.58 pt. Visible in the PDF. |
| ☐ | Verify reviewer emails on faculty pages — **24 h before submitting**, not earlier | OPEN |
| ☐ | iThenticate if VIT has access; overall similarity < 20 % | OPEN |
| ☐ | Spell-check | OPEN |
| ☐ | Read the compiled PDF cold, twice, with a night in between | OPEN |
| ☐ | Confirm PDF and source archive match exactly | OPEN |

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

**Known and intentional:** `references.bib` holds 38 entries, 36 cited. The two
uncited ones are patents (`nunez2025patent`, `toyota2021patent`). BibTeX omits
uncited entries, so they never reach the reference list — harmless. But see the
note below.

> **Worth a decision, not a fix.** `nunez2025patent` is titled
> "Headrest-integrated real-time alertness prediction system", and this paper's
> stated novelty is a headrest EEG form factor. Leaving known prior art of that
> description uncited is an editorial call the authors should make deliberately
> rather than by omission. Same question, more weakly, for
> `toyota2021patent` ("Drowsiness estimation device").
