"""
run_all.py — Azure Demand Forecasting Pipeline Runner
Executes all 4 milestones in sequence with timing and status reporting.
Usage:  python run_all.py
"""

import subprocess
import sys
import time
import os

MILESTONES = [
    ("Milestone 1", "Data Preparation",          "milestone_1_data_prep.py"),
    ("Milestone 2", "Feature Engineering",        "milestone_2_feature_engineering.py"),
    ("Milestone 3", "Model Development",          "milestone_3_model_development.py"),
    ("Milestone 4", "Forecast Integration",       "milestone_4_integration.py"),
]

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def banner():
    print(f"\n{BOLD}{CYAN}{'='*60}")
    print("  Azure Demand Forecasting & Capacity Optimization")
    print(f"  Pipeline Runner — {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}{RESET}\n")

def run_milestone(label: str, description: str, script: str) -> bool:
    print(f"{BOLD}{YELLOW}▶  {label}: {description}{RESET}")
    print(f"   Running {script} ...")
    start = time.time()

    result = subprocess.run(
        [sys.executable, "-u", script],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )

    elapsed = time.time() - start

    if result.returncode == 0:
        print(f"{GREEN}   ✔  Completed in {elapsed:.1f}s{RESET}")
        # Print last 3 lines of output for quick context
        lines = [l for l in result.stdout.splitlines() if l.strip()]
        for line in lines[-3:]:
            print(f"      {line}")
    else:
        print(f"{RED}   ✘  FAILED after {elapsed:.1f}s{RESET}")
        print(f"{RED}{'─'*56}")
        print(result.stderr or result.stdout)
        print(f"{'─'*56}{RESET}")
    print()
    return result.returncode == 0


def main():
    banner()
    total_start = time.time()
    results = []

    for label, desc, script in MILESTONES:
        if not os.path.exists(script):
            print(f"{RED}   ✘  {script} not found — skipping.{RESET}\n")
            results.append((label, False))
            continue
        ok = run_milestone(label, desc, script)
        results.append((label, ok))
        if not ok:
            print(f"{RED}Pipeline stopped: {label} failed.{RESET}")
            break

    total = time.time() - total_start
    print(f"{BOLD}{CYAN}{'='*60}")
    print(f"  Pipeline Summary  ({total:.1f}s total)")
    print(f"{'='*60}{RESET}")
    for label, ok in results:
        status = f"{GREEN}✔  PASS{RESET}" if ok else f"{RED}✘  FAIL{RESET}"
        print(f"  {label:<14} {status}")
    print()

    all_ok = all(ok for _, ok in results)
    if all_ok and len(results) == len(MILESTONES):
        print(f"{GREEN}{BOLD}  All milestones passed! Dashboard: open dashboard.html{RESET}\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
