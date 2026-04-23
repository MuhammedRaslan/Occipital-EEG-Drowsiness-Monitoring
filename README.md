# Pro-Active Driver Monitoring System Using EEG

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Research_Publication-blue.svg)]()

**A novel headrest-based EEG drowsiness detection system that predicts driver drowsiness 5-10 minutes in advance using minimal sensors (O1/O2 occipital channels).**

> 📄 **Publication Status:** Research manuscript in preparation — targeting **IEEE Sensors Journal** submission (2026)

> ⚠️ **Important — accuracy figures below are deprecated.**
> The headline accuracies on this page (89.54 %, 91.32 %, the "1.95 % drop", and the Phase D single-subject 27-critical / 9.5 %-FA numbers) were computed with a stratified random train/test split that mixed epochs from the **same** subjects across train and test — i.e. **subject-level data leakage**. Under proper Leave-One-Subject-Out cross-validation the same models score around chance level on the same data. See [DEPRECATED_RESULTS.md](DEPRECATED_RESULTS.md) for the full record and explanation, and [publication_results_v2.json](publication_results_v2.json) for the honest LOSO numbers. The body of this README has not yet been rewritten — it will be once the new LOSO results are final. **Do not cite the numbers below.**

---

## 🎯 Project Overview

This project develops and validates a **proactive driver drowsiness detection system** that:
- Uses only **2 EEG sensors** (O1/O2 occipital positions) embedded in vehicle headrest
- **Predicts drowsiness 5-10 minutes in advance** (not just current-state detection)
- Achieves **89.54% accuracy** with minimal 2-channel configuration
- Reduces sensor count by **50%** compared to traditional 4-channel systems
- Enables **cost-effective deployment** in consumer vehicles ($100-500 per unit)

### Key Innovation: Temporal Trend Analysis

Unlike reactive camera-based systems, our approach uses **temporal trend analysis** of EEG biomarkers (theta/alpha power) to forecast future drowsiness state, providing advance warning for preventive intervention.

---

## 📊 Performance Results

### Classification Accuracy (Phase B)

| Configuration | Channels | Accuracy | Precision | Recall | Performance Drop |
|--------------|----------|----------|-----------|--------|------------------|
| **Full-Cap Baseline** | 4 (C3, C4, O1, O2) | 91.32% | 95% / 75% | 94% / 70% | - |
| **Headrest System** | 2 (O1, O2 only) | **89.54%** | 94% / 72% | 93% / 68% | **1.95%** ✅ |

**Test Dataset:** DROZY (10 subjects, 43,974 epochs, awake vs. drowsy sessions)

**Key Finding:** Only 1.95% accuracy drop with 50% sensor reduction → **Excellent for patent viability**

### Real-Time Prediction Validation (Phase D)

**Single-Subject Validation - DROZY Subject 07F:**
- **Calibration:** Session 1 awake baseline (theta/alpha = 1.1225) → Session 2 drowsy test
- **Threshold:** 1.6837 (50% increase from baseline)
- **Prediction Results:** 62 total predictions across 90-minute session
  - Yellow alerts: 15 (5-10 min advance warning)
  - Red alerts: 20 (<5 min warning)
  - **Critical alerts: 27** (imminent drowsiness moments)
- **False Alarm Testing:** 9.5% overall false alarm rate, **0% critical false alarms** ✅
- **Status:** ✅ **Validated** - Algorithm correctly predicts drowsiness onset

**Multi-Subject Exploration:**
- **DROZY (5 subjects):** Dataset limitation found - both sessions induce drowsiness
- **SEED-VIG (23 experiments):** Explored alternative dataset
  - Best result: 40.4% detection, 35% false alarms
  - Root cause: Differential Entropy features show only 1% effect size
  - Conclusion: DROZY power spectral density (PSD) features superior for O1/O2 headrest

**Final Assessment:** Single-subject DROZY validation (Steps 2-3) provides strong patent evidence. Multi-subject exploration demonstrates due diligence and dataset-specific adaptation.

---

## 🧠 Technical Approach

### System Architecture

```
EEG Sensors (O1/O2) → Signal Acquisition → Preprocessing → Feature Extraction → Temporal Analysis → Prediction → Graduated Alerts
```

### Signal Processing Pipeline

1. **Electrode Placement:** O1/O2 (occipital lobe, International 10-20 system)
2. **Sampling:** 128 Hz acquisition with 16-24 bit ADC
3. **Preprocessing:** 1-40 Hz bandpass filtering, artifact rejection (>100 μV)
4. **Feature Extraction:** 
   - Theta power (4-8 Hz) - drowsiness marker
   - Alpha power (8-13 Hz) - drowsiness marker
   - Theta/alpha ratio - strong drowsiness indicator
   - Welch's PSD over 60-second sliding windows (30-second overlap)
