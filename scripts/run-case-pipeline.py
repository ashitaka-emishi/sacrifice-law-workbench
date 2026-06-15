#!/usr/bin/env python3
"""Run the case-local pipeline for one case or all cases."""
from __future__ import annotations

import argparse
import subprocess
import sys

from pipeline_common import ROOT, case_ids

STEPS = [
    "normalize-texts.py",
    "segment-texts.py",
    "generate-mipvu-worklist.py",
    "build-concordance.py",
    "run-case-analysis.py",
]


def run_step(script_name: str, case_id: str, strict: bool) -> int:
    command = [sys.executable, str(ROOT / "scripts" / script_name), "--case", case_id]
    if strict:
        command.append("--strict")
    result = subprocess.run(command, cwd=ROOT)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", default=None, help="Optional case id")
    parser.add_argument("--strict", action="store_true", help="Fail on missing expected inputs")
    args = parser.parse_args()

    exit_code = 0
    for case_id in case_ids(args.case_id):
        print(f"\n=== {case_id} ===", flush=True)
        for step in STEPS:
            code = run_step(step, case_id, strict=args.strict)
            if code != 0:
                exit_code = code
                if args.strict:
                    return exit_code
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
