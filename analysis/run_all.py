"""Run every analysis step in dependency order.

    python analysis/run_all.py            # everything
    python analysis/run_all.py --from 10  # resume at a step

Each step is a separate process; a failing step stops the run. The built-in
reproduction checks (published SEED-VIG internal LOSO; spot values from the
original DD-Database recordings; probe label counts) run inside the steps.
The runtime benchmark runs after every analysis and alone, because timings
taken while other work is running are not representative; only the generators
that read its result follow it (numbers.tex, the supplementary tables and the
graphical abstract).
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = ["00_seed_extract", "01_dd_extract", "02_dd_labels", "03_seed_prepare", "10_monitoring",
         "12_baselines_dd", "13_per_subject", "14_tau_sweep", "15_coherence_stats", "16_reference",
         "17_calibration", "18_cross_dataset", "19_ensemble", "21_sensitivity", "22_label_runs", "23_alarms", "24_offsets",
         "30_figures",
         "20_runtime",
         "40_numbers", "41_supp_tables", "make_ga"]
# Steps that live outside analysis/.
SCRIPT = {"make_ga": os.path.join(os.path.dirname(HERE), "manuscript", "make_ga.py")}


def main():
    start = sys.argv[sys.argv.index("--from") + 1] if "--from" in sys.argv else None
    steps = STEPS[STEPS.index(next(s for s in STEPS if s.startswith(start))):] if start else STEPS
    report = []
    for s in steps:
        t0 = time.time()
        p = subprocess.run([sys.executable, SCRIPT.get(s, os.path.join(HERE, f"{s}.py"))],
                           cwd=os.path.dirname(os.path.dirname(HERE)))
        report.append({"step": s, "exit": p.returncode, "seconds": round(time.time() - t0, 1)})
        print(f"== {s}: exit {p.returncode} in {time.time() - t0:.0f}s", flush=True)
        if p.returncode != 0:
            break
    with open(os.path.join(os.path.dirname(HERE), "results", "run_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    sys.exit(0 if all(r["exit"] == 0 for r in report) else 1)


if __name__ == "__main__":
    main()
