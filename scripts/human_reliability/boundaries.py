"""Writable-boundary helpers for human reliability artifacts."""
from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
import os
from pathlib import Path
import shutil
from typing import Any, Callable, Iterator, TypeVar, Union, cast


WRITABLE_SUBTREE = Path("quality/human-reliability")
_CASE_PROTECTED_IGNORE_ROOTS = (WRITABLE_SUBTREE,)


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


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _is_ignored(path: Path, ignored_roots: tuple[Path, ...]) -> bool:
    return any(path == root or _is_relative_to(path, root) for root in ignored_roots)


SnapshotEntry = tuple[str, Union[bytes, str, None]]


def _entry(path: Path) -> SnapshotEntry:
    if path.is_symlink():
        return ("symlink", os.readlink(path))
    if path.is_file():
        return ("file", path.read_bytes())
    if path.is_dir():
        return ("directory", None)
    return ("other", None)


def _iter_snapshot_paths(
    protected_roots: tuple[Path, ...],
    ignored_roots: tuple[Path, ...],
) -> Iterator[Path]:
    for protected_root in protected_roots:
        if not protected_root.exists() and not protected_root.is_symlink():
            continue
        protected_root = protected_root.absolute()
        if _is_ignored(protected_root.resolve(), ignored_roots):
            continue
        yield protected_root
        if protected_root.is_dir() and not protected_root.is_symlink():
            for path in protected_root.rglob("*"):
                if not _is_ignored(path.resolve(), ignored_roots):
                    yield path.absolute()


def _snapshot(
    protected_roots: tuple[Path, ...],
    ignored_roots: tuple[Path, ...],
) -> dict[Path, SnapshotEntry]:
    return {
        path.absolute(): _entry(path)
        for path in _iter_snapshot_paths(protected_roots, ignored_roots)
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


def _prune_empty_dirs(path: Path, stop: Path) -> None:
    while path != stop and _is_relative_to(path, stop):
        try:
            path.rmdir()
        except OSError:
            return
        path = path.parent


def _restore(
    protected_roots: tuple[Path, ...],
    ignored_roots: tuple[Path, ...],
) -> tuple[
    Callable[[dict[Path, SnapshotEntry]], list[Path]],
    dict[Path, SnapshotEntry],
]:
    before = _snapshot(protected_roots, ignored_roots)

    def restore_from_snapshot(snapshot: dict[Path, SnapshotEntry]) -> list[Path]:
        current = _snapshot(protected_roots, ignored_roots)
        changed = sorted(
            path for path, entry in snapshot.items() if current.get(path) != entry
        )
        created = sorted(
            set(current) - set(snapshot),
            key=lambda path: len(path.parts),
            reverse=True,
        )
        for path in created:
            _remove(path)
            for root in protected_roots:
                if _is_relative_to(path, root):
                    _prune_empty_dirs(path.parent, root)
                    break
        for path in sorted(changed, key=lambda item: len(item.parts)):
            _restore_entry(path, snapshot[path])
        return changed + created

    return restore_from_snapshot, before


def _protected_roots(case_root: Path) -> tuple[Path, ...]:
    """Return case paths that human-reliability tools must not mutate."""

    writable = (case_root / WRITABLE_SUBTREE).resolve()
    roots: list[Path] = []
    for child in case_root.iterdir():
        if child.resolve() == writable:
            continue
        roots.append(child.absolute())
    return tuple(roots)


@contextmanager
def immutable_accepted_artifact_guard(root: Path, case_id: str) -> Iterator[None]:
    """Restore and reject writes outside the human-reliability work layer."""

    root = root.resolve()
    case_root = root / "cases" / case_id
    if not case_root.is_dir():
        raise ProtectedPathError(f"unknown case `{case_id}`")
    ignored_roots = tuple(
        (case_root / path).resolve() for path in _CASE_PROTECTED_IGNORE_ROOTS
    )
    restore_from_snapshot, before = _restore(
        _protected_roots(case_root), ignored_roots
    )
    try:
        yield
    finally:
        mutations = restore_from_snapshot(before)
        if mutations:
            relative = [
                path.relative_to(root).as_posix()
                if _is_relative_to(path, root)
                else str(path)
                for path in mutations
            ]
            raise ProtectedPathError(
                "human-reliability command attempted protected write(s): "
                + ", ".join(relative)
            )


F = TypeVar("F", bound=Callable[..., Any])


def protect_accepted_artifacts(func: F) -> F:
    """Guard a case-scoped human-reliability function.

    The wrapped callable must accept ``root`` and ``case_id`` as its first two
    positional arguments.
    """

    @wraps(func)
    def wrapper(root: Path, case_id: str, *args: Any, **kwargs: Any) -> Any:
        with immutable_accepted_artifact_guard(root, case_id):
            return func(root, case_id, *args, **kwargs)

    return cast(F, wrapper)
