"""Every number quoted in the manuscript, as LaTeX macros.

Reads results/*.json and writes manuscript/numbers.tex (with copies in
supplementary/ and response/). The documents print a value with \\res{key}; an
unknown key stops the pdfLaTeX build, so no number can be typed in by hand and
drift from the analysis.

Formatting: percentages to one decimal; kappa and correlations to two
decimals; p-values to two significant figures (three decimals below 0.1,
"<0.001" below that); counts with a thin-space thousands separator.

Output: manuscript/numbers.tex, supplementary/numbers.tex, response/numbers.tex
"""
import json
import os
import shutil
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

R1 = os.path.dirname(C.RESULTS)
OUT = os.path.join(R1, "manuscript", "numbers.tex")
OUT_SUPP = os.path.join(R1, "supplementary", "numbers.tex")
OUT_RESP = os.path.join(R1, "response", "numbers.tex")
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}

V = {}


def load(name):
    with open(os.path.join(C.RESULTS, f"{name}.json"), encoding="utf-8") as f:
        return json.load(f)


def pct(x):
    return f"{x:.1f}"


def dec2(x):
    s = f"{x:.2f}"
    return s.replace("-", "$-$") if s.startswith("-") else s


def pval(x):
    if x < 0.001:
        return "<0.001"
    if x < 0.1:
        return f"{x:.3f}"
    return f"{x:.2f}"


def count(n):
    s = f"{int(n):,}"
    return s.replace(",", "\\,")


def put(key, value):
    if key in V:
        raise KeyError(f"duplicate key {key}")
    V[key] = value


def metric_block(prefix, r):
    """Pooled and per-subject summary of one evaluate() result."""
    p = r["pooled"]
    put(f"{prefix}-auc", pct(p["AUC"]))
    put(f"{prefix}-f1", pct(p["F1w"]))
    if "BalAcc" in p:
        put(f"{prefix}-ba", pct(p["BalAcc"]))
        put(f"{prefix}-kappa", dec2(p["kappa"]))
    put(f"{prefix}-med", pct(r["subject_AUC_median"]))
    if "subject_AUC_IQR" in r:
        put(f"{prefix}-iqrlo", pct(r["subject_AUC_IQR"][0]))
        put(f"{prefix}-iqrhi", pct(r["subject_AUC_IQR"][1]))
    if "subjects_AUC_above_50" in r:
        put(f"{prefix}-above", str(r["subjects_AUC_above_50"]))
    if "n_subjects" in r:
        put(f"{prefix}-nsub", str(r["n_subjects"]))
    if "bootstrap" in r:
        put(f"{prefix}-cilo", pct(r["bootstrap"]["AUC_CI95"][0]))
        put(f"{prefix}-cihi", pct(r["bootstrap"]["AUC_CI95"][1]))


def paired_block(prefix, t, holm_key="p_holm", diff=pct):
    put(f"{prefix}-up", str(t["n_increase"]))
    put(f"{prefix}-down", str(t["n_decrease"]))
    put(f"{prefix}-n", str(t["n"]))
    put(f"{prefix}-p", pval(t["p_two_sided"]))
    put(f"{prefix}-meddiff", diff(t["median_diff"]))
    put(f"{prefix}-d", dec2(t["paired_d"]))
    if holm_key in t:
        put(f"{prefix}-holm", pval(t[holm_key]))
        put(f"{prefix}-star", "$^{*}$" if t[holm_key] < 0.05 else "")


DS = {"SEED-VIG": "seed", "DD-Database": "dd"}
CFG = {"LDA | lean10": "lean10", "LDA | no_COH (lean7)": "lean7", "LDA | no_ENT": "noent",
       "LDA | no_SLOPE": "noslope", "LDA | no_PAF": "nopaf", "LDA | ENT_only": "entonly",
       "LDA | SLOPE_only": "slopeonly", "LDA | PAF_only": "pafonly", "LDA | COH_only": "cohonly",
       "LogReg | lean10": "logreg", "RandomForest | lean10": "rf", "GradBoost | lean10": "gb",
       "LDA | ext50": "ext50", "LDA | ext50_no_COH": "ext50nocoh", "LDA | BASE30_only": "base30",
       "LDA | DWT10_only": "dwt10"}


