"""
Runtime / Latency / Memory Benchmark (Phase 3d)
================================================
Measures per-epoch cost for each stage of the v9 extended-feature
pipeline, so the IEEE paper's "real-time embedded" claim is backed
by actual numbers rather than asserted.

Stages timed:
  1. Welch PSD (for band powers, spectral entropy, aperiodic slope, peak alpha)
  2. Hjorth parameters
  3. Zero-crossing + skewness
  4. DWT sub-band energies
  5. Sample entropy
  6. Permutation entropy
  7. Aperiodic 1/f slope regression
  8. Peak alpha frequency
  9. Per-channel feature assembly (all-in-one)
 10. Cross-channel coherence
 11. Full 50-feature extraction (per 10 s epoch)
 12. Per-subject z-score scaling
 13. Trained LDA predict_proba (single epoch)

Memory:
  * Size of loaded model (.pkl)
  * Estimated feature-vector footprint per epoch

Output: runtime_benchmark.json
"""

import os, sys, io, json, time, pickle, tempfile, warnings
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
import pywt
import antropy as ant
from scipy.signal import welch, coherence
from scipy.integrate import trapezoid
from scipy.stats import entropy as sp_entropy, skew, linregress
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from datetime import datetime

warnings.filterwarnings("ignore")

FS          = 128
EPOCH_SEC   = 10
N_SAMPLES   = FS * EPOCH_SEC      # 1280
N_FEATS_V9  = 50
WARMUP_N    = 20
TRIALS_N    = 500
BANDS       = {"delta":(0.5,4), "theta":(4,8), "alpha":(8,13), "beta":(13,30)}

rng = np.random.default_rng(42)

def make_signal():
    return rng.standard_normal(N_SAMPLES).astype(np.float64)


def band_power(sig, fs, band):
    f, p = welch(sig, fs, nperseg=min(int(fs*2), len(sig)))
    m = (f >= band[0]) & (f <= band[1])
    return float(trapezoid(p[m], f[m])) if m.sum() > 0 else 0.0

def welch_psd(sig, fs):
    return welch(sig, fs, nperseg=min(int(fs*2), len(sig)))

def spectral_entropy(sig, fs):
    f, p = welch_psd(sig, fs)
    m = (f >= 0.5) & (f <= 40)
    p_norm = p[m] / (p[m].sum() + 1e-12)
    return float(sp_entropy(p_norm + 1e-12))

def hjorth_params(sig):
    d1 = np.diff(sig); d2 = np.diff(d1)
    activity   = np.var(sig)
    mobility   = np.sqrt(np.var(d1) / (activity + 1e-12))
    complexity = np.sqrt(np.var(d2) / (np.var(d1) + 1e-12)) / (mobility + 1e-12)
    return activity, mobility, complexity

def zcr(sig):
    return float(np.sum(np.diff(np.sign(sig)) != 0)) / len(sig)

def dwt_energies(sig):
    coeffs = pywt.wavedec(sig, "db4", level=5)
    return [float(np.sum(c**2)) for c in coeffs[:5]]

def aperiodic_slope(sig, fs, fmin=2.0, fmax=40.0):
    f, p = welch_psd(sig, fs)
    m = (f >= fmin) & (f <= fmax)
    lr = linregress(np.log10(f[m] + 1e-12), np.log10(p[m] + 1e-12))
    return float(lr.slope)

def peak_alpha_freq(sig, fs):
    f, p = welch_psd(sig, fs)
    m = (f >= 8.0) & (f <= 13.0)
    return float(f[m][np.argmax(p[m])]) if m.any() else 0.0

def band_coherence(o1, o2, fs, band):
    f, cxy = coherence(o1, o2, fs=fs, nperseg=min(int(fs*2), len(o1)))
    m = (f >= band[0]) & (f <= band[1])
    return float(np.mean(cxy[m])) if m.any() else 0.0


def time_it(fn, trials=TRIALS_N, warmup=WARMUP_N):
    for _ in range(warmup):
        fn()
    t0 = time.perf_counter_ns()
    for _ in range(trials):
        fn()
    elapsed_ns = time.perf_counter_ns() - t0
    return (elapsed_ns / trials) / 1e6   # ms per call


