"""Writable-boundary helpers for human reliability artifacts."""
from __future__ import annotations

from pathlib import Path


WRITABLE_SUBTREE = Path("quality/human-reliability")


class ProtectedPathError(ValueError):
    """Raised when a human-reliability tool targets a protected path."""


def safe_output_path(case_root: Path, relative: str | Path) -> Path:
    case_root = case_root.resolve()
    target = (case_root / relative).resolve()
    allowed = (case_root / WRITABLE_SUBTREE).resolve()
    if target != allowed and allowed not in target.parents:
        raise ProtectedPathError(
            f"refusing output outside human-reliability subtree: {target}"
        )
    return target