def datasets():
    dd = load("dd_labels")
    ex = load("dd_extract")
    put("dd-epochs", count(ex["n_epochs"]))
    put("dd-trials", str(ex["n_trials"]))
    put("dd-drowsy", count(dd["totals"]["n_drowsy"]))
    put("dd-alert", count(dd["totals"]["n_alert"]))
    put("dd-labeled", count(dd["totals"]["n_drowsy"] + dd["totals"]["n_alert"]))
    put("dd-unlab", count(dd["totals"]["n_unlabelled"]))
    pr = [v["n_genuine_presses"] for v in dd["per_trial"].values()]
    put("dd-presses-min", str(min(pr)))
    put("dd-presses-max", str(max(pr)))
    put("dd-presses-total", str(sum(pr)))
    put("dd-presses-median", f"{np.median(pr):g}")
    put("dd-presses-incal", str(sum(len(v["presses_inside_calibration_window"]) for v in dd["per_trial"].values())))
    st = [v["start_marker_s"] for v in dd["per_trial"].values()]
    put("dd-start-lo", f"{min(st):g}")
    put("dd-start-hi", f"{max(st):g}")
    ps = dd["per_subject"]
    prev = [100 * v["n_drowsy"] / (v["n_drowsy"] + v["n_alert"]) for v in ps.values()]
    put("dd-prev-lo", f"{min(prev):.0f}")
    put("dd-prev-hi", f"{max(prev):.0f}")
    for g, v in dd["sensitivity_grid"].items():
        put(f"dd-grid-{g.replace('_', '-')}-nsub", str(v["subjects_with_both_classes"]))

    sp = load("seed_prepare")
    put("seed-epochs", count(sp["n_epochs"]))
    put("seed-awake", count(sp["n_awake"]))
    put("seed-drowsy", count(sp["n_drowsy"]))
    put("seed-ids", str(sp["n_subject_ids"]))
    put("seed-recordings", str(sp["n_recordings"]))
    put("seed-test-ids", str(sp["n_test_subjects"]))
    put("seed-single-class", " and ".join(sp["single_class_subject_ids"]))
    tc = sp["per_subject_counts"]
    test = sp["subject_ids_with_both_classes"]
    put("seed-test-epochs", count(sum(tc[s]["n_awake"] + tc[s]["n_drowsy"] for s in test)))
    put("seed-test-drowsy", count(sum(tc[s]["n_drowsy"] for s in test)))
    put("seed-test-awake", count(sum(tc[s]["n_awake"] for s in test)))
    prev = [100 * tc[s]["n_drowsy"] / (tc[s]["n_drowsy"] + tc[s]["n_awake"]) for s in test]
    put("seed-prev-lo", f"{min(prev):.0f}")
    put("seed-prev-hi", f"{max(prev):.0f}")


def monitoring():
    m = load("monitoring")["results"]
    for ds, short in DS.items():
        for name, r in m[ds]["configs"].items():
            metric_block(f"{short}-{CFG[name]}", r)
        for name, t in m[ds]["comparisons_vs_lean10_LDA"].items():
            paired_block(f"{short}-{CFG[name]}-vs", t)
        put(f"{short}-ncomp", str(len(m[ds]["comparisons_vs_lean10_LDA"])))


def time_on_task():
    a = load("alarms")
    for ds, short in DS.items():
        s = a[ds]["time_on_task"]["summary"]
        put(f"tot-{short}-n", str(s["n"]))
        put(f"tot-{short}-time-med", pct(s["time"]))
        put(f"tot-{short}-time-above", str(s["time_above_50"]))
        for k, lab in (("eeg", "eeg"), ("eeg_ema", "ema")):
            put(f"tot-{short}-{lab}-med", pct(s[k]))
            put(f"tot-{short}-{lab}-beats", str(s[f"{k}_beats_time"]))
            put(f"tot-{short}-{lab}-p", pval(s[f"{k}_vs_time"]["p_two_sided"]))


def alarm_figures():
    """Exploratory alarm analysis: kept for the author notes, not printed in the paper."""
    for target, block in load("alarms")["DD-Database"]["alarms"].items():
        t = target.split()[0]
        for name, key in (("time on task", "clock"), ("EEG", "eeg"), ("EEG + EMA", "ema")):
            put(f"alarm-{t}h-{key}-hit", pct(block[name]["hit_rate"]))
            put(f"alarm-{t}h-{key}-fa", f"{block[name]['false_alarms_per_h']:.1f}")