def full_feature_extraction(o1, o2, fs):
    feats = {}
    for ch_name, sig in [("O1", o1), ("O2", o2)]:
        for bname, brand in BANDS.items():
            feats[f"{bname}_{ch_name}"] = band_power(sig, fs, brand)
        th = feats[f"theta_{ch_name}"]; al = feats[f"alpha_{ch_name}"]; be = feats[f"beta_{ch_name}"]
        feats[f"theta_alpha_ratio_{ch_name}"] = th / (al + 1e-12)
        feats[f"slow_fast_ratio_{ch_name}"]   = (th + al) / (al + be + 1e-12)
        feats[f"spectral_entropy_{ch_name}"]  = spectral_entropy(sig, fs)
        a, m, c = hjorth_params(sig)
        feats[f"hjorth_activity_{ch_name}"]   = a
        feats[f"hjorth_mobility_{ch_name}"]   = m
        feats[f"hjorth_complexity_{ch_name}"] = c
        feats[f"zcr_{ch_name}"] = zcr(sig)
        feats[f"skewness_{ch_name}"] = float(skew(sig))
        for k, e in enumerate(dwt_energies(sig)):
            feats[f"dwt_{k}_{ch_name}"] = e
        feats[f"sample_entropy_{ch_name}"] = float(ant.sample_entropy(sig, order=2))
        feats[f"perm_entropy_{ch_name}"]   = float(ant.perm_entropy(sig, order=3, normalize=True))
        feats[f"aperiodic_slope_{ch_name}"] = aperiodic_slope(sig, fs)
    for bname in ["theta", "alpha", "beta"]:
        p1 = feats[f"{bname}_O1"]; p2 = feats[f"{bname}_O2"]
        feats[f"asymmetry_{bname}"] = (p1 - p2) / (p1 + p2 + 1e-12)
    feats["mean_theta_alpha_ratio"] = (feats["theta_alpha_ratio_O1"] + feats["theta_alpha_ratio_O2"]) / 2
    feats["total_theta"] = feats["theta_O1"] + feats["theta_O2"]
    feats["total_alpha"] = feats["alpha_O1"] + feats["alpha_O2"]
    feats["paf_delta"] = abs(peak_alpha_freq(o1, fs) - peak_alpha_freq(o2, fs))
    feats["coh_theta"] = band_coherence(o1, o2, fs, BANDS["theta"])
    feats["coh_alpha"] = band_coherence(o1, o2, fs, BANDS["alpha"])
    feats["coh_beta"]  = band_coherence(o1, o2, fs, BANDS["beta"])
    return feats


print("="*80)
print("RUNTIME / LATENCY / MEMORY BENCHMARK (Phase 3d)")
print("="*80)
print(f"Timestamp: {datetime.now()}")
print(f"Epoch: {EPOCH_SEC}s @ {FS}Hz ({N_SAMPLES} samples); "
      f"warmup={WARMUP_N}, trials={TRIALS_N}")
print()

o1 = make_signal(); o2 = make_signal()
stages = [
    ("welch PSD (single)",      lambda: welch_psd(o1, FS)),
    ("band power (1 band)",     lambda: band_power(o1, FS, BANDS["alpha"])),
    ("spectral entropy",        lambda: spectral_entropy(o1, FS)),
    ("Hjorth params",           lambda: hjorth_params(o1)),
    ("ZCR",                     lambda: zcr(o1)),
    ("skewness",                lambda: float(skew(o1))),
    ("DWT energies (db4, L=5)", lambda: dwt_energies(o1)),
    ("sample entropy (m=2)",    lambda: ant.sample_entropy(o1, order=2)),
    ("perm entropy (order=3)",  lambda: ant.perm_entropy(o1, order=3, normalize=True)),
    ("aperiodic slope",         lambda: aperiodic_slope(o1, FS)),
    ("peak alpha freq",         lambda: peak_alpha_freq(o1, FS)),
    ("coherence (1 band)",      lambda: band_coherence(o1, o2, FS, BANDS["alpha"])),
]

timings = []
for name, fn in stages:
    ms = time_it(fn)
    timings.append({"stage": name, "ms_per_call": round(ms, 3)})
    print(f"  {name:32s} {ms:7.3f} ms")

