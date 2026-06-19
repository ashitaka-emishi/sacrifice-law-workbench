#!/usr/bin/env python3
"""Enforce immutable reference boundaries for model-reliability tools."""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import shutil
from typing import Iterator, Union


WRITABLE_SUBTREE = Path("quality/model-reliability")
REVIEW_CANDIDATE_SUBTREE = WRITABLE_SUBTREE / "review-queue"


class ProtectedPathError(ValueError):
    """Raised when a model-reliability tool attempts a protected write."""


def safe_output_path(case_root: Path, relative: str | Path) -> Path:
    case_root = case_root.resolve()
    target = (case_root / relative).resolve()
    allowed = (case_root / WRITABLE_SUBTREE).resolve()
    if target != allowed and allowed not in target.parents:
        raise ProtectedPathError(
            f"refusing output outside model-reliability subtree: {target}"
        )
    return target


def review_candidate_path(case_root: Path, filename: str) -> Path:
    target = safe_output_path(case_root, REVIEW_CANDIDATE_SUBTREE / filename)
    expected_parent = (case_root.resolve() / REVIEW_CANDIDATE_SUBTREE).resolve()
    if target.parent != expected_parent:
        raise ProtectedPathError(
            f"review candidates must write directly beneath {expected_parent}"
        )
    return target


def _protected_roots(root: Path, case_root: Path) -> tuple[Path, ...]:
    quality_root = case_root / "quality"
    roots = [
        case_root / "metadata",
        case_root / "corpus",
        case_root / "analysis",
        root / "publication",
    ]
    if quality_root.is_dir():
        roots.extend(
            path
            for path in quality_root.iterdir()
            if path.name != "model-reliability"
        )
    return tuple(path.resolve() for path in roots)


SnapshotEntry = tuple[str, Union[bytes, str, None]]


def _entry(path: Path) -> SnapshotEntry:
    if path.is_symlink():
        return ("symlink", os.readlink(path))
    if path.is_file():
        return ("file", path.read_bytes())
    if path.is_dir():
        return ("directory", None)
    return ("other", None)


def _snapshot(roots: tuple[Path, ...]) -> dict[Path, SnapshotEntry]:
    return {
        path.absolute(): _entry(path)
        for protected_root in roots
        if protected_root.exists() or protected_root.is_symlink()
        for path in (protected_root, *protected_root.rglob("*"))
    }


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def _restore_entry(path: Path, entry: SnapshotEntry) -> None:
    kind, data = entry
    if path.exists() or path.is_symlink():
        _remove(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if kind == "directory":
        path.mkdir(exist_ok=True)
    elif kind == "file":
        assert isinstance(data, bytes)
        path.write_bytes(data)
    elif kind == "symlink":
        assert isinstance(data, str)
        path.symlink_to(data)


def _restore(
    protected_roots: tuple[Path, ...],
    before: dict[Path, SnapshotEntry],
) -> list[Path]:
    current = _snapshot(protected_roots)
    changed = sorted(
        path for path, entry in before.items() if current.get(path) != entry
    )
    created = sorted(
        set(current) - set(before),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for path in created:
        _remove(path)
    for path in sorted(changed, key=lambda item: len(item.parts)):
        _restore_entry(path, before[path])
    return changed + created


@contextmanager
def immutable_reference_guard(root: Path, case_id: str) -> Iterator[None]:
    root = root.resolve()
    case_root = root / "cases" / case_id
    if not case_root.is_dir():
        raise ProtectedPathError(f"unknown case `{case_id}`")
    protected_roots = _protected_roots(root, case_root)
    before = _snapshot(protected_roots)
    try:
        yield
    finally:
        mutations = _restore(protected_roots, before)
        if mutations:
            relative = [
                path.relative_to(root).as_posix()
                if path.is_relative_to(root)
                else str(path)
                for path in mutations
            ]
            raise ProtectedPathError(
                "model-reliability command attempted protected write(s): "
                + ", ".join(relative)
            )
