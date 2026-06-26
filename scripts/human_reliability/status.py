#!/usr/bin/env python3
"""Validate human-reliability artifacts and derive honest execution status."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

try:
    from scripts.human_reliability.boundaries import protect_accepted_artifacts, safe_output_path
except ModuleNotFoundError:
    try:
        from human_reliability.boundaries import protect_accepted_artifacts, safe_output_path
    except ModuleNotFoundError:
        from boundaries import protect_accepted_artifacts, safe_output_path  # type: ignore


ROOT = Path(__file__).resolve().parents[2]
STATUS_GENERATOR = "scripts/human_reliability/status.py"
COMPARISON_ARTIFACTS = {
    "human-agreement.json": "agreement-results-schema.json",
    "reference-comparison.json": "reference-comparison-schema.json",
    "disagreement-log.json": "disagreement-log-schema.json",
    "adjudication-queue.json": "adjudication-queue-schema.json",
    "human-reliability-report.json": "human-reliability-report-schema.json",
}
CASE_ARTIFACT_SCHEMAS = {
    "ingestion-status.json": "ingestion-status-schema.json",
    "submissions/submission-register.json": "submission-register-schema.json",
    "normalized/normalized-coder-runs.json": "normalized-coder-runs-schema.json",
    "adjudication/decisions/adjudication-register.json": (
        "adjudication-register-schema.json"
    ),
    "codebook/codebook-revision-notes.json": "codebook-revision-notes-schema.json",
    "codebook/recommendation-decisions.json": (
        "codebook-recommendation-decisions-schema.json"
    ),
}


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _cohort_hash(cohort: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(cohort))
    approval = payload.get("approval")
    if isinstance(approval, dict):
        approval["manifest_sha256"] = None
    return _sha256(_canonical_json(payload))


def _read(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: unable to read JSON: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{path}: expected a JSON object")
        return None
    return value


def _schema(root: Path, name: str, errors: list[str]) -> dict[str, Any] | None:
    return _read(root / "schemas" / "human-reliability" / name, errors)


def _validate_schema(
    path: Path,
    value: Mapping[str, Any],
    schema: Mapping[str, Any],
    errors: list[str],
) -> None:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for error in sorted(validator.iter_errors(value), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        errors.append(f"{path}: {location}: {error.message}")


def _submission(record: Mapping[str, Any]) -> Mapping[str, Any]:
    value = record.get("submission")
    return value if isinstance(value, Mapping) else record


def _cohort_key(value: Mapping[str, Any]) -> tuple[str, str]:
    return (str(value.get("cohort_id") or ""), str(value.get("cohort_version") or ""))


def _safe_case_path(case_root: Path, relative: str, errors: list[str]) -> Path | None:
    path = (case_root / relative).resolve()
    try:
        path.relative_to(case_root.resolve())
    except ValueError:
        errors.append(f"{path}: artifact path escapes the case root")
        return None
    return path


def _validate_packet_manifest(
    root: Path,
    case_root: Path,
    path: Path,
    manifest: Mapping[str, Any],
    errors: list[str],
) -> None:
    expected = dict(manifest)
    expected_hash = expected.pop("packet_hash", None)
    if expected_hash != _sha256(_canonical_json(expected)):
        errors.append(f"{path}: packet_hash does not match manifest content")
    for entry in manifest.get("payloads", []):
        if not isinstance(entry, Mapping):
            continue
        artifact = _safe_case_path(case_root, str(entry.get("path") or ""), errors)
        if artifact is None:
            continue
        if not artifact.is_file():
            errors.append(f"{artifact}: packet payload is missing")
            continue
        if _sha256(artifact.read_bytes()) != entry.get("hash"):
            errors.append(f"{artifact}: packet payload hash mismatch")
    generator = manifest.get("generator")
    if isinstance(generator, Mapping):
        script = root / str(generator.get("script") or "")
        if script.is_file() and _sha256(script.read_bytes()) != generator.get(
            "script_hash"
        ):
            errors.append(f"{path}: packet generator script hash is stale")


def _read_artifact(
    root: Path,
    path: Path,
    schema_name: str,
    case_id: str,
    errors: list[str],
) -> dict[str, Any] | None:
    value = _read(path, errors)
    if value is None:
        return None
    schema = _schema(root, schema_name, errors)
    if schema is not None:
        _validate_schema(path, value, schema, errors)
    if value.get("case_id") != case_id:
        errors.append(f"{path}: case_id does not match `{case_id}`")
    return value


def _register_reports(
    root: Path,
    case_root: Path,
    report_root: Path,
    schema_name: str,
    case_id: str,
    errors: list[str],
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    if not report_root.exists():
        return reports
    for path in sorted(report_root.glob("*.json")):
        report = _read_artifact(root, path, schema_name, case_id, errors)
        if report is not None:
            reports.append(report)
            try:
                path.relative_to(case_root)
            except ValueError:
                errors.append(f"{path}: validation report escapes the case root")
    return reports


def _cohort_summary(
    cohort: Mapping[str, Any],
    *,
    ingestion_state: str,
    valid_coders: list[str],
    valid_submission_count: int,
    invalid_submission_count: int,
    comparison: Mapping[str, Mapping[str, Any]],
    adjudication_results: Mapping[str, Any] | None,
    correction_candidates: Mapping[str, Any] | None,
    report: Mapping[str, Any] | None,
    errors: list[str],
) -> dict[str, Any]:
    queue = comparison.get("adjudication-queue.json")
    queue_count = 0
    if queue is not None:
        summary = queue.get("summary", {})
        if isinstance(summary, Mapping):
            queue_count = int(summary.get("queue_count") or 0)
    adjudication_state = "not_started"
    unresolved_count = 0
    if adjudication_results is not None:
        summary = adjudication_results.get("summary", {})
        if isinstance(summary, Mapping):
            adjudication_state = str(summary.get("state") or "not_started")
            unresolved_count = int(summary.get("unresolved_count") or 0)
    complete_core = all(
        name in comparison
        for name in (
            "human-agreement.json",
            "reference-comparison.json",
            "disagreement-log.json",
            "adjudication-queue.json",
        )
    )
    report_present = report is not None
    codebook_needed = True
    state = "designed"
    if errors or invalid_submission_count:
        state = "invalid"
    elif ingestion_state == "partial":
        state = "partial"
    elif ingestion_state == "invalid":
        state = "invalid"
    elif ingestion_state == "complete" and not complete_core:
        state = "partial"
    elif complete_core and queue_count > 0 and adjudication_results is None:
        state = "awaiting-adjudication"
    elif adjudication_results is not None and adjudication_state != "complete":
        state = "awaiting-adjudication"
    elif complete_core and report_present and codebook_needed:
        state = "complete"
    elif ingestion_state == "absent":
        state = "designed"
    else:
        state = "partial"
    return {
        "cohort_id": str(cohort.get("cohort_id") or ""),
        "cohort_version": str(cohort.get("cohort_version") or ""),
        "source_language": str(cohort.get("source_language") or ""),
        "task_layer": str(cohort.get("task_layer") or ""),
        "state": state,
        "ingestion_state": ingestion_state,
        "adjudication_state": adjudication_state,
        "valid_primary_coders": valid_coders,
        "valid_submission_count": valid_submission_count,
        "invalid_submission_count": invalid_submission_count,
        "queue_count": queue_count,
        "unresolved_adjudication_count": unresolved_count,
        "correction_candidate_count": len(
            correction_candidates.get("candidates", [])
        )
        if isinstance(correction_candidates, Mapping)
        else 0,
    }


def evaluate_case(
    root: Path,
    case_id: str,
    *,
    validate_existing_status: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    case_root = root / "cases" / case_id
    human_root = case_root / "quality" / "human-reliability"
    errors: list[str] = []
    warnings: list[str] = []
    if not case_root.is_dir():
        errors.append(f"unknown case `{case_id}`")

    present_files = (
        sorted(
            path
            for path in human_root.rglob("*")
            if path.is_file() and path.name != "status.json"
        )
        if human_root.exists()
        else []
    )
    artifacts: dict[str, Mapping[str, Any]] = {}
    for relative, schema_name in CASE_ARTIFACT_SCHEMAS.items():
        if relative == "status.json" and not validate_existing_status:
            continue
        path = human_root / relative
        if not path.exists():
            continue
        value = _read_artifact(root, path, schema_name, case_id, errors)
        if value is not None:
            artifacts[relative] = value

    status_schema = _schema(root, "status-schema.json", errors)
    if validate_existing_status:
        status_path = human_root / "status.json"
        if status_path.exists():
            status_value = _read(status_path, errors)
            if status_value is not None and status_schema is not None:
                _validate_schema(status_path, status_value, status_schema, errors)

    cohorts: dict[tuple[str, str], Mapping[str, Any]] = {}
    for path in sorted((human_root / "cohorts").glob("*.json")):
        cohort = _read_artifact(
            root, path, "cohort-manifest-schema.json", case_id, errors
        )
        if cohort is None:
            continue
        key = _cohort_key(cohort)
        if key in cohorts:
            errors.append(f"{path}: duplicate cohort identity `{key[0]}` `{key[1]}`")
        cohorts[key] = cohort
        try:
            if _cohort_hash(cohort) != cohort.get("approval", {}).get(
                "manifest_sha256"
            ):
                errors.append(f"{path}: approval.manifest_sha256 is stale")
        except Exception as exc:
            errors.append(f"{path}: unable to verify cohort approval hash: {exc}")
        packet_path = _safe_case_path(
            case_root, str(cohort.get("packet_manifest") or ""), errors
        )
        if packet_path is None or not packet_path.is_file():
            errors.append(f"{path}: cohort packet manifest is missing")
            continue
        packet = _read_artifact(
            root, packet_path, "packet-manifest-schema.json", case_id, errors
        )
        if packet is None:
            continue
        _validate_packet_manifest(root, case_root, packet_path, packet, errors)
        for field in (
            "packet_id",
            "sample_id",
            "sample_version",
            "source_language",
            "task_layer",
        ):
            if cohort.get(field) != packet.get(field):
                errors.append(f"{path}: cohort `{field}` differs from packet")

    submission_reports = _register_reports(
        root,
        case_root,
        human_root / "normalized" / "validation-reports",
        "ingestion-report-schema.json",
        case_id,
        errors,
    )
    report_ids = {
        str(report.get("registration_id"))
        for report in submission_reports
        if report.get("registration_id")
    }
    register = artifacts.get("submissions/submission-register.json", {})
    submissions = register.get("submissions", []) if isinstance(register, Mapping) else []
    if not isinstance(submissions, list):
        submissions = []
    registrations = {
        str(entry.get("registration_id")): entry
        for entry in submissions
        if isinstance(entry, Mapping) and entry.get("registration_id")
    }
    invalid_submission_count = sum(
        entry.get("status") == "invalid"
        for entry in submissions
        if isinstance(entry, Mapping)
    )
    for registration_id, entry in registrations.items():
        report_path = _safe_case_path(
            case_root, str(entry.get("validation_report") or ""), errors
        )
        if registration_id not in report_ids or report_path is None or not report_path.is_file():
            errors.append(
                f"{human_root}: registration `{registration_id}` has no "
                "matching validation report"
            )

    normalized = artifacts.get("normalized/normalized-coder-runs.json", {})
    runs = normalized.get("runs", []) if isinstance(normalized, Mapping) else []
    if not isinstance(runs, list):
        runs = []
    valid_registration_ids = {
        registration_id
        for registration_id, entry in registrations.items()
        if entry.get("status") == "valid"
    }
    normalized_registration_ids: set[str] = set()
    runs_by_cohort: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for run in runs:
        if not isinstance(run, Mapping):
            continue
        key = _cohort_key(run)
        runs_by_cohort.setdefault(key, []).append(run)
        registration_id = run.get("registration_id")
        if isinstance(registration_id, str):
            normalized_registration_ids.add(registration_id)
            if registration_id not in valid_registration_ids:
                errors.append(
                    f"{human_root}: normalized run `{registration_id}` is not "
                    "backed by a valid registration"
                )
        cohort = cohorts.get(key)
        if cohort is not None:
            submission = _submission(run)
            packet_path = _safe_case_path(
                case_root, str(cohort.get("packet_manifest") or ""), errors
            )
            packet = _read(packet_path, errors) if packet_path and packet_path.is_file() else None
            if packet is not None:
                if submission.get("packet_id") != packet.get("packet_id"):
                    errors.append(
                        f"{human_root}: normalized human run has stale packet_id"
                    )
                if submission.get("packet_hash") != packet.get("packet_hash"):
                    errors.append(
                        f"{human_root}: normalized human run has stale packet_hash"
                    )
    if normalized_registration_ids != valid_registration_ids:
        errors.append(
            f"{human_root}: normalized runs do not match valid registrations"
        )

    ingestion = artifacts.get("ingestion-status.json", {})
    ingestion_by_cohort = {
        _cohort_key(item): item
        for item in ingestion.get("cohorts", [])
        if isinstance(item, Mapping)
    } if isinstance(ingestion, Mapping) else {}

    comparison_by_cohort: dict[tuple[str, str], dict[str, Mapping[str, Any]]] = {}
    comparison_root = human_root / "comparisons"
    if comparison_root.exists():
        for cohort_dir in sorted(path for path in comparison_root.iterdir() if path.is_dir()):
            for filename, schema_name in COMPARISON_ARTIFACTS.items():
                path = cohort_dir / filename
                if not path.exists():
                    continue
                artifact = _read_artifact(root, path, schema_name, case_id, errors)
                if artifact is None:
                    continue
                key = _cohort_key(artifact)
                comparison_by_cohort.setdefault(key, {})[filename] = artifact

    adjudication_reports = _register_reports(
        root,
        case_root,
        human_root / "adjudication" / "decisions" / "validation-reports",
        "adjudication-ingestion-report-schema.json",
        case_id,
        errors,
    )
    adjudication_report_ids = {
        str(report.get("registration_id"))
        for report in adjudication_reports
        if report.get("registration_id")
    }
    adjudication_register = artifacts.get(
        "adjudication/decisions/adjudication-register.json", {}
    )
    adjudication_submissions = (
        adjudication_register.get("submissions", [])
        if isinstance(adjudication_register, Mapping)
        else []
    )
    if not isinstance(adjudication_submissions, list):
        adjudication_submissions = []
    invalid_adjudication_count = sum(
        entry.get("status") == "invalid"
        for entry in adjudication_submissions
        if isinstance(entry, Mapping)
    )
    valid_adjudication_ids = {
        str(entry.get("registration_id"))
        for entry in adjudication_submissions
        if isinstance(entry, Mapping) and entry.get("status") == "valid"
    }
    for entry in adjudication_submissions:
        if not isinstance(entry, Mapping):
            continue
        registration_id = str(entry.get("registration_id") or "")
        report_path = _safe_case_path(
            case_root, str(entry.get("validation_report") or ""), errors
        )
        if (
            registration_id
            and (
                registration_id not in adjudication_report_ids
                or report_path is None
                or not report_path.is_file()
            )
        ):
            errors.append(
                f"{human_root}: adjudication registration `{registration_id}` "
                "has no matching validation report"
            )

    adjudication_results: dict[tuple[str, str], Mapping[str, Any]] = {}
    for path in sorted((human_root / "adjudication" / "results").glob("*/adjudication-results.json")):
        result = _read_artifact(
            root, path, "adjudication-results-schema.json", case_id, errors
        )
        if result is None:
            continue
        key = _cohort_key(result)
        adjudication_results[key] = result
        if result.get("registration_id") not in valid_adjudication_ids:
            errors.append(f"{path}: adjudication result has no valid registration")
        summary = result.get("summary", {})
        decisions = result.get("decisions", [])
        if isinstance(summary, Mapping) and isinstance(decisions, list):
            reconciliation = {
                "decision_count": len(decisions),
                "accepted_count": sum(
                    item.get("decision", {}).get("status") == "accepted"
                    for item in decisions
                    if isinstance(item, Mapping)
                ),
                "rejected_count": sum(
                    item.get("decision", {}).get("status") == "rejected"
                    for item in decisions
                    if isinstance(item, Mapping)
                ),
                "deferred_count": sum(
                    item.get("decision", {}).get("status") == "deferred"
                    for item in decisions
                    if isinstance(item, Mapping)
                ),
                "unresolved_count": sum(
                    item.get("decision", {}).get("status") == "unresolved"
                    for item in decisions
                    if isinstance(item, Mapping)
                ),
            }
            for field, expected in reconciliation.items():
                if summary.get(field) != expected:
                    errors.append(
                        f"{path}: adjudication summary `{field}` does not reconcile"
                    )

    correction_candidates: dict[tuple[str, str], Mapping[str, Any]] = {}
    for path in sorted((human_root / "correction-candidates").glob("*/correction-candidates.json")):
        candidates = _read_artifact(
            root, path, "correction-candidates-schema.json", case_id, errors
        )
        if candidates is not None:
            correction_candidates[_cohort_key(candidates)] = candidates
            if candidates.get("authority", {}).get("promotion_permitted") is not False:
                errors.append(f"{path}: correction candidates permit direct promotion")

    reports: dict[tuple[str, str], Mapping[str, Any]] = {}
    for key in set(cohorts) | set(comparison_by_cohort):
        path = (
            comparison_root
            / f"{key[0]}-{key[1]}"
            / "human-reliability-report.json"
        )
        if path.exists():
            report = _read_artifact(
                root, path, "human-reliability-report-schema.json", case_id, errors
            )
            if report is not None:
                reports[key] = report

    codebook_notes = artifacts.get("codebook/codebook-revision-notes.json")
    if codebook_notes is not None:
        recommendations = codebook_notes.get("recommendations", [])
        if not isinstance(recommendations, list):
            recommendations = []
        summary = codebook_notes.get("summary", {})
        if isinstance(summary, Mapping):
            reconciliation = {
                "recommendation_count": len(recommendations),
                "proposed_count": sum(
                    item.get("disposition") == "proposed"
                    for item in recommendations
                    if isinstance(item, Mapping)
                ),
                "accepted_count": sum(
                    item.get("disposition") == "accepted"
                    for item in recommendations
                    if isinstance(item, Mapping)
                ),
                "rejected_count": sum(
                    item.get("disposition") == "rejected"
                    for item in recommendations
                    if isinstance(item, Mapping)
                ),
                "deferred_count": sum(
                    item.get("disposition") == "deferred"
                    for item in recommendations
                    if isinstance(item, Mapping)
                ),
            }
            for field, expected in reconciliation.items():
                if summary.get(field) != expected:
                    errors.append(f"{human_root}: codebook summary `{field}` mismatch")

    cohort_records: list[dict[str, Any]] = []
    for key, cohort in sorted(cohorts.items()):
        status = ingestion_by_cohort.get(key, {})
        comparison = comparison_by_cohort.get(key, {})
        valid_coders = sorted(str(item) for item in status.get("valid_primary_coders", []))
        record_errors = [
            error
            for error in errors
            if key[0] in error or str(human_root) in error
        ]
        cohort_records.append(
            _cohort_summary(
                cohort,
                ingestion_state=str(status.get("state") or "absent"),
                valid_coders=valid_coders,
                valid_submission_count=int(status.get("valid_submission_count") or 0),
                invalid_submission_count=int(status.get("invalid_submission_count") or 0),
                comparison=comparison,
                adjudication_results=adjudication_results.get(key),
                correction_candidates=correction_candidates.get(key),
                report=reports.get(key),
                errors=record_errors,
            )
        )

    started = bool(
        submissions
        or runs
        or comparison_by_cohort
        or adjudication_submissions
        or adjudication_results
    )
    if errors or invalid_submission_count or invalid_adjudication_count:
        state = "invalid"
        if invalid_submission_count:
            warnings.append(f"{invalid_submission_count} invalid human submission(s) require review.")
        if invalid_adjudication_count:
            warnings.append(
                f"{invalid_adjudication_count} invalid adjudication submission(s) require review."
            )
    elif any(record["state"] == "awaiting-adjudication" for record in cohort_records):
        state = "awaiting-adjudication"
        warnings.append("Human reliability has queued disagreements awaiting adjudication.")
    elif cohort_records and all(record["state"] == "complete" for record in cohort_records):
        state = "complete"
    elif any(record["state"] == "partial" for record in cohort_records) or started:
        state = "partial"
        warnings.append(
            "Human reliability execution has started, but required artifacts are incomplete."
        )
    elif cohort_records:
        state = "designed"
        warnings.append(
            "Human reliability cohorts are designed; required primary coder submissions are not complete."
        )
    elif present_files:
        state = "partial"
        warnings.append("Human reliability artifacts are present but no approved cohort was found.")
    else:
        state = "absent"
        warnings.append("Human reliability has not been designed for this case.")

    return {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "generator": STATUS_GENERATOR,
        "state": state,
        "valid": not errors and not invalid_submission_count and not invalid_adjudication_count,
        "counts": {
            "cohorts": len(cohort_records),
            "submissions": len(submissions),
            "valid_runs": len(runs),
            "invalid_submissions": invalid_submission_count,
            "adjudication_submissions": len(adjudication_submissions),
            "invalid_adjudications": invalid_adjudication_count,
            "unresolved_adjudications": sum(
                record["unresolved_adjudication_count"] for record in cohort_records
            ),
            "correction_candidates": sum(
                record["correction_candidate_count"] for record in cohort_records
            ),
        },
        "artifacts": {
            "cohorts": bool(cohort_records),
            "packets": any(
                "packet_manifest" in str(cohort.get("packet_manifest") or "")
                or cohort.get("packet_manifest")
                for cohort in cohorts.values()
            ),
            "ingestion_status": "ingestion-status.json" in artifacts,
            "agreement": any("human-agreement.json" in item for item in comparison_by_cohort.values()),
            "reference_comparison": any(
                "reference-comparison.json" in item for item in comparison_by_cohort.values()
            ),
            "disagreements": any("disagreement-log.json" in item for item in comparison_by_cohort.values()),
            "adjudication_queue": any(
                "adjudication-queue.json" in item for item in comparison_by_cohort.values()
            ),
            "adjudication_results": bool(adjudication_results),
            "correction_candidates": bool(correction_candidates),
            "report": bool(reports),
            "codebook_notes": codebook_notes is not None,
        },
        "cohorts": cohort_records,
        "warnings": warnings,
        "errors": errors,
    }


@protect_accepted_artifacts
def write_case_status(root: Path, case_id: str) -> dict[str, Any]:
    status = evaluate_case(root, case_id, validate_existing_status=False)
    case_root = root.resolve() / "cases" / case_id
    path = safe_output_path(case_root, "quality/human-reliability/status.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = (
        write_case_status(args.root, args.case_id)
        if args.write
        else evaluate_case(args.root, args.case_id)
    )
    print(
        f"{args.case_id}: human reliability is `{result['state']}` "
        f"with {len(result['errors'])} error(s)"
    )
    for warning in result["warnings"]:
        print(f"WARNING: {warning}")
    return 1 if result["state"] == "invalid" else 0


if __name__ == "__main__":
    raise SystemExit(main())