print()
full_ms = time_it(lambda: full_feature_extraction(o1, o2, FS), trials=200, warmup=5)
timings.append({"stage": "FULL 50-feature extraction (per 10s epoch)", "ms_per_call": round(full_ms, 3)})
print(f"  {'FULL 50-feature extraction':32s} {full_ms:7.3f} ms per epoch")
print(f"  {'=> real-time factor':32s} {full_ms / (EPOCH_SEC*1000):.6f} "
      f"(< 1.0 means processing is faster than real-time)")

# ── train-once-and-predict latency ───────────────────────────────────────
X_train = rng.standard_normal((14498, N_FEATS_V9))
y_train = rng.integers(0, 2, size=14498)
clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
t0 = time.perf_counter()
clf.fit(X_train, y_train)
train_s = time.perf_counter() - t0
print(f"\n  {'LDA fit on 14498x50':32s} {train_s*1000:7.2f} ms (one-time)")

x_test = rng.standard_normal((1, N_FEATS_V9))
predict_ms = time_it(lambda: clf.predict_proba(x_test), trials=2000, warmup=50)
print(f"  {'LDA predict_proba (1 epoch)':32s} {predict_ms*1000:7.3f} µs")

# ── end-to-end per-epoch latency ────────────────────────────────────────
def end_to_end():
    f = full_feature_extraction(o1, o2, FS)
    x = np.array([f[k] for k in sorted(f.keys())]).reshape(1, -1)
    # need exactly 50 features
    x = x[:, :N_FEATS_V9] if x.shape[1] >= N_FEATS_V9 else np.pad(x, ((0,0),(0,N_FEATS_V9-x.shape[1])))
    return clf.predict_proba(x)

e2e_ms = time_it(end_to_end, trials=200, warmup=5)
print(f"  {'END-TO-END (features + predict)':32s} {e2e_ms:7.3f} ms per epoch")

# ── memory footprint ────────────────────────────────────────────────────
with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tmp:
    pickle.dump(clf, tmp)
    model_bytes = os.path.getsize(tmp.name)
    tmp_path = tmp.name
os.unlink(tmp_path)

feat_vec_bytes = 50 * 8   # float64
cov_mem_bytes  = 2 * 2 * 8  # 2x2 cov matrix
print(f"\n  {'Serialized LDA model size':32s} {model_bytes / 1024:7.2f} KB")
print(f"  {'Feature vector (50 x float64)':32s} {feat_vec_bytes:7d} B")
print(f"  {'Raw epoch (2 x 1280 x float64)':32s} {N_SAMPLES*2*8 / 1024:7.2f} KB")

payload = {
    "timestamp": datetime.now().isoformat(),
    "config": {
        "fs_hz": FS, "epoch_sec": EPOCH_SEC, "n_samples_per_epoch": N_SAMPLES,
        "n_features": N_FEATS_V9, "warmup_trials": WARMUP_N, "trials": TRIALS_N,
    },
    "per_stage_ms": timings,
    "full_pipeline_ms_per_epoch": round(float(full_ms), 3),
    "real_time_factor": round(float(full_ms / (EPOCH_SEC * 1000)), 6),
    "lda_fit_seconds_on_14498x50": round(float(train_s), 3),
    "lda_predict_proba_single_us": round(float(predict_ms * 1000), 3),
    "end_to_end_ms_per_epoch": round(float(e2e_ms), 3),
    "memory_bytes": {
        "serialized_lda_model": int(model_bytes),
        "feature_vector_per_epoch": feat_vec_bytes,
        "raw_epoch_per_channel_pair": int(N_SAMPLES * 2 * 8),
    },
    "interpretation": (
        f"With a 10-s epoch, the pipeline processes one epoch in {full_ms:.1f} ms. "
        f"That is ~{int(EPOCH_SEC*1000/full_ms)}x faster than real-time on a laptop CPU, "
        "so a single core can easily handle continuous streaming with headroom for BLE I/O."
    ),
}

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime_benchmark.json")
with open(out_path, "w") as f:
    json.dump(payload, f, indent=2)
print(f"\nWrote {out_path}")
