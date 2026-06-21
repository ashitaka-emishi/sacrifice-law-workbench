"""Public-safe reference indexes for gitignored local corpus artifacts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


INDEX_VERSION = "1.0"
PROHIBITED_PUBLIC_FIELDS = {
    "text",
    "sentence_text",
    "span_text",
    "lexical_unit",
    "lemma",
    "gloss_en",
    "evidence_span",
}
VOLATILE_ARTIFACT_FIELDS = {"generated_at", "pipeline_log", "raw_path"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_artifact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: stable_artifact_value(child)
            for key, child in value.items()
            if key not in VOLATILE_ARTIFACT_FIELDS
        }
    if isinstance(value, list):
        return [stable_artifact_value(child) for child in value]
    return value


def sha256_json_artifact(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    payload = json.dumps(
        stable_artifact_value(data),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(payload)


def sha256_record(record: dict[str, Any]) -> str:
    payload = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(payload)


def index_path(root: Path, case_id: str) -> Path:
    return root / "cases" / case_id / "metadata" / "local-corpus-reference-index.json"


def iter_prohibited_fields(value: Any, prefix: str = "") -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in PROHIBITED_PUBLIC_FIELDS:
                yield path
            yield from iter_prohibited_fields(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_prohibited_fields(child, f"{prefix}[{index}]")


def read_index(root: Path, case_id: str) -> dict[str, Any] | None:
    path = index_path(root, case_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None
