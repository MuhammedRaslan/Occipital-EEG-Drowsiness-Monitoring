"""Raw-signal baselines on the DD-Database (self-report labels).

SEED-VIG raw recordings are not available on this machine, so these baselines
run on the DD-Database only (decision Q3, 24 Oct 2026).

  * EEGNet-8,2 with the published settings for cross-subject training
    (Lawhern et al. 2018): temporal kernel of half the sampling rate, dropout
    0.25, max-norm constraints, class weights, and up to 500 epochs keeping
    the weights with the lowest validation loss. Two adaptations: the
    validation set is 2 of the 9 training drivers, and training stops after
    50 epochs without improvement (Supplementary Section S7).
  * Riemannian: OAS covariance, tangent space at the training-set mean,
    shrinkage LDA (Ledoit-Wolf), and a logistic-regression variant.

Both use the same label-free calibration as the main pipeline: each channel
of each trial is scaled by its statistics over the trial's first 300 s.

Output: results/baselines_dd.json, caches/scores_baselines_dd.npz
"""
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

EEGNET = {"F1": 8, "D": 2, "F2": 16, "kern1": 64, "kern2": 16, "drop": 0.25, "maxnorm_spatial": 1.0,
          "maxnorm_dense": 0.25, "class_weight": "inverse class proportion, majority class 1", "lr": 1e-3,
          "batch": 64, "max_epochs": 500, "patience": 50, "val_drivers": 2, "seed": 42}


def calibrate_epochs(E, recording, t, cal_sec):
    En = np.empty_like(E, dtype=np.float32)
    for r in np.unique(recording):
        m = recording == r
        fit = m & (t < t[m].min() + cal_sec)
        mu = E[fit].mean(axis=(0, 2), keepdims=True)
        sd = E[fit].std(axis=(0, 2), keepdims=True)
        sd[sd == 0] = 1.0
        En[m] = (E[m] - mu) / sd
    return En


def riemann_scores(En, y, subject, test_subjects, clf_name):
    from pyriemann.estimation import Covariances
    from pyriemann.tangentspace import TangentSpace
    from sklearn.linear_model import LogisticRegression
    covs = Covariances(estimator="oas").transform(En.astype(np.float64))
    p = np.full(len(y), np.nan)
    for s in test_subjects:
        tr = (y >= 0) & (subject != s)
        te = subject == s
        ts = TangentSpace(metric="riemann").fit(covs[tr])
        Ftr, Fte = ts.transform(covs[tr]), ts.transform(covs[te])
        clf = C.lda() if clf_name == "LDA" else LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
        p[te] = clf.fit(Ftr, y[tr]).predict_proba(Fte)[:, 1]
    return p


