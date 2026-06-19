#!/usr/bin/env python3
"""Rebuild all case-local pipeline outputs and project status."""
from __future__ import annotations

import subprocess
import sys

from pipeline_common import ROOT


def reliability_cases() -> list[str]:
    return [
        path.parents[3].name
        for path in sorted(
            (ROOT / "cases").glob(
                "*/quality/model-reliability/sample/sample-manifest.json"
            )
        )
        if path.is_file()
    ]


def main() -> int:
    steps = [
        [sys.executable, str(ROOT / "scripts" / "run-case-pipeline.py")],
    ]
    steps.extend(
        [
            sys.executable,
            str(ROOT / "scripts" / "model_reliability" / "pipeline.py"),
            "run",
            "--case",
            case_id,
        ]
        for case_id in reliability_cases()
    )
    steps.append(
        [sys.executable, str(ROOT / "scripts" / "generate-project-status.py")]
    )
    for command in steps:
        result = subprocess.run(command, cwd=ROOT)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