5. **Classification:** Random Forest classifier (89.54% accuracy)
6. **Temporal Prediction:**
   - Rolling 5-minute history buffer
   - Linear regression on biomarker trends
   - Time-to-threshold extrapolation
   - **5-10 minute advance prediction**

### Graduated Alert System

| Alert Level | Prediction Horizon | Visual | Audio | Action |
|-------------|-------------------|--------|-------|--------|
| **Yellow Warning** | ~10 minutes ahead | Yellow icon | Gentle chime | Suggest rest stop |
| **Red Alert** | ~5 minutes ahead | Red flashing | Urgent beep | Pull over now |
| **Critical** | Current drowsiness | Red continuous | Loud alarm | STOP immediately |

---

## 🗂️ Repository Structure

```
Pro-Active-Driver-Monitoring-System-Using-EEG/
├── README.md                                  # This file
├── EEG_Driver_Drowsiness_Detection.ipynb     # Main analysis notebook
├── WORK_DIARY.md                              # Complete project log
├── extract_O1_O2_channels.py                  # Dataset preparation script
│
├── DROZY_O1_O2/                               # Extracted EEG data (O1/O2 only)
│   ├── 01M_1_O1_O2.edf                       # Subject 01, awake session
│   ├── 01M_2_O1_O2.edf                       # Subject 01, drowsy session
│   └── ... (10 subjects × 2 sessions)
│
├── Patent_Documentation/                      # Patent filing materials
│   ├── PATENT_OUTLINE.md                     # Master roadmap
│   ├── PATENT_TECHNICAL_SPECS.md             # Hardware/software specs
│   ├── PATENT_PRIOR_ART.md                   # Prior art analysis
│   ├── PATENT_CLAIMS.md                      # 33 patent claims
│   ├── PATENT_FIGURES.md                     # 8 figure specifications
│   ├── PATENT_DETAILED_DESCRIPTION.md        # Complete technical description
│   ├── PATENT_PROVISIONAL_FILING_GUIDE.md    # IPO filing instructions
│   └── PATENT_FORMS_TEMPLATE.md              # Forms 1/2/3 templates
│
└── .gitignore                                 # Git ignore rules
```

---

## 🚀 Getting Started

### Prerequisites

