#!/usr/bin/env python3
"""Ingest and validate one JSON or CSV human-coder submission."""
from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import hashlib
import io
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

try:
    from scripts.human_reliability.boundaries import protect_accepted_artifacts, safe_output_path
    from scripts.human_reliability.generate_packets import (
        canonical_json_bytes,
        sha256_bytes,
    )
    from scripts.human_reliability.submission_contract import (
        ResponseContext,
        SubmissionContext,
        validate_submission,
    )
except ModuleNotFoundError:
    from boundaries import protect_accepted_artifacts, safe_output_path  # type: ignore
    from generate_packets import canonical_json_bytes, sha256_bytes  # type: ignore
    from submission_contract import (  # type: ignore
        ResponseContext,
        SubmissionContext,
        validate_submission,
    )


ROOT = Path(__file__).resolve().parents[2]
SENSITIVE_PATTERN = re.compile(
    r"(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|client[_-]?secret)",
    re.IGNORECASE,
)
CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
COMMENT_FIELDS = {
    "conflict_details",
    "uncertainty_note",
    "notes",
    "rival_reading",
    "contextual_meaning",
    "basic_meaning",
    "basic_meaning_source",
    "contrast_explanation",
    "comparison_basis",
    "conceptual_mapping",
    "absence_scope",
    "presence_criterion",
}
BOOLEAN_FIELDS = {
    "qualification_attested",
    "source_language_qualified",
    "independence_attested",
    "ai_assistance_used",
}


class IngestionError(ValueError):
    """Raised when ingestion cannot safely preserve and register input."""


@dataclass
class ParsedSubmission:
    source_format: str
    envelope: dict[str, Any]
    raw_files: dict[str, bytes]
    errors: list[str]
    raw_rows: list[dict[str, Any]]
    row_response_indexes: list[int | None]


@dataclass(frozen=True)
class CohortContext:
    manifest: dict[str, Any]
    packet_manifest: dict[str, Any]
    validation_context: SubmissionContext


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise IngestionError(f"required file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise IngestionError(f"invalid JSON in {path}: {exc}") from exc


def read_json_object(path: Path) -> dict[str, Any]:
    value = read_json(path)
    if not isinstance(value, dict):
        raise IngestionError(f"expected a JSON object in {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def schema_errors(value: Any, schema: Mapping[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        f"{_path(error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(value), key=lambda item: list(item.absolute_path))
    ]


def _path(parts: Iterable[Any]) -> str:
    rendered = "$"
    for part in parts:
        rendered += f"[{part}]" if isinstance(part, int) else f".{part}"
    return rendered


def parse_json_submission(path: Path) -> ParsedSubmission:
    raw = path.read_bytes()
    errors: list[str] = []
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"$: invalid JSON submission: {exc}")
        value = {}
    if not isinstance(value, dict):
        errors.append("$: JSON submission must be an object")
        value = {}
    responses = value.get("responses")
    raw_rows = [dict(item) for item in responses if isinstance(item, dict)] if isinstance(responses, list) else []
    return ParsedSubmission(
        source_format="json",
        envelope=value,
        raw_files={"submission.json": raw},
        errors=errors,
        raw_rows=raw_rows,
        row_response_indexes=list(range(len(raw_rows))),
    )


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]], bytes]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise IngestionError(f"CSV must be UTF-8: {path}: {exc}") from exc
    try:
        reader = csv.DictReader(io.StringIO(text))
        fields = list(reader.fieldnames or [])
        rows: list[dict[str, str]] = []
        for row in reader:
            normalized = {str(key): value or "" for key, value in row.items() if key is not None}
            if row.get(None):
                normalized["__extra_values__"] = json.dumps(row[None], ensure_ascii=False)
            rows.append(normalized)
    except csv.Error as exc:
        raise IngestionError(f"invalid CSV in {path}: {exc}") from exc
    return fields, rows, raw


def _parse_json_cell(value: str, location: str, errors: list[str], default: Any) -> Any:
    if value == "":
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        errors.append(f"{location}: invalid JSON cell: {exc.msg}")
        return value


def _parse_bool(value: str, location: str, errors: list[str]) -> Any:
    if value == "true":
        return True
    if value == "false":
        return False
    errors.append(f"{location}: expected `true` or `false`")
    return value


