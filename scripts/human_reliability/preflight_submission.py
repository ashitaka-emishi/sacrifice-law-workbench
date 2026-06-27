#!/usr/bin/env python3
"""Preflight a returned human-coder submission without writing artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

try:
    from scripts.human_reliability.ingest_submission import (
        IngestionError,
        ParsedSubmission,
        _comment_errors,
        _contains_sensitive_data,
        _raw_digest,
        _row_results,
        load_cohort_context,
        parse_csv_submission,
        parse_json_submission,
        read_json_object,
    )
    from scripts.human_reliability.submission_contract import validate_submission
except ModuleNotFoundError:
    from ingest_submission import (  # type: ignore
        IngestionError,
        ParsedSubmission,
        _comment_errors,
        _contains_sensitive_data,
        _raw_digest,
        _row_results,
        load_cohort_context,
        parse_csv_submission,
        parse_json_submission,
        read_json_object,
    )
    from submission_contract import validate_submission  # type: ignore


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_FIELDS = frozenset(
    {
        "accepted_decision",
        "accepted_label",
        "accepted_labels",
        "adjudicated_decision",
        "adjudication",
        "adjudication_status",
        "answer_key",
        "claim_impact",
        "consensus_summary",
        "design_roles",
        "model_output",
        "model_outputs",
        "reference_decision",
        "review_status",
        "sample_role",
        "sample_roles",
        "support_score",
    }
)
REQUIRED_DECLARATION_FIELDS = (
    "training_completed_at",
    "calibration_completed_at",
    "completed_at",
)


def forbidden_field_errors(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).lower() in FORBIDDEN_FIELDS:
                errors.append(f"{child_path}: forbidden leakage/internal field `{key}`")
            errors.extend(forbidden_field_errors(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(forbidden_field_errors(child, f"{path}[{index}]"))
    return errors


def declaration_errors(submission: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_DECLARATION_FIELDS:
        if not submission.get(field):
            errors.append(f"$.{field}: required declaration timestamp is missing")
    return errors


def preflight_submission(
    root: Path,
    case_id: str,
    cohort_path: Path,
    parsed: ParsedSubmission,
) -> dict[str, Any]:
    """Return a validation report without modifying repository artifacts."""

    root = root.resolve()
    case_root = root / "cases" / case_id
    if not case_root.is_dir():
        raise IngestionError(f"unknown case `{case_id}`")
    if _contains_sensitive_data(parsed.raw_files):
        raise IngestionError("refusing to inspect a submission that appears to contain credentials")

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
    errors.extend(forbidden_field_errors(parsed.envelope))
    errors.extend(declaration_errors(parsed.envelope))
    errors = list(dict.fromkeys(errors))
    status = "valid" if not errors else "invalid"
    raw_hash = _raw_digest(parsed.raw_files)
    report_id = "human-preflight-" + raw_hash.removeprefix("sha256:")[:16]

    return {
        "schema_version": "1.0.0",
        "preflight_id": report_id,
        "case_id": case_id,
        "cohort_id": parsed.envelope.get("cohort_id"),
        "cohort_version": parsed.envelope.get("cohort_version"),
        "submission_id": parsed.envelope.get("submission_id"),
        "coder_id": parsed.envelope.get("coder_id"),
        "packet_id": parsed.envelope.get("packet_id"),
        "source_format": parsed.source_format,
        "raw_hash": raw_hash,
        "status": status,
        "errors": errors,
        "row_results": _row_results(parsed, errors),
        "raw_rows": parsed.raw_rows,
        "writes_artifacts": False,
    }


def print_text_report(report: Mapping[str, Any]) -> None:
    print(f"{report['case_id']}: {report['preflight_id']} is {report['status']}")
    print(f"Source format: {report['source_format']}")
    print(f"Submission ID: {report.get('submission_id') or 'missing'}")
    print(f"Coder ID: {report.get('coder_id') or 'missing'}")
    print(f"Rows received: {len(report['raw_rows'])}")
    if report["errors"]:
        print("Errors:")
        for error in report["errors"]:
            print(f"- {error}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--json-output", action="store_true", help="Emit machine-readable JSON")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--json", dest="json_path", type=Path)
    source.add_argument("--csv", dest="csv_path", type=Path)
    args = parser.parse_args()

    try:
        if args.json_path:
            parsed = parse_json_submission(args.json_path)
        else:
            contract = read_json_object(
                ROOT / "schemas" / "human-reliability" / "submission-csv-contract.json"
            )
            parsed = parse_csv_submission(args.csv_path, contract)
        report = preflight_submission(ROOT, args.case_id, args.cohort, parsed)
    except (IngestionError, OSError) as exc:
        parser.error(str(exc))

    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print_text_report(report)
    return 0 if report["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
