# Submission declarations — IEEE Sensors Journal

This file consolidates the four declaration paragraphs the portal will request. Each is also embedded in the manuscript at the appropriate section (cover letter, acknowledgements, dedicated declaration sections at the end of the paper). Drop-in copies for the portal text fields are below.

---

## 1. Author contributions (CRediT-aligned)

**M. R. Thalassery (first author):** conceptualization, methodology, software, validation, formal analysis, investigation, data curation, writing — original draft, writing — review & editing, visualization.

**S. S. Ali (second author):** software (feature extraction, live demonstrator), validation, writing — review & editing.

**A. R. Pal (corresponding author, last):** supervision, conceptualization (driver-monitoring framing), methodology guidance, writing — review & editing, project administration.

All authors have read and approved the final manuscript and the listed authorship order.

---

## 2. Conflicts of interest

The authors declare no conflicts of interest, financial or otherwise, related to the content of this manuscript. None of the authors has a financial relationship with any commercial driver-monitoring vendor, EEG hardware manufacturer, or automotive OEM.

---

## 3. Funding

This work received no external funding. The work was conducted as the corresponding-undergraduate-capstone project of the first and second authors at the School of Mechanical Engineering, Vellore Institute of Technology (VIT) Chennai, under the supervision of the third author. No part of the manuscript preparation was supported by industry sponsorship.

---

## 4. Data and code availability

**Datasets.** This work uses two publicly-available datasets, neither of which is redistributed in the submission package or supplementary materials.

- **DROZY** (Université de Liège). Original publication: Massoz et al., IEEE WACV 2016. Available under the dataset's published terms of use; access requires acceptance of the ULg licence. We use only the publicly-distributable EEG modality and only the O₁ and O₂ channels.
- **SEED-VIG** (Shanghai Jiao Tong University, BCMI Lab). Original publication: Zheng & Lu, J. Neural Eng. 2017. Available under the BCMI-Lab data-use agreement; access requires application to BCMI. We use only the EEG O₁/O₂ subset and the published PERCLOS annotations.

**Code.** All analysis scripts, pinned dependencies (`requirements.txt`), and a single-entry reproducer (`reproduce.py`) are released at `https://github.com/MuhammedRaslan/Pro-Active-Driver-Monitoring-System-Using-EEG`. The exact commit corresponding to the submitted manuscript will be tagged `paper-submission-v1` and archived at Zenodo with a DOI prior to acceptance. The reproducer regenerates every numbered figure and JSON result file from the raw EDF/MAT inputs in approximately 5 minutes (excluding the ~28-minute EEGNet baseline) on a laptop CPU.

**Per-subject feature caches** (DROZY: `features_v9_cache.npz`, 14 498 epochs × 50 features; SEED-VIG: `features_seed_vig_cache.npz`, 9 155 epochs × 10 features) are not redistributed but regenerate automatically once the raw datasets are placed under `DROZY_O1_O2/` and `Raw_Data/` of the repository, per the README instructions.

**Trained models.** The 10 LDA coefficients and the per-subject z-score statistics are derived deterministically from the dataset under each LOSO fold and are reproducible by re-running the pipeline. We therefore do not release frozen `.pkl` model files; they would not be more authoritative than the reproducer output.

---

## 5. Ethics

The data analysed in this work were collected in third-party studies under their respective ethics approvals (DROZY: Université de Liège IRB; SEED-VIG: Shanghai Jiao Tong University ethics committee). No new human-subjects data were collected for this manuscript. The authors did not interact with the dataset participants.

---

## 6. AI-assistance disclosure

The authors used Anthropic's Claude language model as a software-engineering and writing-review assistant during the development of this work. Claude was used to (a) accelerate Python implementation of feature-extraction and analysis scripts, (b) draft portions of code documentation, and (c) review prose drafts for clarity and consistency. All algorithm choices, experimental designs, statistical analyses, and final scientific conclusions are the authors' own. All AI-generated text was reviewed, edited, and verified by the authors before inclusion in the manuscript. The use of AI assistance is consistent with IEEE's current guidance on author use of generative AI tools.
