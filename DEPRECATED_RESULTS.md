# DEPRECATED RESULTS — Do Not Cite

**Status:** Frozen for historical traceability only.
**Created:** 2026-04-20
**Reason:** Subject-level data leakage in the train/test protocol that produced these numbers.

---

## What is on this page

Every accuracy / precision / recall / F1 / false-alarm number listed below was computed with `sklearn.model_selection.train_test_split(test_size=0.2, random_state=42, stratify=y)` — i.e. a **stratified random split over epochs, with no grouping by subject**. Because the dataset contains many epochs per subject (60-second sliding windows with 30-second overlap), this protocol places epochs from the *same* subject in both training and test sets. The classifier therefore learns the subject's individual EEG signature rather than a generalisable awake-vs-drowsy boundary, which inflates every reported metric.

Under the correct **Leave-One-Subject-Out (LOSO)** protocol — train on 9 subjects, test on the held-out 10th, repeat — the same Random Forest on the same features collapses to roughly chance level on this dataset. See [publication_results_v2.json](publication_results_v2.json) for the honest numbers.

These deprecated numbers are preserved here so that:
- Reviewers tracing prior commits can see the methodological history;
- The course-submitted Capstone Report (now finalised) remains documented;
- Future authors do not re-derive them and quote them as if they were valid.

**They must not appear in the IEEE manuscript, in arXiv preprints, in conference posters, or in any future revision of [README.md](README.md) describing system performance.**

---

## The inflated numbers

### Phase B — "Headrest feasibility" (origin of the 89.54 % claim)

Source cells: notebook `EEG_Driver_Drowsiness_Detection.ipynb` cells 15 (full-cap) and 34 (O1/O2); also reproduced in [presentation_app.py:524](presentation_app.py#L524).

| Configuration | Channels | "Accuracy" (leaked) | Precision (awake / drowsy) | Recall (awake / drowsy) |
|---|---|---|---|---|
| Full-cap baseline | C3, C4, O1, O2 (8 features) | **91.32 %** | 95 % / 75 % | 94 % / 70 % |
| Headrest          | O1, O2 only (4 features)    | **89.54 %** | 94 % / 72 % | 93 % / 68 % |
| Reported drop     | 50 % sensor reduction        | **1.95 %**  | — | — |

Test set: 43,974 epochs across 10 subjects, drawn from the same pool used for training.

### Phase D — "Single-subject prediction validation" (origin of the 27-critical / 9.5 %-FA claims)

Source: notebook Phase D cells (≈ 45–47), also paraphrased in [README.md](README.md) and [WORK_DIARY.md](WORK_DIARY.md).

- Subject 07F: 62 alerts (15 Yellow, 20 Red, 27 Critical) over the drowsy session.
- Subject 01M awake session: 23 false alerts (20 Yellow, 3 Red, 0 Critical).
- Reported "false-alarm rate": **9.5 %** overall, **0 %** critical.

These come from a *single subject's* personal threshold (baseline × 1.5) being applied to that *same subject's* subsequent recording. They demonstrate the algorithm runs end-to-end, not that it generalises across subjects.

---

## What the honest LOSO numbers look like

From [publication_results_v2.json](publication_results_v2.json), 30-feature pipeline, 7 classifiers, LOSO cross-validation, 14,498 epochs:

| Model | LOSO accuracy | F1 (weighted) | AUC |
|---|---|---|---|
| Random Forest        | 50.72 % | 50.55 | 50.95 |
| (others, see JSON)   |   …     |   …   |   …   |

These are the numbers that any IEEE Sensors / TBME / Access reviewer will expect to see. They are not yet competitive — closing that gap is the work of the in-progress Phase 1–4 plan in the project's todo list.

---

## Files still containing the deprecated numbers (banner only, not rewritten)

| File | Rationale for leaving the numbers in place |
|---|---|
| [README.md](README.md)              | Banner added at top; full body retained for git-history readability. To be rewritten in Phase 6 once honest LOSO numbers are final. |
| [WORK_DIARY.md](WORK_DIARY.md)      | Banner added at top; the diary is a chronological record and rewriting it would erase context. |
| `EEG_Driver_Drowsiness_Detection.ipynb` cells 15, 34, and the Phase B summary markdown | `# DEPRECATED — SUBJECT-LEVEL LEAKAGE` comment added at the top of each leaking code cell. |
| [presentation_app.py](presentation_app.py) | Banner added at top of the Section-4 (sensor reduction) panel. The Streamlit demo is no longer the deliverable, so the underlying code is not re-engineered. |
| [report_helpers.py](report_helpers.py), [report_front_matter.py](report_front_matter.py), [report_chapters_1_3.py](report_chapters_1_3.py), [report_chapter4.py](report_chapter4.py), [report_chapters_5_6.py](report_chapters_5_6.py) | Capstone is submitted; these scripts are frozen historical artefacts. **Do not regenerate** [Capstone_Report.docx](Capstone_Report.docx) from them. |
| [GITHUB_UPLOAD_INSTRUCTIONS.md](GITHUB_UPLOAD_INSTRUCTIONS.md) | Internal note, not user-facing. |
| [Patent_Documentation/*.md](Patent_Documentation/) | Patent track is shelved; folder is preserved as a legacy reference. |

---

## What to do instead

1. The single source of truth for performance is [publication_results_v2.json](publication_results_v2.json) (after the Phase 1 rerun planned in the project todos).
2. All paper-bound figures must be regenerated by [publication_analysis.py](publication_analysis.py) (LOSO) or its successor — never from the Jupyter notebook's leaked cells.
3. Any new claim in the manuscript must be traceable to a JSON row produced by an LOSO loop with `subjects != test_subj` masking.
