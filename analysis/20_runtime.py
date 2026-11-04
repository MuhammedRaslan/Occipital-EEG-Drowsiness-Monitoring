"""Measured runtime and model footprint.

Times, on this machine, per 10-s epoch: the lean-10 feature extraction, the
extended 50-feature extraction, an LDA posterior and an EMA update. Reports
the stored size of the trained model and of the per-driver calibration state.

Output: results/runtime.json
"""
import os
import pickle
import platform
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

N = 500


def lean10(o1, o2):
    import antropy as ant
    return [ant.sample_entropy(o1, order=2), ant.sample_entropy(o2, order=2),
            ant.perm_entropy(o1, order=3, normalize=True), ant.perm_entropy(o2, order=3, normalize=True),
            C.aperiodic_slope(o1, C.FS), C.aperiodic_slope(o2, C.FS),
            abs(C.peak_alpha_freq(o1, C.FS) - C.peak_alpha_freq(o2, C.FS)),
            C.band_coherence(o1, o2, C.FS, C.BANDS["theta"]), C.band_coherence(o1, o2, C.FS, C.BANDS["alpha"]),
            C.band_coherence(o1, o2, C.FS, C.BANDS["beta"])]


def timeit(fn, args_list):
    for a in args_list[:10]:
        fn(*a)
    ts = []
    for a in args_list:
        t0 = time.perf_counter()
        fn(*a)
        ts.append((time.perf_counter() - t0) * 1000)
    return {"median_ms": float(np.median(ts)), "p95_ms": float(np.percentile(ts, 95))}


def main():
    E = np.load(os.path.join(C.CACHES, "dd_epochs_v2.npz"))["E"]
    rng = np.random.default_rng(0)
    idx = rng.choice(len(E), N, replace=False)
    args = [(E[i, 0].astype(float), E[i, 1].astype(float)) for i in idx]
    t_lean = timeit(lean10, args)
    t_50 = timeit(lambda a, b: C.feats_epoch_50(a, b), args[:100])

    ds = C.load_dd()
    Xn = ds.calibrated(C.LEAN10)
    m = ds.y >= 0
    clf = C.lda().fit(Xn[m], ds.y[m])
    x1 = Xn[:1]
    t_pred = timeit(lambda: clf.predict_proba(x1), [()] * 2000)
    state = {"p": 0.5}

    def ema_step():
        state["p"] = 0.016 * 0.7 + 0.984 * state["p"]
    t_ema = timeit(ema_step, [()] * 2000)

    coef_bytes = (clf.coef_.size + clf.intercept_.size) * 4
    calib_bytes = 2 * len(C.LEAN10) * 4
    C.write_result("runtime", {
        "machine": {"processor": platform.processor(), "platform": platform.platform(), "python": platform.python_version()},
        "per_epoch": {"lean10_feature_extraction": t_lean, "ext50_feature_extraction": t_50,
                      "lda_posterior": t_pred, "ema_update": t_ema},
        "model_size": {"lda_weights_and_bias_float32_bytes": coef_bytes,
                       "per_driver_calibration_mean_sd_float32_bytes": calib_bytes,
                       "sklearn_pickle_bytes": len(pickle.dumps(clf))},
        "real_time_factor_lean10": t_lean["median_ms"] / (C.EPOCH_SEC * 1000)}, __file__)
    print(f"lean-10 extraction {t_lean['median_ms']:.1f} ms/epoch; 50-feature {t_50['median_ms']:.1f} ms; "
          f"LDA {t_pred['median_ms']*1000:.0f} us; model {coef_bytes} B + calibration {calib_bytes} B")


if __name__ == "__main__":
    main()
