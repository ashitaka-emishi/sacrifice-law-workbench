#!/usr/bin/env python3
"""Validate model-reliability submissions against schema and packet context.

This module defines validation primitives only. Registration, normalization,
reporting, and writes to case-local output directories belong to ingestion.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "model-reliability" / "submission-schema.json"
VOCABULARY_PATH = ROOT / "config" / "controlled-vocabularies.json"


@dataclass(frozen=True)
class SubmissionContext:
    """Authoritative packet and repository identifiers for one submission."""

    packet_id: str
    packet_hash: str
    case_id: str
    document_ids: frozenset[str]
    sentence_documents: Mapping[str, str]
    span_sentences: Mapping[str, str]
    item_ids: frozenset[str] = field(default_factory=frozenset)
    lexical_unit_ids: frozenset[str] = field(default_factory=frozenset)


def load_schema(path: Path = SCHEMA_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_controlled_vocabularies(path: Path = VOCABULARY_PATH) -> dict[str, set[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        name: {
            str(entry["id"])
            for entry in entries
            if isinstance(entry, dict) and entry.get("id")
        }
        for name, entries in data.items()
        if isinstance(entries, list)
    }


def _path(parts: Iterable[Any]) -> str:
    rendered = "$"
    for part in parts:
        rendered += f"[{part}]" if isinstance(part, int) else f".{part}"
    return rendered


def validate_submission(
    submission: Mapping[str, Any],
    context: SubmissionContext,
    *,
    schema: Mapping[str, Any] | None = None,
    vocabularies: Mapping[str, set[str]] | None = None,
) -> list[str]:
    """Return every contract violation without mutating or dropping input rows."""

    active_schema = dict(schema) if schema is not None else load_schema()
    validator = Draft202012Validator(active_schema, format_checker=FormatChecker())
    errors = [
        f"{_path(error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(submission), key=lambda item: list(item.absolute_path))
    ]

    if submission.get("packet_id") != context.packet_id:
        errors.append("$.packet_id: does not match the packet manifest")
    if submission.get("packet_hash") != context.packet_hash:
        errors.append("$.packet_hash: does not match the packet manifest")
    if submission.get("case_id") != context.case_id:
        errors.append("$.case_id: does not match the packet case")

    vocab = vocabularies if vocabularies is not None else load_controlled_vocabularies()
    source_domains = vocab.get("source_domains", set())
    target_domains = vocab.get("target_domains", set())
    seen_items: set[str] = set()
    seen_layer_spans: set[tuple[str, tuple[str, ...]]] = set()

    items = submission.get("items")
    if not isinstance(items, list):
        return errors

    for index, raw_item in enumerate(items):
        if not isinstance(raw_item, Mapping):
            continue
        prefix = f"$.items[{index}]"
        item_id = raw_item.get("item_id")
        task_layer = raw_item.get("task_layer")
        document_id = raw_item.get("document_id")
        sentence_id = raw_item.get("sentence_id")
        span_ids = raw_item.get("span_ids")

        if item_id in seen_items:
            errors.append(f"{prefix}.item_id: duplicate item ID `{item_id}`")
        elif isinstance(item_id, str):
            seen_items.add(item_id)
        if context.item_ids and item_id not in context.item_ids:
            errors.append(f"{prefix}.item_id: unknown packet item ID `{item_id}`")
        if raw_item.get("case_id") != context.case_id:
            errors.append(f"{prefix}.case_id: does not match the packet case")
        if raw_item.get("source_language") != submission.get("source_language"):
            errors.append(f"{prefix}.source_language: does not match the submission language")
        if document_id not in context.document_ids:
            errors.append(f"{prefix}.document_id: unknown document ID `{document_id}`")
        if sentence_id not in context.sentence_documents:
            errors.append(f"{prefix}.sentence_id: unknown sentence ID `{sentence_id}`")
        elif context.sentence_documents[sentence_id] != document_id:
            errors.append(f"{prefix}.sentence_id: does not belong to document `{document_id}`")

        if isinstance(span_ids, list):
            layer_span_key = (str(task_layer), tuple(sorted(str(value) for value in span_ids)))
            if layer_span_key in seen_layer_spans:
                errors.append(f"{prefix}.span_ids: duplicate span set for task layer `{task_layer}`")
            seen_layer_spans.add(layer_span_key)
            for span_id in span_ids:
                if span_id not in context.span_sentences:
                    errors.append(f"{prefix}.span_ids: unknown span ID `{span_id}`")
                elif context.span_sentences[span_id] != sentence_id:
                    errors.append(f"{prefix}.span_ids: span ID `{span_id}` belongs to another sentence")

        lexical_units = raw_item.get("lexical_units")
        if isinstance(lexical_units, list):
            for unit_index, raw_unit in enumerate(lexical_units):
                if not isinstance(raw_unit, Mapping):
                    continue
                unit_id = raw_unit.get("lexical_unit_id")
                span_id = raw_unit.get("span_id")
                unit_prefix = f"{prefix}.lexical_units[{unit_index}]"
                if context.lexical_unit_ids and unit_id not in context.lexical_unit_ids:
                    errors.append(f"{unit_prefix}.lexical_unit_id: unknown lexical-unit ID `{unit_id}`")
                if isinstance(span_ids, list) and span_id not in span_ids:
                    errors.append(f"{unit_prefix}.span_id: is not declared in the item's span_ids")
                start = raw_unit.get("char_offset_start")
                end = raw_unit.get("char_offset_end")
                if isinstance(start, int) and isinstance(end, int) and end <= start:
                    errors.append(f"{unit_prefix}.char_offset_end: must be greater than char_offset_start")

        case_fields = raw_item.get("case_fields")
        if isinstance(case_fields, Mapping):
            prefix_value = f"{context.case_id}__"
            for key in case_fields:
                if not str(key).startswith(prefix_value):
                    errors.append(f"{prefix}.case_fields.{key}: must use the `{prefix_value}` namespace")

        cmt = raw_item.get("cmt")
        if isinstance(cmt, Mapping):
            primary = cmt.get("source_domain_primary")
            if isinstance(primary, str) and primary not in source_domains:
                errors.append(f"{prefix}.cmt.source_domain_primary: unknown controlled value `{primary}`")
            for secondary in cmt.get("source_domain_secondary", []):
                if isinstance(secondary, str) and secondary not in source_domains:
                    errors.append(f"{prefix}.cmt.source_domain_secondary: unknown controlled value `{secondary}`")
            target = cmt.get("target_domain")
            if isinstance(target, str) and target not in target_domains:
                errors.append(f"{prefix}.cmt.target_domain: unknown controlled value `{target}`")

    return errors


def assert_valid_submission(
    submission: Mapping[str, Any],
    context: SubmissionContext,
    **kwargs: Any,
) -> None:
    """Raise ValueError with all violations when a submission is invalid."""

    errors = validate_submission(submission, context, **kwargs)
    if errors:
        raise ValueError("Invalid model-reliability submission:\n- " + "\n- ".join(errors))