def baselines():
    b = load("baselines_dd")["results"]
    for name, key in (("Riemannian TS + LDA", "rieml"), ("Riemannian TS + LogReg", "riemlr"), ("EEGNet", "eegnet")):
        metric_block(f"dd-{key}", b[name])
    put("rt-eegnet-min", f"{b['EEGNet']['elapsed_s'] / 60:.0f}")
    best = [f["best_epoch"] for f in b["EEGNet"].get("training", [])]
    if best:
        put("dd-eegnet-best-lo", str(min(best)))
        put("dd-eegnet-best-hi", str(max(best)))
        put("dd-eegnet-best-med", f"{np.median(best):.0f}")


def offsets():
    """Pooled AUC without driver offsets, and each baseline against the lean-10 LDA per driver."""
    o = load("offsets")
    for name, key in (("Lean-10 LDA", "lean10"), ("Riemannian TS + LDA", "rieml"), ("Riemannian TS + LogReg", "riemlr"),
                      ("EEGNet", "eegnet")):
        r = o["DD-Database"][name]
        put(f"off-{key}-centred", pct(r["pooled_AUC_offsets_removed"]))
        put(f"off-{key}-rho", dec2(r["rho_mean_score_drowsy_share"]))
        if name in o["versus_lean10"]:
            paired_block(f"dd-{key}-vs", o["versus_lean10"][name])


def per_subject():
    ps = load("per_subject")["results"]
    for ds, short in DS.items():
        rows = ps[ds]["lean10"]["per_subject"]
        for s, v in rows.items():
            put(f"{short}-s{s}-auc", pct(v["AUC"]))
            put(f"{short}-s{s}-recd", pct(v["recall_drowsy"]))
            put(f"{short}-s{s}-reca", pct(v["recall_alert"]))
            put(f"{short}-s{s}-precd", pct(v["precision_drowsy"]))
        for k in ("precision_drowsy", "recall_drowsy", "precision_alert", "recall_alert"):
            put(f"{short}-med-{k.replace('_', '')}", pct(np.median([v[k] for v in rows.values()])))
        low_recall = [s for s, v in rows.items() if v["recall_drowsy"] < 20]
        put(f"{short}-recd-lt20-n", str(len(low_recall)))
        low_recall_good_auc = [s for s in low_recall if rows[s]["AUC"] >= 65]
        put(f"{short}-recd-lt20-auc65-n", str(len(low_recall_good_auc)))
        below55 = sorted([s for s, v in rows.items() if v["AUC"] < 55], key=lambda s: rows[s]["AUC"])
        put(f"{short}-below55-n", str(len(below55)))
        put(f"{short}-below55-list", ", ".join(below55))


def tau():
    t = load("tau_sweep")
    for ds, short in DS.items():
        r = t["results"][ds]
        for tau_s, v in r["fixed_tau_sweep"].items():
            put(f"{short}-tau{tau_s}-auc", pct(v["pooled"]["AUC"]))
            put(f"{short}-tau{tau_s}-f1", pct(v["pooled"]["F1w"]))
            put(f"{short}-tau{tau_s}-med", pct(v["subject_AUC_median"]))
            put(f"{short}-tau{tau_s}-above", str(v["subjects_AUC_above_50"]))
        best = max(r["fixed_tau_sweep"].items(), key=lambda kv: kv[1]["pooled"]["AUC"])
        put(f"{short}-taubest", best[0])
        bestmed = max(r["fixed_tau_sweep"].items(), key=lambda kv: kv[1]["subject_AUC_median"])
        put(f"{short}-taubestmed", bestmed[0])
        n = r["nested"]
        metric_block(f"{short}-nested", n["result"])
        vals = n["chosen_tau_values"]
        put(f"{short}-nested-taus", f"{min(vals)}--{max(vals)}" if len(vals) > 1 else str(vals[0]))
        put(f"{short}-nested-ntaus", str(len(vals)))
        chosen = [v["tau"] for v in n["chosen_tau_per_outer_subject"].values()]
        for tau_s in t["taus_s"]:
            put(f"{short}-nested-tau{tau_s}-count", str(chosen.count(tau_s)))
        paired_block(f"{short}-nested-vs", n["vs_unsmoothed_per_subject_AUC"])
        ps0 = load("per_subject")["results"][ds]["lean10"]["per_subject"]
        for s, v in n["result"]["per_subject"].items():
            put(f"{short}-s{s}-nauc", pct(v["AUC"]))
        worse = [s for s in ps0 if n["result"]["per_subject"][s]["AUC"] < ps0[s]["AUC"]]
        put(f"{short}-nested-worse-list", ", ".join(sorted(worse, key=lambda s: ps0[s]["AUC"])))
    put("tau-grid", ", ".join(str(x) for x in t["taus_s"]))


