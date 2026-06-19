#!/usr/bin/env python3
"""Ingest and validate one manual JSON or two-file CSV model submission."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

try:
    from scripts.model_reliability.boundaries import safe_output_path
    from scripts.model_reliability.generate_packets import canonical_json_bytes, sha256_bytes
    from scripts.model_reliability.submission_contract import (
        SubmissionContext,
        validate_submission,
    )
except ModuleNotFoundError:  # Direct execution from scripts/model_reliability/.
    try:
        from model_reliability.boundaries import safe_output_path
        from model_reliability.generate_packets import (
            canonical_json_bytes,
            sha256_bytes,
        )
        from model_reliability.submission_contract import (
            SubmissionContext,
            validate_submission,
        )
    except ModuleNotFoundError:
        from boundaries import safe_output_path  # type: ignore
        from generate_packets import canonical_json_bytes, sha256_bytes  # type: ignore
        from submission_contract import (  # type: ignore
            SubmissionContext,
            validate_submission,
        )


ROOT = Path(__file__).resolve().parents[2]
SENSITIVE_PATTERN = re.compile(
    r"(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|client[_-]?secret|account[_-]?id)",
    re.IGNORECASE,
)
JSON_ITEM_COLUMNS = {
    "span_ids",
    "lexical_units",
    "source_risk_flags",
    "identification",
    "cmt",
    "interpretation",
    "uncertainty",
    "case_fields",
}
OPTIONAL_ITEM_COLUMNS = {"sentence_gloss_en", "identification", "cmt", "interpretation"}


class IngestionError(ValueError):
    """Raised when ingestion cannot safely register a submission."""


@dataclass
class ParsedSubmission:
    source_format: str
    envelope: dict[str, Any]
    raw_files: dict[str, bytes]
    errors: list[str]
    raw_metadata_rows: list[dict[str, str]]
    raw_item_rows: list[dict[str, str]]


@dataclass
class PacketContext:
    manifest: dict[str, Any]
    validation_context: SubmissionContext
    items: dict[str, dict[str, Any]]
    prompts: dict[str, dict[str, Any]]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise IngestionError(f"required file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise IngestionError(f"invalid JSON in {path}: {exc}") from exc
    return data


def read_json_object(path: Path) -> dict[str, Any]:
    data = read_json(path)
    if not isinstance(data, dict):
        raise IngestionError(f"expected a JSON object in {path}")
    return data


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]], bytes]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise IngestionError(f"CSV must be UTF-8: {path}: {exc}") from exc
    try:
        reader = csv.DictReader(io.StringIO(text))
        fields = list(reader.fieldnames or [])
        rows = []
        for row in reader:
            normalized = {
                str(key): value or "" for key, value in row.items() if key is not None
            }
            if row.get(None):
                normalized["__extra_values__"] = json.dumps(row[None], ensure_ascii=False)
            rows.append(normalized)
    except csv.Error as exc:
        raise IngestionError(f"invalid CSV in {path}: {exc}") from exc
    return fields, rows, raw


def _parse_json_cell(value: str, location: str, errors: list[str]) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        errors.append(f"{location}: invalid JSON cell: {exc.msg}")
        return value


def parse_json_submission(path: Path) -> ParsedSubmission:
    raw = path.read_bytes()
    errors: list[str] = []
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"$: invalid JSON submission: {exc}")
        parsed = {}
    if not isinstance(parsed, dict):
        errors.append("$: JSON submission must be an object")
        parsed = {}
    raw_items = parsed.get("items", [])
    return ParsedSubmission(
        source_format="json",
        envelope=parsed,
        raw_files={"submission.json": raw},
        errors=errors,
        raw_metadata_rows=[],
        raw_item_rows=[dict(item) for item in raw_items if isinstance(item, dict)]
        if isinstance(raw_items, list)
        else [],
    )


def parse_csv_submission(
    metadata_path: Path,
    items_path: Path,
    contract: Mapping[str, Any],
) -> ParsedSubmission:
    metadata_fields, metadata_rows, metadata_raw = _read_csv(metadata_path)
    item_fields, item_rows, items_raw = _read_csv(items_path)
    errors: list[str] = []
    files = contract.get("files", {}) if isinstance(contract, Mapping) else {}
    metadata_required = set(files.get("metadata", {}).get("required_columns", []))
    items_required = set(files.get("items", {}).get("required_columns", []))
    for label, actual, required in (
        ("metadata", set(metadata_fields), metadata_required),
        ("items", set(item_fields), items_required),
    ):
        missing = sorted(required - actual)
        extra = sorted(actual - required)
        if missing:
            errors.append(f"$.csv.{label}: missing column(s): {', '.join(missing)}")
        if extra:
            errors.append(f"$.csv.{label}: unexpected column(s): {', '.join(extra)}")
    if len(metadata_rows) != 1:
        errors.append(f"$.csv.metadata: expected exactly one row, found {len(metadata_rows)}")
    for row_index, row in enumerate(metadata_rows, start=2):
        if "__extra_values__" in row:
            errors.append(f"$.csv.metadata (row {row_index}): extra cell value(s) were preserved")
    for row_index, row in enumerate(item_rows, start=2):
        if "__extra_values__" in row:
            errors.append(f"$.items[{row_index - 2}] (CSV row {row_index}): extra cell value(s) were preserved")

    metadata = metadata_rows[0] if metadata_rows else {}
    language_capabilities = _parse_json_cell(
        metadata.get("language_capabilities", ""), "$.csv.metadata.language_capabilities", errors
    )
    settings = _parse_json_cell(metadata.get("settings", ""), "$.csv.metadata.settings", errors)
    envelope: dict[str, Any] = {
        key: metadata.get(key, "")
        for key in (
            "schema_version",
            "submission_id",
            "case_id",
            "sample_id",
            "sample_version",
            "packet_id",
            "packet_hash",
            "prompt_id",
            "prompt_hash",
            "source_language",
            "code_revision",
        )
    }
    envelope["run"] = {
        "run_id": metadata.get("run_id", ""),
        "provider": metadata.get("provider", ""),
        "model": metadata.get("model", ""),
        "model_version": metadata.get("model_version") or None,
        "completed_at": metadata.get("completed_at", ""),
        "language_capabilities": language_capabilities,
        "settings": settings,
    }

    normalized_items: list[dict[str, Any]] = []
    for item_index, row in enumerate(item_rows):
        csv_row = item_index + 2
        item: dict[str, Any] = {}
        for field in item_fields:
            value = row.get(field, "")
            location = f"$.items[{item_index}].{field} (CSV row {csv_row})"
            if field in OPTIONAL_ITEM_COLUMNS and value == "":
                continue
            if field in JSON_ITEM_COLUMNS:
                item[field] = _parse_json_cell(value, location, errors)
            elif field == "confidence":
                try:
                    item[field] = float(value)
                except ValueError:
                    errors.append(f"{location}: expected a number")
                    item[field] = value
            else:
                item[field] = value
        normalized_items.append(item)
    envelope["items"] = normalized_items
    return ParsedSubmission(
        source_format="csv",
        envelope=envelope,
        raw_files={"metadata.csv": metadata_raw, "items.csv": items_raw},
        errors=errors,
        raw_metadata_rows=metadata_rows,
        raw_item_rows=item_rows,
    )


def _verify_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise IngestionError(f"packet {label} is missing: {path}")
    actual = sha256_bytes(path.read_bytes())
    if actual != expected:
        raise IngestionError(f"packet {label} hash mismatch: expected {expected}, found {actual}")


def _packet_artifact_path(case_root: Path, packet_root: Path, relative: str) -> Path:
    target = (case_root / relative).resolve()
    if not target.is_relative_to(packet_root.resolve()):
        raise IngestionError(f"packet artifact path escapes packet directory: {relative}")
    return target


def _schema_errors(instance: Any, schema: Mapping[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        error.message
        for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    ]


def load_packet_context(root: Path, case_id: str) -> PacketContext:
    case_root = root / "cases" / case_id
    packet_root = case_root / "quality" / "model-reliability" / "packets"
    manifest_path = packet_root / "packet-manifest.json"
    manifest = read_json_object(manifest_path)
    manifest_schema = read_json_object(
        root / "schemas" / "model-reliability" / "packet-manifest-schema.json"
    )
    manifest_errors = _schema_errors(manifest, manifest_schema)
    if manifest_errors:
        raise IngestionError("invalid packet manifest: " + "; ".join(manifest_errors))
    if manifest.get("case_id") != case_id:
        raise IngestionError(f"packet manifest case_id must be `{case_id}`")
    expected_hash = str(manifest.get("packet_hash") or "")
    without_hash = {key: value for key, value in manifest.items() if key != "packet_hash"}
    actual_hash = sha256_bytes(canonical_json_bytes(without_hash))
    if actual_hash != expected_hash:
        raise IngestionError(
            f"packet manifest hash mismatch: expected {expected_hash}, calculated {actual_hash}"
        )

    packet_items: dict[str, dict[str, Any]] = {}
    sentence_documents: dict[str, str] = {}
    span_sentences: dict[str, str] = {}
    document_ids: set[str] = set()
    lexical_unit_ids: set[str] = set()
    item_schema = read_json_object(
        root / "schemas" / "model-reliability" / "packet-item-schema.json"
    )
    for payload in manifest.get("payloads", []):
        if not isinstance(payload, dict):
            raise IngestionError("packet manifest contains an invalid payload entry")
        path = _packet_artifact_path(
            case_root, packet_root, str(payload.get("path") or "")
        )
        _verify_hash(path, str(payload.get("hash") or ""), "payload")
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) != payload.get("item_count"):
            raise IngestionError(f"packet payload item count mismatch: {path}")
        for line_number, line in enumerate(lines, start=1):
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise IngestionError(f"invalid packet JSONL at {path}:{line_number}: {exc}") from exc
            if not isinstance(item, dict):
                raise IngestionError(f"packet item must be an object at {path}:{line_number}")
            item_schema_errors = _schema_errors(item, item_schema)
            if item_schema_errors:
                raise IngestionError(
                    f"invalid packet item at {path}:{line_number}: " + "; ".join(item_schema_errors)
                )
            item_id = str(item.get("item_id") or "")
            if not item_id or item_id in packet_items:
                raise IngestionError(f"missing or duplicate packet item ID `{item_id}`")
            packet_items[item_id] = item
            document_id = str(item.get("document_id") or "")
            sentence_id = str(item.get("sentence_id") or "")
            document_ids.add(document_id)
            if sentence_id in sentence_documents and sentence_documents[sentence_id] != document_id:
                raise IngestionError(f"packet sentence `{sentence_id}` belongs to multiple documents")
            sentence_documents[sentence_id] = document_id
            for span_id in item.get("span_ids", []):
                span_id = str(span_id)
                if span_id in span_sentences and span_sentences[span_id] != sentence_id:
                    raise IngestionError(f"packet span `{span_id}` belongs to multiple sentences")
                span_sentences[span_id] = sentence_id
            for unit in item.get("lexical_units", []):
                if isinstance(unit, dict) and unit.get("lexical_unit_id"):
                    lexical_unit_ids.add(str(unit["lexical_unit_id"]))

    prompts: dict[str, dict[str, Any]] = {}
    for prompt in manifest.get("prompts", []):
        if not isinstance(prompt, dict):
            raise IngestionError("packet manifest contains an invalid prompt entry")
        layer = str(prompt.get("task_layer") or "")
        if not layer or layer in prompts:
            raise IngestionError(f"missing or duplicate packet prompt layer `{layer}`")
        prompt_path = _packet_artifact_path(
            case_root, packet_root, str(prompt.get("path") or "")
        )
        _verify_hash(prompt_path, str(prompt.get("hash") or ""), "prompt")
        prompts[layer] = prompt

    return PacketContext(
        manifest=manifest,
        validation_context=SubmissionContext(
            packet_id=str(manifest.get("packet_id") or ""),
            packet_hash=expected_hash,
            case_id=case_id,
            document_ids=frozenset(document_ids),
            sentence_documents=sentence_documents,
            span_sentences=span_sentences,
            item_ids=frozenset(packet_items),
            lexical_unit_ids=frozenset(lexical_unit_ids),
        ),
        items=packet_items,
        prompts=prompts,
    )


def _vocabularies(root: Path) -> dict[str, set[str]]:
    data = read_json_object(root / "config" / "controlled-vocabularies.json")
    return {
        key: {
            str(item["id"])
            for item in values
            if isinstance(item, dict) and item.get("id")
        }
        for key, values in data.items()
        if isinstance(values, list)
    }


def _packet_alignment_errors(
    submission: Mapping[str, Any], packet: PacketContext
) -> list[str]:
    errors: list[str] = []
    items = submission.get("items")
    if not isinstance(items, list):
        return errors
    submitted_ids: set[str] = set()
    layers: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            continue
        prefix = f"$.items[{index}]"
        item_id = str(item.get("item_id") or "")
        layer = str(item.get("task_layer") or "")
        if layer:
            layers.add(layer)
        expected = packet.items.get(item_id)
        if expected is None:
            continue
        submitted_ids.add(item_id)
        for field in (
            "task_layer",
            "case_id",
            "document_id",
            "sentence_id",
            "span_ids",
            "source_language",
            "sentence_source_text",
            "sentence_gloss_en",
            "source_risk_flags",
        ):
            if item.get(field) != expected.get(field):
                errors.append(f"{prefix}.{field}: does not match packet item `{item_id}`")
        expected_units = expected.get("lexical_units", [])
        actual_units = item.get("lexical_units", [])
        if not isinstance(actual_units, list) or len(actual_units) != len(expected_units):
            errors.append(f"{prefix}.lexical_units: must preserve every packet lexical unit")
            continue
        for unit_index, (actual, expected_unit) in enumerate(zip(actual_units, expected_units)):
            if not isinstance(actual, Mapping) or not isinstance(expected_unit, Mapping):
                continue
            for field in (
                "lexical_unit_id",
                "span_id",
                "source_text",
                "gloss_en",
                "char_offset_start",
                "char_offset_end",
            ):
                if actual.get(field) != expected_unit.get(field):
                    errors.append(
                        f"{prefix}.lexical_units[{unit_index}].{field}: does not match packet source"
                    )

    if len(layers) != 1:
        errors.append("$.items: one submission must contain exactly one task layer")
        return errors
    layer = next(iter(layers))
    expected_ids = {
        item_id for item_id, item in packet.items.items() if item.get("task_layer") == layer
    }
    missing = sorted(expected_ids - submitted_ids)
    unexpected = sorted(submitted_ids - expected_ids)
    if missing:
        errors.append("$.items: missing packet item ID(s): " + ", ".join(missing))
    if unexpected:
        errors.append("$.items: item ID(s) belong to another task layer: " + ", ".join(unexpected))

    prompt = packet.prompts.get(layer)
    if prompt is None:
        errors.append(f"$.prompt_id: packet has no prompt for task layer `{layer}`")
    else:
        if submission.get("prompt_id") != prompt.get("id"):
            errors.append("$.prompt_id: does not match the packet task-layer prompt")
        if submission.get("prompt_hash") != prompt.get("hash"):
            errors.append("$.prompt_hash: does not match the packet task-layer prompt")
    return errors


def _metadata_errors(submission: Mapping[str, Any], packet: PacketContext) -> list[str]:
    errors: list[str] = []
    manifest = packet.manifest
    for field in ("sample_id", "sample_version", "source_language", "code_revision"):
        if submission.get(field) != manifest.get(field):
            errors.append(f"$.{field}: does not match the packet manifest")
    run = submission.get("run")
    if isinstance(run, Mapping):
        capabilities = run.get("language_capabilities")
        if isinstance(capabilities, list) and submission.get("source_language") not in capabilities:
            errors.append("$.run.language_capabilities: must include the submission source_language")
    return errors


def _case_vocabulary_errors(
    root: Path, case_id: str, submission: Mapping[str, Any]
) -> list[str]:
    items = submission.get("items")
    if not isinstance(items, list):
        return []
    cmt_items = [
        (index, item)
        for index, item in enumerate(items)
        if isinstance(item, Mapping) and isinstance(item.get("cmt"), Mapping)
    ]
    if not cmt_items:
        return []
    path = root / "cases" / case_id / "config" / "case-clusters.json"
    cluster_data = read_json(path)
    if not isinstance(cluster_data, list):
        raise IngestionError(f"case cluster vocabulary must be an array: {path}")
    valid_clusters = {
        str(item["id"])
        for item in cluster_data
        if isinstance(item, dict) and item.get("id")
    }
    errors: list[str] = []
    for index, item in cmt_items:
        cluster_id = item["cmt"].get("cluster_id")
        if cluster_id not in valid_clusters:
            errors.append(f"$.items[{index}].cmt.cluster_id: unknown cluster ID `{cluster_id}`")
    return errors


def _raw_digest(raw_files: Mapping[str, bytes]) -> str:
    digest = hashlib.sha256()
    for filename in sorted(raw_files):
        digest.update(filename.encode("utf-8"))
        digest.update(b"\0")
        digest.update(raw_files[filename])
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _item_results(envelope: Mapping[str, Any], errors: Sequence[str]) -> list[dict[str, Any]]:
    items = envelope.get("items")
    if not isinstance(items, list):
        return []
    results: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        prefix = f"$.items[{index}]"
        item_errors = [error for error in errors if error.startswith(prefix)]
        results.append(
            {
                "index": index,
                "item_id": item.get("item_id") if isinstance(item, Mapping) else None,
                "status": "invalid" if item_errors else "valid",
                "errors": item_errors,
                "raw_item": item,
            }
        )
    return results


def _markdown_report(report: Mapping[str, Any]) -> str:
    lines = [
        f"# Model Submission Validation: {report['registration_id']}",
        "",
        f"- Status: **{report['status']}**",
        f"- Source format: `{report['source_format']}`",
        f"- Submission ID: `{report.get('submission_id') or 'missing'}`",
        f"- Run ID: `{report.get('run_id') or 'missing'}`",
        f"- Errors: {len(report['errors'])}",
        f"- Items received: {len(report['item_results'])}",
        "",
    ]
    if report["errors"]:
        lines.extend(["## Errors", ""])
        lines.extend(f"- {error}" for error in report["errors"])
        lines.append("")
    lines.extend(["## Item results", ""])
    if report["item_results"]:
        lines.extend(
            f"- `{item.get('item_id') or 'missing'}`: {item['status']}"
            + (f" ({len(item['errors'])} error(s))" if item["errors"] else "")
            for item in report["item_results"]
        )
    else:
        lines.append("- No parseable item rows were received.")
    lines.append("")
    return "\n".join(lines)


def _contains_sensitive_data(raw_files: Mapping[str, bytes]) -> bool:
    return any(SENSITIVE_PATTERN.search(data.decode("utf-8", errors="ignore")) for data in raw_files.values())


def ingest_submission(
    root: Path,
    case_id: str,
    parsed: ParsedSubmission,
) -> dict[str, Any]:
    root = root.resolve()
    case_root = root / "cases" / case_id
    if not case_root.is_dir():
        raise IngestionError(f"unknown case `{case_id}`")
    if _contains_sensitive_data(parsed.raw_files):
        raise IngestionError("refusing to store a submission that appears to contain credentials or account IDs")

    packet = load_packet_context(root, case_id)
    schema = read_json_object(root / "schemas" / "model-reliability" / "submission-schema.json")
    errors = list(parsed.errors)
    errors.extend(
        validate_submission(
            parsed.envelope,
            packet.validation_context,
            schema=schema,
            vocabularies=_vocabularies(root),
        )
    )
    errors.extend(_metadata_errors(parsed.envelope, packet))
    errors.extend(_packet_alignment_errors(parsed.envelope, packet))
    errors.extend(_case_vocabulary_errors(root, case_id, parsed.envelope))

    raw_hash = _raw_digest(parsed.raw_files)
    registration_id = "submission-" + raw_hash.removeprefix("sha256:")[:16]
    register_path = safe_output_path(
        case_root, "quality/model-reliability/submissions/submission-register.json"
    )
    register = read_json_object(register_path) if register_path.exists() else {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "submissions": [],
    }
    entries = register.get("submissions", [])
    if register.get("case_id") != case_id or not isinstance(entries, list):
        raise IngestionError("submission register has an invalid case_id or submissions field")

    existing_registration = next(
        (entry for entry in entries if entry.get("registration_id") == registration_id), None
    )
    if existing_registration:
        if existing_registration.get("raw_hash") != raw_hash:
            raise IngestionError(f"registration hash-prefix collision for `{registration_id}`")
        raw_dir = safe_output_path(
            case_root, f"quality/model-reliability/submissions/raw/{registration_id}"
        )
        for filename, expected_bytes in parsed.raw_files.items():
            raw_path = raw_dir / filename
            if not raw_path.is_file() or raw_path.read_bytes() != expected_bytes:
                raise IngestionError(f"immutable raw registration was altered: {raw_path}")
        report_path = safe_output_path(
            case_root,
            f"quality/model-reliability/normalized/validation-reports/{registration_id}.json",
        )
        if not report_path.exists():
            raise IngestionError(f"existing registration `{registration_id}` has no validation report")
        return read_json_object(report_path)

    submission_id = parsed.envelope.get("submission_id")
    run = parsed.envelope.get("run")
    run_id = run.get("run_id") if isinstance(run, Mapping) else None
    for entry in entries:
        if entry.get("status") != "valid":
            continue
        if submission_id and entry.get("submission_id") == submission_id:
            errors.append(f"$.submission_id: duplicate registered submission ID `{submission_id}`")
        if run_id and entry.get("run_id") == run_id:
            errors.append(f"$.run.run_id: duplicate registered run ID `{run_id}`")

    normalized_path = safe_output_path(
        case_root, "quality/model-reliability/normalized/normalized-runs.json"
    )
    normalized = read_json_object(normalized_path) if normalized_path.exists() else {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "runs": [],
    }
    runs = normalized.get("runs", [])
    if normalized.get("case_id") != case_id or not isinstance(runs, list):
        raise IngestionError("normalized-runs.json has an invalid case_id or runs field")

    aggregate_path = safe_output_path(
        case_root, "quality/model-reliability/normalized/validation-report.json"
    )
    aggregate = read_json_object(aggregate_path) if aggregate_path.exists() else {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "submissions": [],
    }
    summaries = aggregate.get("submissions", [])
    if aggregate.get("case_id") != case_id or not isinstance(summaries, list):
        raise IngestionError("validation-report.json has an invalid case_id or submissions field")

    raw_dir = safe_output_path(
        case_root, f"quality/model-reliability/submissions/raw/{registration_id}"
    )
    report_json_path = safe_output_path(
        case_root,
        f"quality/model-reliability/normalized/validation-reports/{registration_id}.json",
    )
    report_md_path = safe_output_path(
        case_root,
        f"quality/model-reliability/normalized/validation-reports/{registration_id}.md",
    )
    aggregate_md_path = safe_output_path(
        case_root, "quality/model-reliability/normalized/validation-report.md"
    )

    errors = list(dict.fromkeys(errors))
    status = "valid" if not errors else "invalid"
    registered_at = utc_now()
    item_results = _item_results(parsed.envelope, errors)
    report = {
        "schema_version": "1.0.0",
        "registration_id": registration_id,
        "registered_at": registered_at,
        "case_id": case_id,
        "submission_id": submission_id,
        "run_id": run_id,
        "source_format": parsed.source_format,
        "raw_hash": raw_hash,
        "status": status,
        "errors": errors,
        "item_results": item_results,
        "raw_metadata_rows": parsed.raw_metadata_rows,
        "raw_item_rows": parsed.raw_item_rows,
    }

    raw_dir.mkdir(parents=True, exist_ok=False)
    for filename, data in parsed.raw_files.items():
        raw_path = raw_dir / filename
        raw_path.write_bytes(data)
        raw_path.chmod(0o444)

    write_json(report_json_path, report)
    report_md_path.write_text(_markdown_report(report), encoding="utf-8")

    entry = {
        "registration_id": registration_id,
        "registered_at": registered_at,
        "submission_id": submission_id,
        "run_id": run_id,
        "packet_id": parsed.envelope.get("packet_id"),
        "source_format": parsed.source_format,
        "raw_hash": raw_hash,
        "status": status,
        "validation_report": report_json_path.relative_to(case_root).as_posix(),
    }
    entries.append(entry)
    register["submissions"] = entries
    write_json(register_path, register)

    if status == "valid":
        runs.append(
            {
                "registration_id": registration_id,
                "registered_at": registered_at,
                "raw_hash": raw_hash,
                "submission": parsed.envelope,
            }
        )
    normalized["runs"] = runs
    write_json(normalized_path, normalized)

    summaries.append(
        {
            "registration_id": registration_id,
            "submission_id": submission_id,
            "run_id": run_id,
            "status": status,
            "error_count": len(errors),
            "item_count": len(item_results),
            "report": report_json_path.relative_to(case_root).as_posix(),
        }
    )
    aggregate["submissions"] = summaries
    aggregate["latest_registration_id"] = registration_id
    write_json(aggregate_path, aggregate)
    aggregate_md_path.write_text(
        "# Model Submission Validation Summary\n\n"
        + "\n".join(
            f"- `{item['registration_id']}`: **{item['status']}**, "
            f"{item['error_count']} error(s), {item['item_count']} item(s)"
            for item in summaries
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--json", dest="json_path", type=Path)
    source.add_argument("--metadata-csv", type=Path)
    parser.add_argument("--items-csv", type=Path)
    args = parser.parse_args()
    if args.metadata_csv and not args.items_csv:
        parser.error("--items-csv is required with --metadata-csv")
    if args.items_csv and not args.metadata_csv:
        parser.error("--items-csv requires --metadata-csv")
    try:
        if args.json_path:
            parsed = parse_json_submission(args.json_path)
        else:
            contract = read_json_object(
                ROOT / "schemas" / "model-reliability" / "submission-csv-contract.json"
            )
            parsed = parse_csv_submission(args.metadata_csv, args.items_csv, contract)
        report = ingest_submission(ROOT, args.case_id, parsed)
    except (IngestionError, OSError) as exc:
        parser.error(str(exc))
    print(
        f"{args.case_id}: {report['registration_id']} is {report['status']} "
        f"with {len(report['errors'])} error(s)"
    )
    return 0 if report["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
