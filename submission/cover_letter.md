# Cover letter — IEEE Sensors Journal submission

**Manuscript:** Pro-Active Driver Drowsiness Monitoring Using Two-Channel Occipital EEG
**Authors:** Muhammed Raslan Thalassery, Sulaiman Shiyas Ali, Abhishek Rudra Pal, G. Murali Mohan
**Affiliation:** School of Mechanical Engineering (SMEC), Vellore Institute of Technology (VIT) Chennai, Vandalur–Kelambakkam Road, Chennai 600127, Tamil Nadu, India
**Corresponding author:** Dr. Abhishek Rudra Pal (abhishek.rudrapal@vit.ac.in)
**Date:** [TODO insert at submission]

---

Dear Editor-in-Chief,

We submit for your consideration the enclosed manuscript titled **"Pro-Active Driver Drowsiness Monitoring Using Two-Channel Occipital EEG"** for publication in the IEEE Sensors Journal.

**The contribution.** This work develops and validates a deployment-oriented EEG pipeline for in-vehicle drowsiness detection using two occipital electrodes (O₁ and O₂) integrated into a vehicle headrest. The pipeline combines a 10-feature shrinkage LDA classifier (sample/permutation entropy, aperiodic 1/f slope, peak-alpha-frequency difference, and inter-hemispheric coherence in three bands) with a causal exponential moving-average smoother and a per-driver percentile-calibrated alarm threshold. Two complementary tracks are reported. The monitoring track achieves a weighted F1 of 76.79 % under strict leave-one-subject-out cross-validation on DROZY (10 subjects, 14 498 epochs) — statistically superior to the unsmoothed lean-feature baseline (paired Wilcoxon p = 0.005, Cohen's d = 1.11) and to a tuned Riemannian and an EEGNet baseline — and 66.13 % on a pooled 31-subject DROZY ∪ SEED-VIG benchmark. The pro-active track, evaluated on SEED-VIG under a survival-framed FPR-controlled protocol, flags drowsiness with a median lead of +8.83 min (0.0 % per-session false alerts) on 71.4 % of sessions against the earliest behavioural sign of drowsiness (PERCLOS > 0.30), and +31.67 min (9.5 % false alerts) on 85.7 % of sessions against the severe fighting-sleep threshold.

**The novelty.** To our knowledge this is the first paper to report a behaviour-anchored, FPR-controlled, survival-framed advance-prediction evaluation on SEED-VIG, and to quantify the per-driver-calibration and causal-smoothing contributions to subject-independent F1 with paired statistical tests. The pro-active protocol replaces the unprotected uncontrolled framing common in the prior literature, in which advance leads were reported against unspecified or per-subject-fitted behavioural thresholds and censored evidence was silently dropped. We further report two honest negative ablations — phase-coherence variants (PLV / ImCoh / wPLI) and a three-model posterior ensemble — that bound the optimisation envelope of a 2-channel occipital pipeline and justify the lean-LDA-plus-EMA architecture as the deployable choice rather than an under-engineered one.

**Fit to IEEE Sensors Journal.** The work is a direct fit for the journal's focus on practical sensor-data pipelines with deployment constraints. The pipeline runs at 56 ms per 10-second epoch on a laptop CPU with approximately 100 bytes of trained model state, suitable for an ARM Cortex-M4 deployment target; per-driver calibration adds ~5 kB per driver and refits in milliseconds via closed-form Ledoit–Wolf shrinkage. The headrest form factor avoids facial imaging (a privacy advantage under emerging biometric-data regulations) and avoids direct scalp-electrode contact with hair (the dominant failure mode for dry-EEG signal quality). The work originates from the School of Mechanical Engineering at VIT Chennai with an explicit automotive-sensor integration framing.

**Declarations.**

- This manuscript has not been published or submitted elsewhere; an earlier version of this work appears solely as a university capstone thesis at VIT Chennai, which is not considered prior publication under IEEE policy.
- All authors have approved the submission and agreed to the listed authorship order.
- The authors declare no conflicts of interest. No external funding was received for this work.
- All analysis scripts, pinned dependencies, and a single-entry reproducer are released at `https://github.com/MuhammedRaslan/Pro-Active-Driver-Monitoring-System-Using-EEG` (Zenodo DOI to be added after submission acceptance).
- We have respected the data-use agreements for DROZY and SEED-VIG; no raw data is redistributed in the submission package.

We have suggested reviewers and excluded conflicts in the submission portal accordingly. We thank you for considering our manuscript.

Sincerely,

Dr. Abhishek Rudra Pal
School of Mechanical Engineering
Vellore Institute of Technology (VIT) Chennai
Chennai 600127, Tamil Nadu, India
ORCID: [TODO]
Email: abhishek.rudrapal@vit.ac.in

On behalf of co-authors:
Muhammed Raslan Thalassery (ORCID: [TODO])
Sulaiman Shiyas Ali (ORCID: [TODO])
G. Murali Mohan (ORCID: [TODO])