```bash
Python 3.8+
MNE-Python 1.x
NumPy
Pandas
Matplotlib
Scikit-learn
SciPy
```

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/YOUR_USERNAME/Pro-Active-Driver-Monitoring-System-Using-EEG.git
cd Pro-Active-Driver-Monitoring-System-Using-EEG
```

2. **Install dependencies:**
```bash
pip install mne numpy pandas matplotlib scikit-learn scipy
```

3. **Open Jupyter Notebook:**
```bash
jupyter notebook EEG_Driver_Drowsiness_Detection.ipynb
```

### Running the Analysis

The notebook is organized in phases:

- **Phase 1-5:** ML baseline (data loading, preprocessing, feature extraction, classification)
- **Phase A:** EEG fundamentals and visualization
- **Phase B:** Headrest sensor feasibility (O1/O2 only vs. full-cap)
- **Phase C:** Proactive prediction (temporal trend analysis, 5-10 min ahead)
- **Phase D:** Real-time algorithm validation (single/multi-subject prediction testing)
  - Step 1: Core prediction algorithms implemented
  - Steps 2-3: DROZY single-subject validation (✅ 27 critical detections, 9.5% false alarms)
  - Step 4: Multi-subject calibration exploration (5 strategies, dataset limitation found)
  - Steps 5-6: SEED-VIG alternative dataset validation (40.4% best result)
- **Phase E:** Real-time simulation animation (demonstration dashboard)

Run all cells sequentially to reproduce the **89.54% accuracy** result and validation outcomes.

---

## 📁 Dataset Information

### DROZY Dataset (Occipital Channels Only)

The repository includes **O1/O2 channel extracts** from the DROZY dataset:

- **10 subjects** (6 male, 4 female)
- **2 sessions per subject:**
  - Session 1 (_1.edf): Awake/alert state
  - Session 2 (_2.edf): Drowsy/fatigued state
- **Channels:** O1, O2 (occipital electrodes only)
- **Sampling rate:** 128 Hz
- **Total epochs:** 43,974 (83% awake, 17% drowsy)

**Original full dataset:** [DROZY Database](https://www.physionet.org/content/drozy/1.0.0/)

> **Note:** We extracted only O1/O2 channels to reduce repository size and focus on headrest-relevant sensors. Original DROZY includes C3, C4, Cz, EOG, and other channels.

---

## 🏆 Key Results & Findings

### 1. Minimal Sensor Configuration Validated
- **50% sensor reduction** (4 → 2 channels) with only **1.95% accuracy loss**
- O1/O2 occipital placement captures drowsiness effectively
- Validates headrest-embedded sensor feasibility

### 2. Proactive Prediction Demonstrated
- Theta/alpha power shows **measurable upward trends** over time in drowsy states
- Temporal slope analysis enables **5-10 minute advance forecasting**
- Linear regression on rolling 5-minute buffer predicts drowsiness onset

### 3. Commercial Viability
- System cost: **$100-500** (vs. $5,000-50,000 for multi-channel EEG)
- Non-invasive headrest integration (no gel, no cap)
- Suitable for mass automotive deployment

### 4. Competitive Advantage
- **Proactive vs. Reactive:** Most systems detect current drowsiness; we predict 5-10 min ahead
- **Minimal sensors:** 2 channels vs. 8-32 in research systems
- **Camera limitations:** Works in dark, with sunglasses, no privacy concerns

---

## 📄 Publication Strategy

### Status: Manuscript in Preparation (2026)

**Target Venue:** IEEE Sensors Journal / Expert Systems with Applications / EMBC 2026  
**Paper Type:** Full Research Article  
**Contribution Type:** Novel Method + Experimental Validation

### Key Differentiators vs. Prior Work

| Feature | Our System | Neurovigil (2025) | Toyota (2021) | Camera Systems |
|---------|------------|-------------------------------|---------------------------|----------------|
| **Prediction Timeline** | 5-10 min advance | Generic "prediction" | Current state only | Current state only |
| **Sensor Count** | 2 channels | Multi-modal (EEG/EOG/EMG) | MEG (expensive) | None (camera) |
| **Cost** | $100-500 | $1,000+ | $10,000+ | $200-1,000 |
| **Accuracy** | 89.54% | Not disclosed | Not disclosed | 70-85% |

### Research Contributions (for Paper)

1. **Temporal Trend Extrapolation:** First demonstration of linear regression on rolling EEG biomarker history to predict time-to-drowsiness 5-10 minutes ahead
2. **Minimal Sensor Configuration:** Rigorous validation that 2-channel (O1/O2) achieves 89.54% accuracy — only 1.95% below 4-channel baseline
3. **Graduated Alert Framework:** Yellow (10 min) → Red (5 min) → Critical (now) with 0% critical false alarms

### Paper Outline

1. **Abstract** — Problem, method, key results (89.54%, 5-10 min ahead, 0% critical FA)
2. **Introduction** — Drowsiness statistics, reactive vs. proactive detection gap
3. **Related Work** — Prior EEG drowsiness systems, sensor minimization, temporal prediction
4. **Methodology** — O1/O2 placement, PSD feature extraction, temporal regression algorithm
5. **Experiments** — DROZY dataset, classification (Phase B), prediction validation (Phase D)
6. **Results & Discussion** — Accuracy tables, prediction timeline, false alarm analysis
7. **Conclusion & Future Work** — Hardware prototype, multi-subject generalization

**Submission Timeline:**
- ✅ Technical validation complete: March 2026
- 🔜 Manuscript draft: April 2026
- 🔜 Internal review & revision: May 2026
- 🔜 Journal submission: June 2026

---

## 🔬 Validation Methodology

### Dataset: DROZY
- **Realistic simulation:** Subjects performed monotonous driving simulation tasks
- **Controlled drowsiness induction:** Session 2 recorded after sleep deprivation
- **Ground truth labels:** Expert annotation of awake vs. drowsy states

### Metrics:
- **Accuracy:** 89.54% (overall classification correctness)
- **Precision:** 94% awake, 72% drowsy
- **Recall:** 93% awake, 68% drowsy
- **F1-Score:** Balanced performance across classes
- **Confusion Matrix:** 43,974 epochs analyzed

### Cross-Validation:
- 10-subject leave-one-out validation
- Ensures generalization across individuals

---

## 🛠️ Future Work

### Phase D: Real-Time Processing (Optional)
- Implement embedded system (ARM Cortex-M4)
- Measure latency and computational requirements
- Create demonstration dashboard

### Phase F: Hardware Prototype (Optional)
- Design dry electrode integration in headrest fabric
- Test electrode-scalp contact quality during actual driving
- Validate wireless data transmission
- Build proof-of-concept demonstrator

### Phase G: Enhanced Features (Future Research)
- Frontal electrodes for emotional state detection
- Camera fusion for multi-modal system
- Personalized calibration algorithms
- Cloud-based fleet monitoring analytics

---

## 📚 Related Publications & References

### Prior Art (Key Patents):
1. **US12446811B2 (Neurovigil, 2025):** Multi-modal biosignal headrest system
2. **US11091168B2 (Toyota, 2021):** Magnetoencephalography-based drowsiness detection
3. **US10143401B2 (Bosch, 2018):** Camera-based driver monitoring
4. **US9974479B2 (Seeing Machines, 2018):** Eye tracking driver state estimation

### Academic References:
1. Lin et al. (2013): "EEG-based drowsiness estimation for safety driving using independent component analysis"
2. Mu et al. (2017): "Drowsiness detection based on EEG signal"
3. Sahayadhas et al. (2012): "Detecting driver drowsiness based on sensors"

### Datasets:
- **DROZY:** Real driving simulation with drowsiness annotation
- **SEED-VIG:** Vigilance estimation dataset (alternative)

---

## 🤝 Contributing

This is currently a research project with pending patent protection. Contributions will be welcome after patent filing is complete.

For inquiries, please contact via GitHub Issues.

---

## 📄 License & Open Science

**Status:** Open Research (MIT License)

This repository contains:
- ✅ **Fully open source:** EEG analysis code, methodology, and extracted dataset
- ✅ **Reproducible research:** All results can be reproduced by running the Jupyter notebook sequentially
- ✅ **Dataset included:** DROZY O1/O2 channel extracts (20 EDF files)

**If you use this work, please cite the paper once published.**

---

## 📞 Contact & Support

**Project Creator:** Muhammad  
**Institution:** [Your University]  
**Repository:** https://github.com/YOUR_USERNAME/Pro-Active-Driver-Monitoring-System-Using-EEG

**Citation:**
```bibtex
@misc{proactive_dms_2026,
  author = {Muhammad},
  title = {Pro-Active Driver Monitoring System Using EEG: 5-10 Minute Advance Drowsiness Prediction with Minimal Sensors},
  year = {2026},
  publisher = {GitHub},
  url = {https://github.com/YOUR_USERNAME/Pro-Active-Driver-Monitoring-System-Using-EEG}
}
```

---

## 🎯 Project Timeline

- **March 5, 2026:** Project initiated
- **March 5, 2026:** Technical validation complete (Phases A, B, C) — 89.54% accuracy
- **March 11, 2026:** Phase D prediction algorithm validation complete
  - Single-subject DROZY validation: ✅ 27 critical detections, 9.5% false alarms
  - Multi-subject exploration: DROZY + SEED-VIG datasets tested
  - Root cause analysis: PSD vs. Differential Entropy feature comparison documented
- **March 17, 2026:** Pivot to research publication — manuscript preparation begins
- **April 2026:** Research manuscript draft (target)
- **May 2026:** Internal review and revision
- **June 2026:** Journal submission (target)

---

## 🏅 Achievements

✅ **Technical:** 89.54% accuracy with 50% sensor reduction  
✅ **Innovation:** 5-10 minute advance prediction capability validated  
✅ **Real-Time Validation:** 27 critical drowsiness detections, 9.5% false alarm rate, 0% critical false alarms  
✅ **Dataset Exploration:** DROZY + SEED-VIG comparative analysis complete  
✅ **Reproducibility:** All code and data included for full result replication  
✅ **Cost-Effectiveness:** $100-500 system cost for mass deployment  
✅ **Publication Ready:** Technical contributions drafted and ready for manuscript  

---

## ⭐ Acknowledgments

- **DROZY Dataset:** Researchers at CTU in Prague for drowsiness EEG data
- **MNE-Python:** Open-source EEG analysis framework
- **Indian Patent Office:** Patent filing resources and procedures

---

## 📊 Repository Statistics

- **Languages:** Python (Jupyter Notebook), Markdown
- **Lines of Code:** ~2,000 (analysis notebook)
- **Documentation:** 60,000+ words (patent + technical docs)
- **Dataset:** 20 EDF files (O1/O2 extracts, ~15-25 MB)
- **Figures:** 8 specified (to be drawn for complete specification)

---

**⚡ This project demonstrates the feasibility of low-cost, proactive driver drowsiness detection using minimal EEG sensors embedded in vehicle headrests. Patent protection ensures commercial viability while advancing automotive safety research.**

**📢 Star ⭐ this repository if you find it useful!**