def coherence():
    c = load("coherence_stats")["results"]
    for ds, short in DS.items():
        for band, v in c[ds].items():
            pre = f"{short}-coh-{band}"
            paired_block(pre, v["subject_level"], diff=lambda x: f"{x:+.3f}".replace("-", "$-$"))
            # p < 10^k with k = ceil(log10 p), so the printed bound is always true
            put(f"{pre}-mwexp", f"{int(np.ceil(v['epoch_level_mannwhitney_log10p']))}")
            put(f"{pre}-ac", dec2(v["lag1_autocorr_mean"]))
            put(f"{pre}-aclo", dec2(v["lag1_autocorr_range"][0]))
            put(f"{pre}-achi", dec2(v["lag1_autocorr_range"][1]))
            put(f"{pre}-nep", count(v["n_epochs"]))
        ac = [v["lag1_autocorr_mean"] for v in c[ds].values()]
        put(f"{short}-coh-ac-lo", dec2(min(ac)))
        put(f"{short}-coh-ac-hi", dec2(max(ac)))
        mw = [v["epoch_level_mannwhitney_log10p"] for v in c[ds].values()]
        put(f"{short}-coh-mwexp-max", f"{int(np.ceil(max(mw)))}")


REF = {"MSC O1-O2": "msc", "zero-lag share O1-O2": "zls", "ImCoh O1-O2": "imcoh", "wPLI O1-O2": "wpli",
       "MSC C3-C4": "c3c4", "MSC O1-C3": "o1c3", "MSC O2-C4": "o2c4", "MSC O1-C4": "o1c4", "MSC O2-C3": "o2c3",
       "MSC O1-O2 (common-average ref)": "car"}


def reference():
    r = load("reference")["results"]
    for name, v in r.items():
        meas, band = name.rsplit(" ", 1)
        pre = f"ref-{REF[meas]}-{band}"
        put(f"{pre}-mean", dec2(v["mean_all_labelled"]))
        put(f"{pre}-alert", f"{v['alert_mean']:.3f}")
        put(f"{pre}-drowsy", f"{v['drowsy_mean']:.3f}")
        s = v["subject_level"]
        put(f"{pre}-up", str(s["n_increase"]))
        put(f"{pre}-n", str(s["n"]))
        put(f"{pre}-p", pval(s["p_two_sided"]))
        put(f"{pre}-d", dec2(s["paired_d"]))
        put(f"{pre}-holmb", pval(s["p_holm_bands"]))
        put(f"{pre}-holma", pval(s["p_holm_all"]))
    zl = [v["mean_all_labelled"] for k, v in r.items() if k.startswith("zero-lag")]
    put("ref-zls-lo", f"{100 * min(zl):.0f}")
    put("ref-zls-hi", f"{100 * max(zl):.0f}")
    put("ref-ntests", str(len(r)))
    # The abstract spells this count out; all three lag-insensitive measures must agree.
    up = {r[f"{m} beta"]["subject_level"]["n_increase"] for m in ("ImCoh O1-O2", "wPLI O1-O2", "MSC O1-O2 (common-average ref)")}
    if len(up) != 1:
        raise ValueError(f"lag-insensitive measures disagree on drivers up: {up}; reword the abstract")
    put("ref-beta-up-word", WORDS[up.pop()])
    put("ref-beta-n-word", WORDS[r["ImCoh O1-O2 beta"]["subject_level"]["n"]])


def join_list(items):
    items = [str(x) for x in items]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + (", and " if len(items) > 2 else " and ") + items[-1]


def calibration():
    full = load("calibration")
    c = full["results"]
    real = full["dd_presses_during_calibration"]
    scored = [x for x in real if x["this_trial"]["AUC"] is not None]
    if len(scored) != 1:
        raise ValueError("the text of Section III-F assumes one scorable trial with a press during calibration")
    x = scored[0]
    put("dd-realpress-n", WORDS[len(real)])
    put("dd-realpress-driver", x["this_trial"]["trial"].split("_")[0])
    put("dd-realpress-auc", pct(x["this_trial"]["AUC"]))
    put("dd-realpress-other-auc", pct(x["other_trial"]["AUC"]))
    put("dd-realpress-alert", str(x["this_trial"]["n_alert"]))
    cond = {"standard": "std", "at_1800": "t30", "at_3600": "t60", "drowsy_labelled": "drowsy",
            "before_first_press": "prepress"}
    for ds, short in DS.items():
        for fs, block in c[ds].items():
            for k, v in block.items():
                pre = f"{short}-cal-{cond[k]}-{fs}"
                put(f"{pre}-auc", pct(v["pooled"]["AUC"]))
                put(f"{pre}-f1", pct(v["pooled"]["F1w"]))
                put(f"{pre}-ba", pct(v["pooled"]["BalAcc"]))
                put(f"{pre}-kappa", dec2(v["pooled"]["kappa"]))
                put(f"{pre}-med", pct(v["subject_AUC_median"]))
                put(f"{pre}-used", str(v["subjects_with_variant_window"]))
            alt = [v["subject_AUC_median"] for k, v in block.items() if k != "standard"]
            put(f"{short}-cal-alt-{fs}-medlo", pct(min(alt)))
            put(f"{short}-cal-alt-{fs}-medhi", pct(max(alt)))