def parse_csv_submission(path: Path, contract: Mapping[str, Any]) -> ParsedSubmission:
    fields, rows, raw = _read_csv(path)
    errors: list[str] = []
    metadata_columns = list(contract.get("metadata_columns", []))
    common_columns = list(contract.get("common_response_columns", []))
    layer_columns = contract.get("layer_columns", {})
    allowed = set(metadata_columns + common_columns)
    for values in layer_columns.values() if isinstance(layer_columns, Mapping) else []:
        if isinstance(values, list):
            allowed.update(str(value) for value in values)
    missing_base = sorted(set(metadata_columns + common_columns) - set(fields))
    extra = sorted(set(fields) - allowed)
    if missing_base:
        errors.append("$.csv: missing column(s): " + ", ".join(missing_base))
    if extra:
        errors.append("$.csv: unexpected column(s): " + ", ".join(extra))
    if not rows:
        errors.append("$.csv: expected at least one response row")

    metadata: dict[str, Any] = {}
    first = rows[0] if rows else {}
    for field in metadata_columns:
        raw_value = first.get(field, "")
        location = f"$.csv.{field}"
        if field in BOOLEAN_FIELDS:
            metadata[field] = _parse_bool(raw_value, location, errors)
        elif field == "conflict_details":
            metadata[field] = raw_value or None
        else:
            metadata[field] = raw_value
    for row_index, row in enumerate(rows, start=2):
        if "__extra_values__" in row:
            errors.append(f"$.csv (row {row_index}): extra cell value(s) were preserved")
        for field in metadata_columns:
            if row.get(field, "") != first.get(field, ""):
                errors.append(f"$.csv.{field} (row {row_index}): inconsistent repeated metadata")

    task_layer = str(metadata.get("task_layer") or "")
    required_layer_columns = (
        set(layer_columns.get(task_layer, [])) if isinstance(layer_columns, Mapping) else set()
    )
    unexpected_layer = sorted(
        set(fields) - set(metadata_columns) - set(common_columns) - required_layer_columns
    )
    missing_layer = sorted(required_layer_columns - set(fields))
    if missing_layer:
        errors.append(f"$.csv.{task_layer}: missing column(s): " + ", ".join(missing_layer))
    if unexpected_layer:
        errors.append(
            f"$.csv.{task_layer}: column(s) belong to another task layer: "
            + ", ".join(unexpected_layer)
        )

    grouped: dict[str, list[tuple[int, dict[str, str]]]] = {}
    order: list[str] = []
    for index, row in enumerate(rows):
        item_id = row.get("item_id", "")
        if item_id not in grouped:
            grouped[item_id] = []
            order.append(item_id)
        grouped[item_id].append((index, row))

    responses: list[dict[str, Any]] = []
    row_response_indexes: list[int | None] = [None] * len(rows)
    json_fields = {
        "case_fields",
        "lexical_unit_ids",
        "source_domain_secondary",
        "entailments",
        "agents",
        "patients",
        "beneficiaries",
        "excluded_agents",
    }
    for response_index, item_id in enumerate(order):
        group = grouped[item_id]
        if task_layer != "identification" and len(group) > 1:
            errors.append(
                f"$.responses[{response_index}].item_id: duplicate CSV rows for `{item_id}`"
            )
        first_row = group[0][1]
        response: dict[str, Any] = {
            "item_id": item_id,
            "task_layer": task_layer,
            "document_id": first_row.get("document_id", ""),
            "sentence_id": first_row.get("sentence_id", ""),
            "source_span_id": first_row.get("source_span_id") or None,
            "disposition": first_row.get("disposition", ""),
            "confidence": None,
            "uncertainty": first_row.get("uncertainty", ""),
            "uncertainty_note": first_row.get("uncertainty_note", ""),
            "out_of_scope_reason": first_row.get("out_of_scope_reason") or None,
            "notes": first_row.get("notes", ""),
            "case_fields": _parse_json_cell(
                first_row.get("case_fields", ""),
                f"$.responses[{response_index}].case_fields",
                errors,
                {},
            ),
        }
        confidence = first_row.get("confidence", "")
        if confidence:
            try:
                response["confidence"] = float(confidence)
            except ValueError:
                errors.append(f"$.responses[{response_index}].confidence: expected a number")
                response["confidence"] = confidence
        for row_index, row in group:
            row_response_indexes[row_index] = response_index
            for field in common_columns:
                if row.get(field, "") != first_row.get(field, ""):
                    errors.append(
                        f"$.responses[{response_index}].{field} "
                        f"(CSV row {row_index + 2}): inconsistent item metadata"
                    )

        out_of_scope = response["disposition"] == "out_of_scope"
        if task_layer == "identification":
            response["lexical_unit_ids"] = [row.get("lexical_unit_id", "") for _, row in group]
            if not out_of_scope:
                response["lexical_unit_responses"] = [
                    {
                        field: row.get(field, "")
                        for field in layer_columns.get("identification", [])
                    }
                    for _, row in group
                ]
        else:
            response["lexical_unit_ids"] = _parse_json_cell(
                first_row.get("lexical_unit_ids", ""),
                f"$.responses[{response_index}].lexical_unit_ids",
                errors,
                [],
            )
            if not out_of_scope:
                payload: dict[str, Any] = {}
                for field in layer_columns.get(task_layer, []):
                    if field == "lexical_unit_ids":
                        continue
                    value = first_row.get(field, "")
                    payload[field] = (
                        _parse_json_cell(
                            value,
                            f"$.responses[{response_index}].{task_layer}_response.{field}",
                            errors,
                            [],
                        )
                        if field in json_fields
                        else (value or None if field == "cluster_id" else value)
                    )
                response[f"{task_layer}_response"] = payload
        responses.append(response)
    return ParsedSubmission(
        source_format="csv",
        envelope={**metadata, "responses": responses},
        raw_files={"submission.csv": raw},
        errors=errors,
        raw_rows=rows,
        row_response_indexes=row_response_indexes,
    )


