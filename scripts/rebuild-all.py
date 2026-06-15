#!/usr/bin/env python3
"""Rebuild all case-local pipeline outputs and project status."""
from __future__ import annotations

import subprocess
import sys

from pipeline_common import ROOT


def main() -> int:
    steps = [
        [sys.executable, str(ROOT / "scripts" / "run-case-pipeline.py")],
        [sys.executable, str(ROOT / "scripts" / "generate-project-status.py")],
    ]
    for command in steps:
        result = subprocess.run(command, cwd=ROOT)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
