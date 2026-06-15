#!/usr/bin/env python3
"""Shared helpers for the case-local research pipeline."""
from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path
from typing import Any, Iterable, Union

import yaml

ROOT = Path(__file__).resolve().parents[1]
CASES_ROOT = ROOT / "cases"


def now_iso() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def case_ids(selected: str | None = None) -> list[str]:
    if selected:
        return [selected]
    if not CASES_ROOT.exists():
        return []
    return [
        path.name
        for path in sorted(CASES_ROOT.iterdir())
        if path.is_dir() and (path / "metadata" / "document-manifest.json").exists()
    ]


def case_dir(case_id: str) -> Path:
    return CASES_ROOT / case_id


def document_manifest(case_id: str) -> dict[str, Any]:
    return read_json(case_dir(case_id) / "metadata" / "document-manifest.json", {}) or {}


def documents(case_id: str) -> list[dict[str, Any]]:
    manifest = document_manifest(case_id)
    docs = manifest.get("documents", [])
    return [doc for doc in docs if isinstance(doc, dict)]


def document_id(doc: dict[str, Any]) -> str:
    value = doc.get("document_id", doc.get("id"))
    return "" if value is None else str(value)


def cluster_config(case_id: str) -> list[dict[str, Any]]:
    data = read_json(case_dir(case_id) / "config" / "case-clusters.json", []) or []
    return [item for item in data if isinstance(item, dict)]


def valid_cluster_ids(case_id: str) -> set[str]:
    return {str(item.get("id")) for item in cluster_config(case_id) if item.get("id")}


def raw_path_for(case_id: str, doc: dict[str, Any]) -> Path:
    base = case_dir(case_id)
    raw = doc.get("expected_raw_path") or doc.get("raw_path")
    if raw:
        path = Path(str(raw))
        return path if path.is_absolute() else base / path
    return base / "corpus" / "raw" / f"{document_id(doc)}.txt"


def text_path_for(case_id: str, doc: dict[str, Any]) -> Path:
    return case_dir(case_id) / "corpus" / "text" / f"{document_id(doc)}.md"


def segmented_path_for(case_id: str, doc: dict[str, Any]) -> Path:
    return case_dir(case_id) / "corpus" / "segmented" / f"{document_id(doc)}.json"


def annotated_path_for(case_id: str, doc: dict[str, Any]) -> Path:
    return case_dir(case_id) / "corpus" / "annotated" / f"{document_id(doc)}_annotated.json"


def mipvu_path_for(case_id: str, doc_or_id: Union[dict[str, Any], str]) -> Path:
    doc_id = document_id(doc_or_id) if isinstance(doc_or_id, dict) else str(doc_or_id)
    return case_dir(case_id) / "corpus" / "mipvu" / f"{doc_id}_mipvu.json"


def cmt_mappings_path_for(case_id: str) -> Path:
    return case_dir(case_id) / "corpus" / "cmt" / "cmt-mappings.json"


def iter_cmt_mappings(data: Any) -> Iterable[dict[str, Any]]:
    if isinstance(data, dict):
        items = data.get("mappings", [])
    elif isinstance(data, list):
        items = data
    else:
        return
    for item in items or []:
        if isinstance(item, dict):
            yield item


def parse_markdown_with_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}
    return meta if isinstance(meta, dict) else {}, parts[2].strip()


def frontmatter_for(case_id: str, doc: dict[str, Any], raw_path: Path) -> str:
    meta = dict(doc)
    doc_id = document_id(doc)
    meta["document_id"] = doc_id
    meta.setdefault("case_id", case_id)
    meta["raw_path"] = str(raw_path.relative_to(case_dir(case_id)) if raw_path.is_relative_to(case_dir(case_id)) else raw_path)
    meta["pipeline_log"] = [
        {
            "stage": "normalize-texts",
            "script": "scripts/normalize-texts.py",
            "generated_at": now_iso(),
        }
    ]
    return "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip() + "\n---\n\n"


_ABBREV_RE = re.compile(
    r"\b(?:Mr|Mrs|Ms|Dr|Gov|Hon|Gen|Col|Maj|Capt|Sen|Rep|Lt|Sgt|Pvt|St|No|Vs|Vol|Pp|Sec|Dept|etc|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec|U\.S|U)\.",
    re.IGNORECASE,
)
_INITIAL_RE = re.compile(r"\b[A-Z]\.")
_PH = "\x00"


def split_sentences(text: str) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    protected = _ABBREV_RE.sub(lambda match: match.group().replace(".", _PH), text)
    protected = _INITIAL_RE.sub(lambda match: match.group().replace(".", _PH), protected)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'`\[])", protected)
    return [part.replace(_PH, ".").strip() for part in parts if part.strip()]


def iter_sentence_nodes(doc: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for section in doc.get("sections", []) or []:
        for para in section.get("paragraphs", []) or []:
            for sent in para.get("sentences", []) or []:
                if isinstance(sent, dict):
                    yield sent


def iter_instances_from_annotated(data: Any) -> Iterable[tuple[dict[str, Any], str | None]]:
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield item, item.get("sentence_id")
        return
    if not isinstance(data, dict):
        return
    if isinstance(data.get("instances"), list):
        for item in data["instances"]:
            if isinstance(item, dict):
                yield item, item.get("sentence_id")
    for sent in iter_sentence_nodes(data):
        sentence_id = sent.get("sentence_id")
        for inst in sent.get("metaphor_instances", []) or []:
            if isinstance(inst, dict):
                yield inst, sentence_id


def iter_mipvu_records(data: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(data, dict):
        return
    for item in data.get("lexical_units", []) or []:
        if isinstance(item, dict):
            yield item


def count_by(items: Iterable[dict[str, Any]], getter) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = getter(item)
        values = value if isinstance(value, list) else [value]
        for entry in values:
            if entry in (None, ""):
                continue
            key = str(entry)
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])))


def get_nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
