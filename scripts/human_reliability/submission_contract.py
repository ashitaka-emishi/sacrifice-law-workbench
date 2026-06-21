#!/usr/bin/env python3
"""Validate completed human-coder submissions against packet context.

This module owns exchange-contract validation only. Raw-byte preservation,
CSV parsing, registration, and normalized output belong to issue #81.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "human-reliability" / "submission-schema.json"
CSV_CONTRACT_PATH = ROOT / "schemas" / "human-reliability" / "submission-csv-contract.json"
VOCABULARY_PATH = ROOT / "config" / "controlled-vocabularies.json"


@dataclass(frozen=True)
class ResponseContext:
    """Packet-authoritative identifiers for one sampled response item."""

    document_id: str
    sentence_id: str
    source_span_id: str | None
    lexical_unit_ids: tuple[str, ...]


@dataclass(frozen=True)
class SubmissionContext:
    """Cohort and packet identity required to validate one submission."""

    cohort_id: str
    cohort_version: str
    case_id: str
    sample_id: str
    sample_version: str
    packet_id: str
    packet_hash: str
    source_language: str
    task_layer: str
    codebook_version: str
    training_version: str
    calibration_id: str
    primary_coder_ids: frozenset[str]
    responses: Mapping[str, ResponseContext]
    ai_assistance_allowed: bool = False


def load_schema(path: Path = SCHEMA_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv_contract(path: Path = CSV_CONTRACT_PATH) -> dict[str, Any]:
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
    """Return all structural and contextual violations without mutating input."""

    active_schema = dict(schema) if schema is not None else load_schema()
    validator = Draft202012Validator(active_schema, format_checker=FormatChecker())
    errors = [
        f"{_path(error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(submission), key=lambda item: list(item.absolute_path))
    ]

    expected_identity = {
        "cohort_id": context.cohort_id,
        "cohort_version": context.cohort_version,
        "case_id": context.case_id,
        "sample_id": context.sample_id,
        "sample_version": context.sample_version,
        "packet_id": context.packet_id,
        "packet_hash": context.packet_hash,
        "source_language": context.source_language,
        "task_layer": context.task_layer,
        "codebook_version": context.codebook_version,
        "training_version": context.training_version,
        "calibration_id": context.calibration_id,
    }
    for field, expected in expected_identity.items():
        if submission.get(field) != expected:
            errors.append(f"$.{field}: does not match the approved cohort and packet context")
    if submission.get("ai_assistance_used") is True and not context.ai_assistance_allowed:
        errors.append("$.ai_assistance_used: is not allowed by this independent cohort")
    if submission.get("coder_id") not in context.primary_coder_ids:
        errors.append(f"$.coder_id: is not an assigned primary coder for cohort `{context.cohort_id}`")

    vocab = vocabularies if vocabularies is not None else load_controlled_vocabularies()
    source_domains = vocab.get("source_domains", set())
    target_domains = vocab.get("target_domains", set())
    seen_items: set[str] = set()
    responses = submission.get("responses")
    if not isinstance(responses, list):
        return errors

    for index, raw_response in enumerate(responses):
        if not isinstance(raw_response, Mapping):
            continue
        prefix = f"$.responses[{index}]"
        item_id = raw_response.get("item_id")
        if not isinstance(item_id, str):
            continue
        if item_id in seen_items:
            errors.append(f"{prefix}.item_id: duplicate item ID `{item_id}`")
            continue
        seen_items.add(item_id)
        expected = context.responses.get(item_id)
        if expected is None:
            errors.append(f"{prefix}.item_id: unknown packet item ID `{item_id}`")
            continue
        if raw_response.get("task_layer") != context.task_layer:
            errors.append(f"{prefix}.task_layer: does not match the cohort task layer")
        for field, expected_value in (
            ("document_id", expected.document_id),
            ("sentence_id", expected.sentence_id),
            ("source_span_id", expected.source_span_id),
        ):
            if raw_response.get(field) != expected_value:
                errors.append(f"{prefix}.{field}: does not match packet item `{item_id}`")

        lexical_unit_ids = raw_response.get("lexical_unit_ids")
        if isinstance(lexical_unit_ids, list):
            submitted_ids = tuple(str(value) for value in lexical_unit_ids)
            if len(submitted_ids) != len(set(submitted_ids)):
                errors.append(f"{prefix}.lexical_unit_ids: contains duplicate IDs")
            if set(submitted_ids) != set(expected.lexical_unit_ids):
                errors.append(f"{prefix}.lexical_unit_ids: does not match packet item `{item_id}`")

        lexical_responses = raw_response.get("lexical_unit_responses")
        if isinstance(lexical_responses, list):
            response_ids = [
                value.get("lexical_unit_id")
                for value in lexical_responses
                if isinstance(value, Mapping)
            ]
            if len(response_ids) != len(set(response_ids)):
                errors.append(f"{prefix}.lexical_unit_responses: contains duplicate lexical-unit IDs")
            if set(response_ids) != set(expected.lexical_unit_ids):
                errors.append(
                    f"{prefix}.lexical_unit_responses: must cover every packet lexical unit exactly once"
                )

        case_fields = raw_response.get("case_fields")
        if isinstance(case_fields, Mapping):
            required_prefix = f"{context.case_id}__"
            for key in case_fields:
                if not str(key).startswith(required_prefix):
                    errors.append(
                        f"{prefix}.case_fields.{key}: must use the `{required_prefix}` namespace"
                    )

        cmt = raw_response.get("cmt_response")
        if isinstance(cmt, Mapping):
            primary = cmt.get("source_domain_primary")
            if primary not in source_domains:
                errors.append(
                    f"{prefix}.cmt_response.source_domain_primary: unknown controlled value `{primary}`"
                )
            secondary = cmt.get("source_domain_secondary")
            if isinstance(secondary, list):
                for value in secondary:
                    if value not in source_domains:
                        errors.append(
                            f"{prefix}.cmt_response.source_domain_secondary: unknown controlled value `{value}`"
                        )
            target = cmt.get("target_domain")
            if target not in target_domains:
                errors.append(
                    f"{prefix}.cmt_response.target_domain: unknown controlled value `{target}`"
                )

    missing_items = sorted(set(context.responses) - seen_items)
    if missing_items:
        errors.append("$.responses: missing packet item(s): " + ", ".join(missing_items))
    return errors


def assert_valid_submission(
    submission: Mapping[str, Any],
    context: SubmissionContext,
    **kwargs: Any,
) -> None:
    errors = validate_submission(submission, context, **kwargs)
    if errors:
        raise ValueError("Invalid human-coder submission:\n- " + "\n- ".join(errors))