def transfer():
    x = load("cross_dataset")["results"]
    for name, v in x.items():
        fs, direction = name.split(": ")
        key = "dd2seed" if direction.startswith("DD") else "seed2dd"
        metric_block(f"xfer-{key}-{fs}", v)
    # Calibration-window length (Supplementary S11): win-<what>-<dataset varied><seconds>-auc|med
    tags = {"SEED-VIG LOSO": "seed-loso", "DD-Database LOSO": "dd-loso",
            "DD-Database -> SEED-VIG": "dd2seed", "SEED-VIG -> DD-Database": "seed2dd"}
    for name, v in load("cross_dataset")["calibration_window_sensitivity"].items():
        what, window = name.split(" | ")
        varied = "dd" if window.startswith("DD") else "seed"
        pre = f"win-{tags[what]}-{varied}{window.split()[-2]}"
        put(f"{pre}-auc", pct(v["pooled_AUC"]))
        put(f"{pre}-med", pct(v["subject_AUC_median"]))


def ensemble():
    e = load("ensemble")
    names = {"M1 lean-10 LDA": "m1", "M2 Riemannian TS+LDA": "m2", "M3 EMA (nested tau)": "m3",
             "average": "avg", "stacked LDA (LOSO)": "stack"}
    for name, v in e["summary"].items():
        k = names[name]
        put(f"ens-{k}-auc", pct(v["pooled_AUC"]))
        put(f"ens-{k}-f1", pct(v["F1w"]))
        put(f"ens-{k}-med", pct(v["subject_AUC_median"]))
        put(f"ens-{k}-acc", pct(v["accuracy"]))
    for name, v in e["pairs"].items():
        a, b = name.split(" ~ ")
        k = names[a] + names[b]
        put(f"ens-{k}-r", dec2(v["posterior_r"]))
        put(f"ens-{k}-rw", dec2(v["posterior_r_within_subject_median"]))
        put(f"ens-{k}-er", dec2(v["error_r"]))
        put(f"ens-{k}-q", dec2(v["yules_Q"]))
        put(f"ens-{k}-dis", pct(100 * v["disagreement"]))
        put(f"ens-{k}-df", pct(100 * v["double_fault"]))
    put("ens-oracle", pct(e["oracle_accuracy"]))
    acc = e["member_accuracy_on_best_member_errors"]
    put("ens-m1-on-m3err", pct(acc["M1 lean-10 LDA"]))
    put("ens-m2-on-m3err", pct(acc["M2 Riemannian TS+LDA"]))


def sensitivity():
    s = load("sensitivity")
    for g, v in s["S3_label_grid"].items():
        pre = f"sens-{g.replace('_', '-')}"
        put(f"{pre}-auc", pct(v["pooled_AUC"]))
        put(f"{pre}-f1", pct(v["F1w"]))
        put(f"{pre}-med", pct(v["subject_AUC_median"]))
        put(f"{pre}-above", str(v["subjects_AUC_above_50"]))
        put(f"{pre}-nsub", str(v["n_subjects"]))
    full = [v["subject_AUC_median"] for v in s["S3_label_grid"].values() if v["n_subjects"] == 10]
    put("sens-grid-full-lo", pct(min(full)))
    put("sens-grid-full-hi", pct(max(full)))
    part = [v["subject_AUC_median"] for v in s["S3_label_grid"].values() if v["n_subjects"] < 10]
    put("sens-grid-part-lo", pct(min(part)))
    put("sens-grid-part-hi", pct(max(part)))
    u = s["S4_unfiltered"]["unfiltered"]
    put("sens-unfilt-auc", pct(u["pooled_AUC"]))
    put("sens-unfilt-f1", pct(u["F1w"]))
    put("sens-unfilt-med", pct(u["subject_AUC_median"]))
    put("sens-unfilt-above", str(u["subjects_AUC_above_50"]))
    for ds, short in DS.items():
        v = s["S9_nested_feature_set"][ds]
        put(f"sens-nfs-{short}-auc", pct(v["result"]["pooled_AUC"]))
        put(f"sens-nfs-{short}-med", pct(v["result"]["subject_AUC_median"]))
        put(f"sens-nfs-{short}-lean7n", str(sum(x == "lean7" for x in v["chosen_per_outer_subject"].values())))
        put(f"sens-nfs-{short}-n", str(len(v["chosen_per_outer_subject"])))