def _artifact_path(case_root: Path, relative: str, allowed_root: Path) -> Path:
    target = (case_root / relative).resolve()
    if not target.is_relative_to(allowed_root.resolve()):
        raise IngestionError(f"artifact path escapes allowed human-reliability directory: {relative}")
    return target


def _verify_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise IngestionError(f"{label} is missing: {path}")
    actual = sha256_bytes(path.read_bytes())
    if actual != expected:
        raise IngestionError(f"{label} hash mismatch: expected {expected}, found {actual}")


def cohort_hash(cohort: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(cohort))
    approval = payload.get("approval")
    if isinstance(approval, dict):
        approval["manifest_sha256"] = None
    return sha256_bytes(canonical_json_bytes(payload))


def load_cohort_context(root: Path, case_id: str, cohort_path: Path) -> CohortContext:
    case_root = (root / "cases" / case_id).resolve()
    human_root = (case_root / "quality" / "human-reliability").resolve()
    resolved_cohort = cohort_path.resolve()
    if not resolved_cohort.is_relative_to(human_root):
        raise IngestionError("cohort manifest must be inside the case human-reliability subtree")
    cohort = read_json_object(resolved_cohort)
    cohort_schema = read_json_object(
        root / "schemas" / "human-reliability" / "cohort-manifest-schema.json"
    )
    errors = schema_errors(cohort, cohort_schema)
    if errors:
        raise IngestionError("invalid cohort manifest: " + "; ".join(errors))
    if cohort.get("case_id") != case_id:
        raise IngestionError(f"cohort manifest case_id must be `{case_id}`")
    approval = cohort.get("approval")
    approved_hash = approval.get("manifest_sha256") if isinstance(approval, Mapping) else None
    if approved_hash != cohort_hash(cohort):
        raise IngestionError(
            "cohort approval.manifest_sha256 does not match canonical cohort content"
        )

    packet_path = _artifact_path(
        case_root,
        str(cohort["packet_manifest"]),
        human_root / "packets",
    )
    packet_manifest = read_json_object(packet_path)
    packet_schema = read_json_object(
        root / "schemas" / "human-reliability" / "packet-manifest-schema.json"
    )
    packet_errors = schema_errors(packet_manifest, packet_schema)
    if packet_errors:
        raise IngestionError("invalid packet manifest: " + "; ".join(packet_errors))
    unsigned = {key: value for key, value in packet_manifest.items() if key != "packet_hash"}
    expected_packet_hash = sha256_bytes(canonical_json_bytes(unsigned))
    if packet_manifest.get("packet_hash") != expected_packet_hash:
        raise IngestionError("packet manifest hash does not match canonical content")

    for field in (
        "case_id",
        "sample_id",
        "sample_version",
        "packet_id",
        "source_language",
        "task_layer",
        "codebook_version",
    ):
        if cohort.get(field) != packet_manifest.get(field):
            raise IngestionError(f"cohort `{field}` does not match packet manifest")
    if sorted(cohort["rights_constraints"]) != sorted(packet_manifest["rights_constraints"]):
        raise IngestionError("cohort rights_constraints do not match packet manifest")
    restricted = any(
        token in str(value).lower().replace("_", "-")
        for value in packet_manifest["rights_constraints"]
        for token in ("local-only", "restricted", "do-not-commit")
    )
    if restricted and cohort["storage_policy"] != "local_only":
        raise IngestionError("restricted packet requires cohort storage_policy `local_only`")
    if cohort["storage_policy"] == "local_only" and (root / ".git").exists():
        local_output = (
            case_root / "quality" / "human-reliability" / "submissions"
        ).relative_to(root)
        ignored = subprocess.run(
            ["git", "check-ignore", "--quiet", local_output.as_posix()],
            cwd=root,
            check=False,
        )
        if ignored.returncode != 0:
            raise IngestionError(
                f"local_only submission path is not gitignored: {local_output}"
            )
    if len(cohort["primary_coder_ids"]) < int(cohort["required_primary_coders"]):
        raise IngestionError(
            "cohort primary_coder_ids cannot satisfy required_primary_coders"
        )

    packet_dir = packet_path.parent.resolve()
    packet_items: dict[str, ResponseContext] = {}
    for payload in packet_manifest["payloads"]:
        payload_path = _artifact_path(case_root, str(payload["path"]), packet_dir)
        _verify_hash(payload_path, str(payload["hash"]), "packet payload")
        if payload.get("media_type") != "application/x-ndjson":
            continue
        for line_number, line in enumerate(payload_path.read_text(encoding="utf-8").splitlines(), start=1):
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise IngestionError(
                    f"invalid packet JSONL at {payload_path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(item, dict):
                raise IngestionError(f"packet item must be an object at {payload_path}:{line_number}")
            item_id = str(item.get("item_id") or "")
            if not item_id or item_id in packet_items:
                raise IngestionError(f"missing or duplicate packet item ID `{item_id}`")
            packet_items[item_id] = ResponseContext(
                document_id=str(item.get("document_id") or ""),
                sentence_id=str(item.get("sentence_id") or ""),
                source_span_id=(
                    str(item["source_span_id"]) if item.get("source_span_id") else None
                ),
                lexical_unit_ids=tuple(
                    str(unit.get("lexical_unit_id") or "")
                    for unit in item.get("lexical_units", [])
                    if isinstance(unit, Mapping)
                ),
            )
    if not packet_items:
        raise IngestionError("packet manifest has no JSONL coding payload")
    return CohortContext(
        manifest=cohort,
        packet_manifest=packet_manifest,
        validation_context=SubmissionContext(
            cohort_id=str(cohort["cohort_id"]),
            cohort_version=str(cohort["cohort_version"]),
            case_id=case_id,
            sample_id=str(cohort["sample_id"]),
            sample_version=str(cohort["sample_version"]),
            packet_id=str(cohort["packet_id"]),
            packet_hash=str(packet_manifest["packet_hash"]),
            source_language=str(cohort["source_language"]),
            task_layer=str(cohort["task_layer"]),
            codebook_version=str(cohort["codebook_version"]),
            training_version=str(cohort["training_version"]),
            calibration_id=str(cohort["calibration_id"]),
            primary_coder_ids=frozenset(str(value) for value in cohort["primary_coder_ids"]),
            responses=packet_items,
            ai_assistance_allowed=bool(cohort["ai_assistance_allowed"]),
        ),
    )


def _comment_errors(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key) in COMMENT_FIELDS and isinstance(child, str):
                if len(child) > 10000:
                    errors.append(f"{child_path}: comment exceeds 10000 characters")
                if CONTROL_CHARACTER_PATTERN.search(child):
                    errors.append(f"{child_path}: comment contains a prohibited control character")
            errors.extend(_comment_errors(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_comment_errors(child, f"{path}[{index}]"))
    return errors


def _raw_digest(raw_files: Mapping[str, bytes]) -> str:
    digest = hashlib.sha256()
    for filename in sorted(raw_files):
        digest.update(filename.encode("utf-8"))
        digest.update(b"\0")
        digest.update(raw_files[filename])
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _contains_sensitive_data(raw_files: Mapping[str, bytes]) -> bool:
    return any(
        SENSITIVE_PATTERN.search(value.decode("utf-8", errors="ignore"))
        for value in raw_files.values()
    )


def _row_results(parsed: ParsedSubmission, errors: Sequence[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for index, row in enumerate(parsed.raw_rows):
        response_index = (
            parsed.row_response_indexes[index]
            if index < len(parsed.row_response_indexes)
            else None
        )
        prefix = f"$.responses[{response_index}]" if response_index is not None else "$.csv"
        row_errors = [
            error
            for error in errors
            if error.startswith(prefix) or f"row {index + 2}" in error
        ]
        results.append(
            {
                "index": index,
                "item_id": row.get("item_id") if isinstance(row, Mapping) else None,
                "status": "invalid" if row_errors else "valid",
                "errors": row_errors,
                "raw_row": row,
            }
        )
    return results


def cohort_ingestion_summary(
    entries: Sequence[Mapping[str, Any]],
    cohort: Mapping[str, Any],
) -> dict[str, Any]:
    matching = [
        entry
        for entry in entries
        if entry.get("cohort_id") == cohort.get("cohort_id")
        and entry.get("cohort_version") == cohort.get("cohort_version")
    ]
    effective: dict[str, Mapping[str, Any]] = {}
    for entry in matching:
        identity = str(entry.get("coder_id") or entry.get("submission_id") or entry.get("registration_id"))
        effective[identity] = entry
    valid = [entry for entry in effective.values() if entry.get("status") == "valid"]
    invalid = [entry for entry in effective.values() if entry.get("status") == "invalid"]
    coder_ids = sorted(
        {
            str(entry["coder_id"])
            for entry in valid
            if isinstance(entry.get("coder_id"), str) and entry.get("coder_id")
        }
    )
    required = int(cohort["required_primary_coders"])
    if not matching:
        state = "absent"
    elif invalid:
        state = "invalid"
    elif len(coder_ids) >= required:
        state = "complete"
    else:
        state = "partial"
    return {
        "cohort_id": str(cohort["cohort_id"]),
        "cohort_version": str(cohort["cohort_version"]),
        "state": state,
        "required_primary_coders": required,
        "valid_primary_coders": coder_ids,
        "valid_submission_count": len(valid),
        "invalid_submission_count": len(invalid),
        "registration_ids": [str(entry["registration_id"]) for entry in matching],
    }


def _write_ingestion_status(
    case_root: Path,
    case_id: str,
    cohort: Mapping[str, Any],
    entries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    status_path = safe_output_path(
        case_root, "quality/human-reliability/ingestion-status.json"
    )
    status_document = read_json_object(status_path) if status_path.exists() else {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "cohorts": [],
    }
    cohorts = status_document.get("cohorts")
    if status_document.get("case_id") != case_id or not isinstance(cohorts, list):
        raise IngestionError("ingestion-status.json has invalid case_id or cohorts")
    summary = cohort_ingestion_summary(entries, cohort)
    cohorts = [
        item
        for item in cohorts
        if not (
            item.get("cohort_id") == summary["cohort_id"]
            and item.get("cohort_version") == summary["cohort_version"]
        )
    ]
    cohorts.append(summary)
    status_document["cohorts"] = sorted(
        cohorts, key=lambda item: (item["cohort_id"], item["cohort_version"])
    )
    write_json(status_path, status_document)
    return summary


@protect_accepted_artifacts
def refresh_ingestion_status(
    root: Path,
    case_id: str,
    cohort_path: Path,
) -> dict[str, Any]:
    """Write current ingestion status, including `absent` before submissions."""

    root = root.resolve()
    case_root = root / "cases" / case_id
    cohort = load_cohort_context(root, case_id, cohort_path)
    register_path = safe_output_path(
        case_root, "quality/human-reliability/submissions/submission-register.json"
    )
    entries: list[Mapping[str, Any]] = []
    if register_path.exists():
        register = read_json_object(register_path)
        raw_entries = register.get("submissions")
        if register.get("case_id") != case_id or not isinstance(raw_entries, list):
            raise IngestionError("submission register has an invalid case_id or submissions field")
        entries = [entry for entry in raw_entries if isinstance(entry, Mapping)]
    return _write_ingestion_status(case_root, case_id, cohort.manifest, entries)


def _markdown_report(report: Mapping[str, Any]) -> str:
    lines = [
        f"# Human Submission Validation: {report['registration_id']}",
        "",
        f"- Status: **{report['status']}**",
        f"- Cohort ingestion state: **{report['cohort_ingestion_state']}**",
        f"- Source format: `{report['source_format']}`",
        f"- Submission ID: `{report.get('submission_id') or 'missing'}`",
        f"- Coder ID: `{report.get('coder_id') or 'missing'}`",
        f"- Errors: {len(report['errors'])}",
        f"- Rows received: {len(report['row_results'])}",
        "",
    ]
    if report["errors"]:
        lines.extend(["## Errors", ""])
        lines.extend(f"- {error}" for error in report["errors"])
        lines.append("")
    lines.extend(["## Row results", ""])
    lines.extend(
        f"- Row {row['index'] + 1}, `{row.get('item_id') or 'missing'}`: {row['status']}"
        for row in report["row_results"]
    )
    lines.append("")
    return "\n".join(lines)


@protect_accepted_artifacts
def ingest_submission(
    root: Path,
    case_id: str,
    cohort_path: Path,
    parsed: ParsedSubmission,
) -> dict[str, Any]:
    root = root.resolve()
    case_root = root / "cases" / case_id
    if not case_root.is_dir():
        raise IngestionError(f"unknown case `{case_id}`")
    if _contains_sensitive_data(parsed.raw_files):
        raise IngestionError("refusing to store a submission that appears to contain credentials")
    cohort = load_cohort_context(root, case_id, cohort_path)
    submission_schema = read_json_object(
        root / "schemas" / "human-reliability" / "submission-schema.json"
    )
    vocabulary = read_json_object(root / "config" / "controlled-vocabularies.json")
    vocabularies = {
        key: {
            str(item["id"])
            for item in values
            if isinstance(item, Mapping) and item.get("id")
        }
        for key, values in vocabulary.items()
        if isinstance(values, list)
    }
    errors = list(parsed.errors)
    errors.extend(
        validate_submission(
            parsed.envelope,
            cohort.validation_context,
            schema=submission_schema,
            vocabularies=vocabularies,
        )
    )
    errors.extend(_comment_errors(parsed.envelope))

    raw_hash = _raw_digest(parsed.raw_files)
    registration_id = "human-submission-" + raw_hash.removeprefix("sha256:")[:16]
    register_path = safe_output_path(
        case_root, "quality/human-reliability/submissions/submission-register.json"
    )
    register = read_json_object(register_path) if register_path.exists() else {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "submissions": [],
    }
    entries = register.get("submissions")
    if register.get("case_id") != case_id or not isinstance(entries, list):
        raise IngestionError("submission register has an invalid case_id or submissions field")

    existing = next(
        (entry for entry in entries if entry.get("registration_id") == registration_id),
        None,
    )
    if existing:
        raw_dir = safe_output_path(
            case_root,
            f"quality/human-reliability/submissions/raw/{registration_id}",
        )
        for filename, expected_bytes in parsed.raw_files.items():
            raw_path = raw_dir / filename
            if not raw_path.is_file() or raw_path.read_bytes() != expected_bytes:
                raise IngestionError(f"immutable raw registration was altered: {raw_path}")
        report_path = safe_output_path(
            case_root,
            f"quality/human-reliability/normalized/validation-reports/{registration_id}.json",
        )
        return read_json_object(report_path)

    submission_id = parsed.envelope.get("submission_id")
    coder_id = parsed.envelope.get("coder_id")
    cohort_id = parsed.envelope.get("cohort_id")
    cohort_version = parsed.envelope.get("cohort_version")
    for entry in entries:
        if entry.get("status") != "valid":
            continue
        if submission_id and entry.get("submission_id") == submission_id:
            errors.append(f"$.submission_id: duplicate valid submission ID `{submission_id}`")
        if (
            coder_id
            and entry.get("coder_id") == coder_id
            and entry.get("cohort_id") == cohort_id
            and entry.get("cohort_version") == cohort_version
        ):
            errors.append(f"$.coder_id: duplicate valid submission for coder `{coder_id}`")
    errors = list(dict.fromkeys(errors))
    status = "valid" if not errors else "invalid"
    registered_at = utc_now()

    raw_dir = safe_output_path(
        case_root, f"quality/human-reliability/submissions/raw/{registration_id}"
    )
    report_json_path = safe_output_path(
        case_root,
        f"quality/human-reliability/normalized/validation-reports/{registration_id}.json",
    )
    report_md_path = safe_output_path(
        case_root,
        f"quality/human-reliability/normalized/validation-reports/{registration_id}.md",
    )
    normalized_path = safe_output_path(
        case_root, "quality/human-reliability/normalized/normalized-coder-runs.json"
    )
    normalized = read_json_object(normalized_path) if normalized_path.exists() else {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "runs": [],
    }
    runs = normalized.get("runs")
    if normalized.get("case_id") != case_id or not isinstance(runs, list):
        raise IngestionError("normalized-coder-runs.json has invalid case_id or runs")

    entry = {
        "registration_id": registration_id,
        "registered_at": registered_at,
        "cohort_id": cohort_id,
        "cohort_version": cohort_version,
        "submission_id": submission_id,
        "coder_id": coder_id,
        "packet_id": parsed.envelope.get("packet_id"),
        "source_format": parsed.source_format,
        "raw_hash": raw_hash,
        "status": status,
        "validation_report": report_json_path.relative_to(case_root).as_posix(),
    }
    entries.append(entry)
    summary = cohort_ingestion_summary(entries, cohort.manifest)
    report = {
        "schema_version": "1.0.0",
        "registration_id": registration_id,
        "registered_at": registered_at,
        "case_id": case_id,
        "cohort_id": cohort_id,
        "cohort_version": cohort_version,
        "submission_id": submission_id,
        "coder_id": coder_id,
        "source_format": parsed.source_format,
        "raw_hash": raw_hash,
        "status": status,
        "errors": errors,
        "row_results": _row_results(parsed, errors),
        "raw_rows": parsed.raw_rows,
        "cohort_ingestion_state": summary["state"],
    }

    raw_dir.mkdir(parents=True, exist_ok=False)
    for filename, data in parsed.raw_files.items():
        raw_path = raw_dir / filename
        raw_path.write_bytes(data)
        raw_path.chmod(0o444)
    write_json(report_json_path, report)
    report_md_path.write_text(_markdown_report(report), encoding="utf-8")
    register["submissions"] = entries
    write_json(register_path, register)
    if status == "valid":
        runs.append(
            {
                "registration_id": registration_id,
                "registered_at": registered_at,
                "raw_hash": raw_hash,
                "cohort_id": str(cohort_id),
                "cohort_version": str(cohort_version),
                "coder_id": str(coder_id),
                "submission": parsed.envelope,
            }
        )
    normalized["runs"] = runs
    write_json(normalized_path, normalized)
    _write_ingestion_status(case_root, case_id, cohort.manifest, entries)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument("--cohort", type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--json", dest="json_path", type=Path)
    source.add_argument("--csv", dest="csv_path", type=Path)
    source.add_argument("--status-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.status_only:
            summary = refresh_ingestion_status(ROOT, args.case_id, args.cohort)
            print(
                f"{args.case_id}: cohort `{summary['cohort_id']}` ingestion is "
                f"{summary['state']}"
            )
            return 0
        if args.json_path:
            parsed = parse_json_submission(args.json_path)
        else:
            contract = read_json_object(
                ROOT / "schemas" / "human-reliability" / "submission-csv-contract.json"
            )
            parsed = parse_csv_submission(args.csv_path, contract)
        report = ingest_submission(ROOT, args.case_id, args.cohort, parsed)
    except (IngestionError, OSError) as exc:
        parser.error(str(exc))
    print(
        f"{args.case_id}: {report['registration_id']} is {report['status']}; "
        f"cohort ingestion is {report['cohort_ingestion_state']}"
    )
    return 0 if report["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
