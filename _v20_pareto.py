import json, sys, io
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
with open("publication_results_v20.json") as f:
    d = json.load(f)
flat = []
for mode, m1 in d["sweep"].items():
    for thr, m2 in m1.items():
        for dwl, m3 in m2.items():
            for tau, cell in m3.items():
                # Drop operating points with no both-onset cases (med_lead meaningless)
                if cell["median_lead_min_both"] is None or cell["n_both"] < 5:
                    continue
                flat.append({
                    "mode": mode, "thr": thr, "dwl": dwl, "tau": tau,
                    "proactive": cell["proactive_rate"] or 0,
                    "med_lead":  cell["median_lead_min_both"],
                    "fpr":       cell["fpr_awake_mean"] or 1.0,
                    "sens":      cell["sens_drowsy_mean"] or 0,
                    "n_both":    cell["n_both"],
                })

# Pareto front: maximise proactive AND med_lead, minimise fpr.
def dominates(a, b):
    return ((a["proactive"] >= b["proactive"]) and
            (a["med_lead"]  >= b["med_lead"])  and
            (a["fpr"]       <= b["fpr"])       and
            ((a["proactive"] > b["proactive"]) or
             (a["med_lead"]  > b["med_lead"])  or
             (a["fpr"]       < b["fpr"])))
pareto = [a for a in flat if not any(dominates(b, a) for b in flat if b is not a)]

# Filter: FPR budget 5 %, 10 %, 15 %, 20 %, 30 %
print("Pareto front filtered by FPR_awake budget:")
for fpr_budget in (0.05, 0.10, 0.15, 0.20, 0.30):
    cand = [c for c in flat if c["fpr"] <= fpr_budget]
    if not cand:
        print(f"  FPR<={fpr_budget:.2f}: no operating point found")
        continue
    # Pick the best proactive rate, tiebreak by lead
    best = max(cand, key=lambda c: (c["proactive"], c["med_lead"], -c["fpr"]))
    print(f"  FPR<={fpr_budget:.2f} => {best['mode']:14} thr={best['thr']:<5} "
          f"dwl={best['dwl']:>3}s tau={best['tau']:>4}s  "
          f"proactive={best['proactive']:.3f}  med_lead={best['med_lead']:5.2f}m  "
          f"FPR={best['fpr']:.3f}  sens={best['sens']:.3f}")

print()
print("All Pareto-optimal operating points (proactive up, lead up, FPR down):")
pareto.sort(key=lambda c: (-c["proactive"], -c["med_lead"], c["fpr"]))
for c in pareto[:25]:
    print(f"  {c['mode']:14} thr={c['thr']:<5} dwl={c['dwl']:>3}s tau={c['tau']:>4}s  "
          f"proactive={c['proactive']:.3f}  med_lead={c['med_lead']:5.2f}m  "
          f"FPR={c['fpr']:.3f}  sens={c['sens']:.3f}")
print(f"  ... ({len(pareto)} Pareto points total)")