def runtime():
    r = load("runtime")
    pe = r["per_epoch"]
    put("rt-lean10-ms", f"{pe['lean10_feature_extraction']['median_ms']:.0f}")
    put("rt-lean10-p95", f"{pe['lean10_feature_extraction']['p95_ms']:.0f}")
    put("rt-ext50-ms", f"{pe['ext50_feature_extraction']['median_ms']:.0f}")
    put("rt-lda-us", f"{1000 * pe['lda_posterior']['median_ms']:.0f}")
    put("rt-ema-us", f"{1000 * pe['ema_update']['median_ms']:.1f}")
    put("rt-model-bytes", str(r["model_size"]["lda_weights_and_bias_float32_bytes"]))
    put("rt-cal-bytes", str(r["model_size"]["per_driver_calibration_mean_sd_float32_bytes"]))
    put("rt-pct-realtime", f"{100 * r['real_time_factor_lean10']:.2f}")
    put("rt-python", r["machine"]["python"])


def label_runs():
    full = load("label_runs")
    r = full["results"]
    for ds, short in DS.items():
        for cls in ("alert", "drowsy"):
            v = r[ds][cls]
            put(f"{short}-run-{cls}-med", f"{v['median_run_s']:.0f}")
            put(f"{short}-run-{cls}-wmed", f"{v['epoch_weighted_median_run_s']:.0f}")
            put(f"{short}-run-{cls}-n", str(v["n_runs"]))
    w = full["seed_calibration_windows"]
    n_late = len(w["late_start_s"])
    put("seed-win-n", str(w["n_recordings"]))
    put("seed-win-ontime-n", str(w["n_recordings"] - n_late))
    put("seed-win-late-n", WORDS[n_late])
    put("seed-win-late-list", join_list(f"{t:.0f}" for t in w["late_start_s"]))
    put("seed-win-alldrowsy-n", WORDS[len(w["all_drowsy_window_subjects"])])
    put("seed-win-alldrowsy-list", join_list(w["all_drowsy_window_subjects"]))
    put("seed-win-short-n", WORDS[w["n_windows_under_6_epochs"]])
    put("seed-win-latetest-list", join_list(sorted(w["late_start_test_subjects"], key=int)))
    e = w["without_late_test_subjects"]
    put("seed-win-excl-nsub", str(e["n_subjects"]))
    put("seed-win-excl-auc", pct(e["pooled_AUC"]))
    put("seed-win-excl-med", pct(e["subject_AUC_median"]))


def main():
    datasets()
    label_runs()
    monitoring()
    baselines()
    per_subject()
    tau()
    coherence()
    reference()
    calibration()
    transfer()
    ensemble()
    sensitivity()
    time_on_task()
    offsets()
    alarm_figures()
    runtime()
    lines = [
        "% Generated by analysis/40_numbers.py from results/*.json. Do not edit.",
        "\\makeatletter",
        "\\DeclareRobustCommand{\\res}[1]{\\@ifundefined{res@#1}"
        "{\\PackageError{numbers}{Unknown result key #1}{Run analysis/40_numbers.py}}"
        "{\\@nameuse{res@#1}}}",
    ]
    for k in sorted(V):
        v = V[k]
        if v.startswith("<"):
            v = "{<}" + v[1:]
        lines.append(f"\\@namedef{{res@{k}}}{{{v}}}")
    lines.append("\\makeatother")
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    shutil.copyfile(OUT, OUT_SUPP)
    os.makedirs(os.path.dirname(OUT_RESP), exist_ok=True)
    shutil.copyfile(OUT, OUT_RESP)
    print(f"wrote {len(V)} values to {os.path.relpath(OUT, os.path.dirname(R1))} and the two copies")


if __name__ == "__main__":
    main()