def eegnet_scores(En, y, subject, test_subjects):
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, TensorDataset

    class EEGNet(nn.Module):
        def __init__(self, channels=2, samples=C.EPOCH):
            super().__init__()
            F1, D, F2 = EEGNET["F1"], EEGNET["D"], EEGNET["F2"]
            kern1, kern2, drop = EEGNET["kern1"], EEGNET["kern2"], EEGNET["drop"]
            self.conv1 = nn.Conv2d(1, F1, (1, kern1), padding="same", bias=False)
            self.bn1 = nn.BatchNorm2d(F1)
            self.dwconv = nn.Conv2d(F1, F1 * D, (channels, 1), groups=F1, bias=False)
            self.bn2 = nn.BatchNorm2d(F1 * D)
            self.pool1, self.drop1 = nn.AvgPool2d((1, 4)), nn.Dropout(drop)
            self.sep_dw = nn.Conv2d(F1 * D, F1 * D, (1, kern2), padding="same", groups=F1 * D, bias=False)
            self.sep_pw = nn.Conv2d(F1 * D, F2, (1, 1), bias=False)
            self.bn3 = nn.BatchNorm2d(F2)
            self.pool2, self.drop2 = nn.AvgPool2d((1, 8)), nn.Dropout(drop)
            with torch.no_grad():
                n_flat = self._features(torch.zeros(1, 1, channels, samples)).shape[1]
            self.fc = nn.Linear(n_flat, 2)

        def _features(self, x):
            x = F.elu(self.bn2(self.dwconv(self.bn1(self.conv1(x)))))
            x = self.drop1(self.pool1(x))
            x = F.elu(self.bn3(self.sep_pw(self.sep_dw(x))))
            return torch.flatten(self.drop2(self.pool2(x)), 1)

        def forward(self, x):
            return self.fc(self._features(x))

        def max_norm(self):
            """The published constraints: each spatial filter, and each output unit of the classifier."""
            with torch.no_grad():
                self.dwconv.weight.copy_(torch.renorm(self.dwconv.weight, 2, 0, EEGNET["maxnorm_spatial"]))
                self.fc.weight.copy_(torch.renorm(self.fc.weight, 2, 0, EEGNET["maxnorm_dense"]))

    torch.set_num_threads(max(1, (os.cpu_count() or 2) - 1))
    p = np.full(len(y), np.nan)
    log = []
    for k, s in enumerate(test_subjects):
        t0 = time.time()
        drivers = sorted(set(subject[(y >= 0) & (subject != s)]))
        rng = np.random.default_rng(EEGNET["seed"] + k)
        val_drivers = sorted(str(v) for v in rng.choice(drivers, EEGNET["val_drivers"], replace=False))
        va = (y >= 0) & np.isin(subject, val_drivers)
        tr = (y >= 0) & (subject != s) & ~va
        te = subject == s
        counts = np.bincount(y[tr], minlength=2)
        crit = nn.CrossEntropyLoss(weight=torch.tensor(counts.max() / counts, dtype=torch.float32))
        torch.manual_seed(EEGNET["seed"] + k)
        model = EEGNet()
        opt = torch.optim.Adam(model.parameters(), lr=EEGNET["lr"])
        loader = DataLoader(TensorDataset(torch.from_numpy(En[tr][:, None]), torch.from_numpy(y[tr].astype(np.int64))),
                            batch_size=EEGNET["batch"], shuffle=True)
        Xva, yva = torch.from_numpy(En[va][:, None]), torch.from_numpy(y[va].astype(np.int64))
        best, best_epoch, best_state = np.inf, -1, None
        for epoch in range(EEGNET["max_epochs"]):
            model.train()
            for xb, yb in loader:
                opt.zero_grad()
                crit(model(xb), yb).backward()
                opt.step()
                model.max_norm()
            model.eval()
            with torch.no_grad():
                loss = float(crit(model(Xva), yva))
            if loss < best:
                best, best_epoch = loss, epoch
                best_state = {n: v.clone() for n, v in model.state_dict().items()}
            elif epoch - best_epoch >= EEGNET["patience"]:
                break
        model.load_state_dict(best_state)
        model.eval()
        with torch.no_grad():
            p[te] = torch.softmax(model(torch.from_numpy(En[te][:, None])), 1)[:, 1].numpy()
        log.append({"test_driver": str(s), "validation_drivers": val_drivers, "epochs_run": epoch + 1,
                    "best_epoch": best_epoch + 1, "best_validation_loss": best, "seconds": time.time() - t0})
        print(f"  EEGNet fold {s}: best epoch {best_epoch + 1} of {epoch + 1}, {time.time()-t0:.0f}s", flush=True)
    return p, log


def main():
    ds = C.load_dd()
    z = np.load(os.path.join(C.CACHES, "dd_epochs_v2.npz"), allow_pickle=True)
    assert (z["subject"] == ds.subject).all() and (z["t"] == ds.t).all()
    En = calibrate_epochs(z["E"], ds.recording, ds.t, ds.cal_sec)
    res, cache = {}, {}
    for name, fn in (("Riemannian TS + LDA", lambda: (riemann_scores(En, ds.y, ds.subject, ds.test_subjects, "LDA"), None)),
                     ("Riemannian TS + LogReg", lambda: (riemann_scores(En, ds.y, ds.subject, ds.test_subjects, "LogReg"), None)),
                     ("EEGNet", lambda: eegnet_scores(En, ds.y, ds.subject, ds.test_subjects))):
        t0 = time.time()
        p, log = fn()
        res[name] = C.evaluate(ds, p)
        res[name]["elapsed_s"] = time.time() - t0
        if log:
            res[name]["training"] = log
        cache[name.replace(" ", "_").replace("+", "")] = p
        print(f"{name}: AUC {res[name]['pooled']['AUC']:.2f}  median subject AUC {res[name]['subject_AUC_median']:.1f}", flush=True)
    np.savez_compressed(os.path.join(C.CACHES, "scores_baselines_dd.npz"), **cache)
    C.write_result("baselines_dd", {"calibration": "per-trial channel scaling over the first 300 s (label-free)",
                                    "eegnet_settings": EEGNET, "results": res}, __file__)


if __name__ == "__main__":
    main()
