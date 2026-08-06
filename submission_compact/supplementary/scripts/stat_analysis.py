"""
Statistical Rigor (Phase 3c)
=============================
Post-hoc analysis of the v3-v9 publication_results_*.json files.

Outputs (into publication_results_v10.json and a printed table):
  * Per-model: mean ± std ± 95% CI of per-subject accuracy (t-distribution)
  * Paired Wilcoxon signed-rank test between the current best (v9 LDA)
    and every other pipeline, across the 10 subjects.
  * Cohen's d (paired) between v9 LDA and every other pipeline.
  * Summary table ready for the IEEE Results section.

This script reads only existing JSONs — no new training runs.
"""

import os, sys, io, json
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
from scipy import stats

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_FILE = os.path.join(_SCRIPT_DIR, "publication_results_v10.json")
SUBJECTS = ["01M","02F","03F","04M","05M","06M","07F","08M","09M","10M"]


def load_version(v):
    path = os.path.join(_SCRIPT_DIR, f"publication_results_{v}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def per_subject_accs(model_entry):
    """Return (subject -> accuracy) dict from a model_comparison entry."""
    if "per_subject" not in model_entry:
        return None
    return {r["subject"]: r["accuracy"] for r in model_entry["per_subject"]}


def ci95(a):
    """Two-sided 95% CI for the mean, t-distribution."""
    a = np.asarray(a, dtype=float)
    n = len(a)
    if n < 2:
        return float(a.mean()), 0.0, 0.0
    m = a.mean()
    se = a.std(ddof=1) / np.sqrt(n)
    half = stats.t.ppf(0.975, df=n-1) * se
    return float(m), float(m - half), float(m + half)


def cohens_d_paired(a, b):
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    d = a - b
    if d.std(ddof=1) < 1e-12:
        return 0.0
    return float(d.mean() / d.std(ddof=1))


# ─── harvest every (version, model) pair with per_subject data ──────────
COMPARISON_SPECS = [
    # (version, models_of_interest, short_label_fn)
    ("v3",  ["Gradient Boosting", "Random Forest"],                         lambda m: f"v3 {m}"),
    ("v4",  ["LDA"],                                                         lambda m: f"v4 {m} (subject_both)"),
    ("v5",  ["LDA", "Logistic Regression"],                                  lambda m: f"v5 {m} (subject_awake)"),
    ("v6",  ["TS + LDA (Riemann)", "TS + LogReg (Riemann)", "MDM (Riemann)"], lambda m: f"v6 {m}"),
    ("v7",  ["TS+LDA (Riemann, tuned)", "TS+LogReg (Riemann, tuned)"],       lambda m: f"v7 {m}"),
    ("v9",  ["LDA (shrinkage=auto)", "LogReg (C=1, bal)"],                   lambda m: f"v9 {m} (50 features)"),
]

entries = []   # list of (label, subject->acc dict, headline metrics dict)
for v, models, lbl_fn in COMPARISON_SPECS:
    doc = load_version(v)
    if doc is None:
        continue
    mc = doc.get("model_comparison", {})
    for m in models:
        if m not in mc:
            continue
        ps = per_subject_accs(mc[m])
        if ps is None:
            continue
        entries.append({
            "label": lbl_fn(m),
            "per_subject": ps,
            "metrics": {k: mc[m][k] for k in
                        ("accuracy", "f1_score", "auc_roc", "kappa", "precision", "recall")
                        if k in mc[m]},
        })

# ─── also load v8 (structured differently: sweeps/cal_60s/LDA) ─────────
v8 = load_version("v8")
if v8 is not None and "sweeps" in v8:
    for key, bucket in v8["sweeps"].items():
        for m in ("LDA", "LogReg"):
            if m not in bucket: continue
            ps = per_subject_accs(bucket[m])
            if ps is None: continue
            entries.append({
                "label": f"v8 {m} ({key})",
                "per_subject": ps,
                "metrics": {k: bucket[m][k] for k in
                            ("accuracy", "f1_score", "auc_roc", "kappa", "precision", "recall")
                            if k in bucket[m]},
            })

# ─── also load v11 ablations (structured as ablations/<label>/{...}) ───
v11 = load_version("v11")
if v11 is not None and "ablations" in v11:
    for key, bucket in v11["ablations"].items():
        ps = per_subject_accs(bucket)
        if ps is None: continue
        entries.append({
            "label": f"v11 LDA [{key}]",
            "per_subject": ps,
            "metrics": {k: bucket[k] for k in
                        ("accuracy", "f1_score", "auc_roc", "kappa", "precision", "recall")
                        if k in bucket},
        })

# ─── also load v14 EEGNet (top-level overall + per_subject) ────────────
v14 = load_version("v14")
if v14 is not None and "per_subject" in v14:
    ps = {r["subject"]: r["accuracy"] for r in v14["per_subject"]}
    entries.append({
        "label": "v14 EEGNet (raw, LOSO)",
        "per_subject": ps,
        "metrics": {k: v14["overall"][k] for k in
                    ("accuracy", "f1_score", "auc_roc", "kappa", "precision", "recall")
                    if k in v14["overall"]},
    })

# ─── per-model CI table, sorted by F1 descending ────────────────────────
def label_sort_key(e):
    return -e["metrics"].get("f1_score", 0.0)

entries.sort(key=label_sort_key)

print("="*100)
print("PER-MODEL SUMMARY (sorted by weighted F1, best first)")
print("="*100)
print(f"{'Model':<55}  {'F1%':>6}  {'Acc%':>6}  {'AUC%':>6}  {'κ':>6}  {'mean±CI95 (per-subj acc)':<28}")
print("-" * 100)
for e in entries:
    accs = np.array(list(e["per_subject"].values()), dtype=float)
    mu, lo, hi = ci95(accs)
    m = e["metrics"]
    print(f"{e['label']:<55}  "
          f"{m.get('f1_score','-'):>6}  "
          f"{m.get('accuracy','-'):>6}  "
          f"{m.get('auc_roc','-'):>6}  "
          f"{m.get('kappa','-'):>6}  "
          f"{mu:5.2f} [{lo:5.2f}, {hi:5.2f}]")

# ─── paired tests against v11 ENT+SLOPE+COH lean (new headline) ────────
ref = next((e for e in entries if e["label"].startswith("v11 LDA [ONLY ENT+SLOPE+COH")), None)
if ref is None:
    ref = next((e for e in entries if e["label"].startswith("v9 LDA")), None)
if ref is None:
    print("\n(no v9 LDA entry found; skipping paired tests)")
else:
    ref_accs = [ref["per_subject"][s] for s in SUBJECTS if s in ref["per_subject"]]
    print()
    print("="*100)
    print(f"PAIRED TESTS vs REFERENCE = {ref['label']}")
    print("="*100)
    print(f"{'Comparator':<55}  {'Δmean':>7}  {'Wilcoxon p':>11}  {'paired d':>9}")
    print("-" * 100)
    pair_rows = []
    for e in entries:
        if e["label"] == ref["label"]:
            continue
        other_accs = [e["per_subject"].get(s) for s in SUBJECTS]
        if any(a is None for a in other_accs):
            continue
        diffs = np.array(ref_accs) - np.array(other_accs)
        try:
            w_stat, p_val = stats.wilcoxon(ref_accs, other_accs, zero_method="wilcox",
                                           alternative="greater")
        except ValueError:
            w_stat, p_val = float("nan"), float("nan")
        d = cohens_d_paired(ref_accs, other_accs)
        pair_rows.append({"comparator": e["label"],
                          "delta_mean": float(diffs.mean()),
                          "wilcoxon_p_ref_greater": float(p_val),
                          "paired_cohens_d": float(d)})
        print(f"{e['label']:<55}  {diffs.mean():+7.2f}  {p_val:>11.4f}  {d:>+9.3f}")

# ─── persist ────────────────────────────────────────────────────────────
payload = {
    "note": "Post-hoc statistical rigor for paper Results section.",
    "generated_from_versions": ["v3","v4","v5","v6","v7","v8","v9","v11","v14"],
    "subjects": SUBJECTS,
    "per_model": [
        {
            "label": e["label"],
            "metrics": e["metrics"],
            "per_subject_acc": e["per_subject"],
            "per_subject_acc_mean": round(float(np.mean(list(e["per_subject"].values()))), 2),
            "per_subject_acc_std":  round(float(np.std(list(e["per_subject"].values()))),  2),
            "per_subject_acc_ci95": list(ci95(list(e["per_subject"].values()))),
        }
        for e in entries
    ],
    "reference_label": ref["label"] if ref is not None else None,
    "paired_vs_reference": pair_rows if ref is not None else [],
}
with open(RESULTS_FILE, "w") as f:
    json.dump(payload, f, indent=2)
print(f"\nWrote {RESULTS_FILE}")
