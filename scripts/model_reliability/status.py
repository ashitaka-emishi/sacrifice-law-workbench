#!/usr/bin/env python3
"""Validate model-reliability artifacts and derive honest execution status."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator, FormatChecker

try:
    from scripts.model_reliability.boundaries import safe_output_path
    from scripts.model_reliability.generate_packets import stable_source_hash
except ModuleNotFoundError:
    try:
        from model_reliability.boundaries import safe_output_path
        from model_reliability.generate_packets import stable_source_hash
    except ModuleNotFoundError:
        from boundaries import safe_output_path  # type: ignore
        from generate_packets import stable_source_hash  # type: ignore

ROOT = Path(__file__).resolve().parents[2]
STATUS_GENERATOR = "scripts/model_reliability/status.py"
ARTIFACT_SCHEMAS = {
    "status.json": "status-schema.json",
    "sample/sample-manifest.json": "sample-manifest-schema.json",
    "packets/packet-manifest.json": "packet-manifest-schema.json",
    "submissions/submission-register.json": "submission-register-schema.json",
    "normalized/normalized-runs.json": "normalized-runs-schema.json",
    "comparisons/agreement-results.json": "agreement-results-schema.json",
    "comparisons/disagreement-log.json": "disagreement-log-schema.json",
    "review-queue/model-review-queue.json": "review-queue-schema.json",
    "comparisons/consensus-report.json": "consensus-report-schema.json",
    "codebook/codebook-revision-notes.json": "codebook-revision-notes-schema.json",
    "codebook/recommendation-decisions.json": "codebook-recommendation-decisions-schema.json",
    "completion/completion-checklist.json": "completion-checklist-schema.json",
}
COMPLETE_ARTIFACTS = (
    "comparisons/agreement-results.json",
    "comparisons/disagreement-log.json",
    "review-queue/model-review-queue.json",
    "comparisons/consensus-report.json",
    "comparisons/consensus-report.md",
    "codebook/codebook-revision-notes.json",
    "codebook/codebook-revision-notes.md",
)


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


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


def _schema(
    root: Path, name: str, errors: list[str]
) -> dict[str, Any] | None:
    return _read(root / "schemas" / "model-reliability" / name, errors)


def _validate_schema(
    path: Path,
    value: Mapping[str, Any],
    schema: Mapping[str, Any],
    errors: list[str],
) -> None:
    validator = Draft202012Validator(
        schema, format_checker=FormatChecker()
    )
    for error in sorted(validator.iter_errors(value), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        errors.append(f"{path}: {location}: {error.message}")


def _submission(record: Mapping[str, Any]) -> Mapping[str, Any]:
    value = record.get("submission")
    return value if isinstance(value, Mapping) else record


def _run_id(record: Mapping[str, Any]) -> str | None:
    submission = _submission(record)
    run = submission.get("run")
    value = run.get("run_id") if isinstance(run, Mapping) else submission.get("run_id")
    return value if isinstance(value, str) and value else None


def _validation_reports(
    root: Path,
    model_root: Path,
    case_id: str,
    errors: list[str],
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    schema = _schema(root, "ingestion-report-schema.json", errors)
    for path in sorted(
        (model_root / "normalized" / "validation-reports").glob("*.json")
    ):
        report = _read(path, errors)
        if report is None:
            continue
        if schema is not None:
            _validate_schema(path, report, schema, errors)
        if report.get("case_id") != case_id:
            errors.append(f"{path}: case_id does not match `{case_id}`")
        reports.append(report)
    return reports


def _validate_packet(
    root: Path,
    case_id: str,
    manifest: Mapping[str, Any],
    errors: list[str],
) -> None:
    case_root = root / "cases" / case_id
    expected_manifest = dict(manifest)
    expected_hash = expected_manifest.pop("packet_hash", None)
    if expected_hash != _sha256(_canonical_json(expected_manifest)):
        errors.append(
            f"{case_root}: packet manifest hash does not match manifest content"
        )
    item_schema = _schema(root, "packet-item-schema.json", errors)
    seen_items: set[str] = set()
    for section in ("prompts", "source_inputs", "payloads"):
        entries = manifest.get(section, [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            relative = Path(str(entry.get("path", "")))
            path = (
                root / relative
                if relative.parts and relative.parts[0] in {"cases", "config", "scripts"}
                else case_root / relative
            ).resolve()
            allowed_roots = (root.resolve(), case_root.resolve())
            if not any(path == allowed or allowed in path.parents for allowed in allowed_roots):
                errors.append(f"{path}: packet artifact path escapes repository")
                continue
            if not path.is_file():
                errors.append(f"{path}: packet artifact is missing")
                continue
            actual_hash = (
                stable_source_hash(path)
                if section == "source_inputs"
                else _sha256(path.read_bytes())
            )
            if actual_hash != entry.get("hash"):
                errors.append(f"{path}: packet artifact hash mismatch")
            if section != "payloads":
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
            if len(lines) != entry.get("item_count"):
                errors.append(f"{path}: packet item count mismatch")
            for line_number, line in enumerate(lines, start=1):
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append(f"{path}:{line_number}: invalid JSON: {exc}")
                    continue
                if not isinstance(item, dict):
                    errors.append(f"{path}:{line_number}: packet item is not an object")
                    continue
                if item_schema is not None:
                    _validate_schema(path, item, item_schema, errors)
                item_id = item.get("item_id")
                if not isinstance(item_id, str) or not item_id:
                    errors.append(f"{path}:{line_number}: packet item has no item_id")
                elif item_id in seen_items:
                    errors.append(f"{path}:{line_number}: duplicate item_id `{item_id}`")
                else:
                    seen_items.add(item_id)


def _cross_validate(
    case_id: str,
    model_root: Path,
    artifacts: Mapping[str, Mapping[str, Any]],
    reports: Iterable[Mapping[str, Any]],
    errors: list[str],
) -> tuple[int, int]:
    manifest = artifacts.get("packets/packet-manifest.json")
    register = artifacts.get("submissions/submission-register.json")
    normalized = artifacts.get("normalized/normalized-runs.json")
    submissions = (
        register.get("submissions", [])
        if isinstance(register, Mapping)
        else []
    )
    runs = normalized.get("runs", []) if isinstance(normalized, Mapping) else []
    if not isinstance(submissions, list):
        submissions = []
    if not isinstance(runs, list):
        runs = []

    registrations = {
        str(entry.get("registration_id")): entry
        for entry in submissions
        if isinstance(entry, Mapping) and entry.get("registration_id")
    }
    report_ids = {
        str(report.get("registration_id"))
        for report in reports
        if report.get("registration_id")
    }
    for registration_id, entry in registrations.items():
        report_path = model_root.parents[1] / str(
            entry.get("validation_report", "")
        )
        if registration_id not in report_ids or not report_path.is_file():
            errors.append(
                f"{model_root}: registration `{registration_id}` has no "
                "matching validation report"
            )

    run_ids: list[str] = []
    normalized_registrations: set[str] = set()
    for record in runs:
        if not isinstance(record, Mapping):
            continue
        run_id = _run_id(record)
        if run_id is None:
            errors.append(f"{model_root}: normalized run has no run_id")
            continue
        run_ids.append(run_id)
        registration_id = record.get("registration_id")
        if isinstance(registration_id, str):
            normalized_registrations.add(registration_id)
            entry = registrations.get(registration_id)
            if entry is None or entry.get("status") != "valid":
                errors.append(
                    f"{model_root}: normalized run `{run_id}` is not backed by "
                    "a valid registration"
                )
        submission = _submission(record)
        if manifest is not None:
            if submission.get("packet_id") != manifest.get("packet_id"):
                errors.append(
                    f"{model_root}: normalized run `{run_id}` has stale packet_id"
                )
            if submission.get("packet_hash") != manifest.get("packet_hash"):
                errors.append(
                    f"{model_root}: normalized run `{run_id}` has stale packet_hash"
                )
    if len(run_ids) != len(set(run_ids)):
        errors.append(f"{model_root}: normalized runs contain duplicate run IDs")
    valid_registrations = {
        registration_id
        for registration_id, entry in registrations.items()
        if entry.get("status") == "valid"
    }
    if normalized_registrations != valid_registrations:
        errors.append(
            f"{model_root}: normalized runs do not match valid registrations"
        )

    downstream = (
        "comparisons/agreement-results.json",
        "comparisons/disagreement-log.json",
        "review-queue/model-review-queue.json",
        "comparisons/consensus-report.json",
        "codebook/codebook-revision-notes.json",
        "completion/completion-checklist.json",
    )
    for relative in downstream:
        artifact = artifacts.get(relative)
        if artifact is not None and sorted(artifact.get("run_ids", [])) != sorted(
            run_ids
        ):
            errors.append(f"{model_root / relative}: run_ids do not match normalized runs")

    disagreement = artifacts.get("comparisons/disagreement-log.json")
    queue = artifacts.get("review-queue/model-review-queue.json")
    if disagreement is not None and queue is not None:
        disagreement_ids = [
            item.get("disagreement_id")
            for item in disagreement.get("disagreements", [])
            if isinstance(item, Mapping)
        ]
        queue_ids = [
            item.get("disagreement_id")
            for item in queue.get("entries", [])
            if isinstance(item, Mapping)
        ]
        if sorted(disagreement_ids) != sorted(queue_ids):
            errors.append(
                f"{model_root}: review queue does not cover classified disagreements"
            )

    agreement = artifacts.get("comparisons/agreement-results.json")
    report = artifacts.get("comparisons/consensus-report.json")
    if report is not None:
        summary = report.get("summary", {})
        stability = report.get("model_stability", [])
        reference = report.get("reference_diagnostics", [])
        priorities = report.get("review_priorities", [])
        if isinstance(summary, Mapping):
            reconciliations = {
                "field_count": len(stability) if isinstance(stability, list) else -1,
                "stable_field_count": sum(
                    row.get("status") == "stable"
                    for row in stability
                    if isinstance(row, Mapping)
                ),
                "unstable_field_count": sum(
                    row.get("status") == "unstable"
                    for row in stability
                    if isinstance(row, Mapping)
                ),
                "review_queue_count": (
                    len(priorities) if isinstance(priorities, list) else -1
                ),
                "unanimous_reference_challenge_count": sum(
                    int(row.get("unanimous_reference_challenge_count", 0))
                    for row in reference
                    if isinstance(row, Mapping)
                ),
            }
            for key, expected in reconciliations.items():
                if summary.get(key) != expected:
                    errors.append(
                        f"{model_root}: consensus summary `{key}` does not reconcile"
                    )

    notes = artifacts.get("codebook/codebook-revision-notes.json")
    decisions = artifacts.get("codebook/recommendation-decisions.json")
    if decisions is not None and notes is None:
        errors.append(
            f"{model_root}: decision register has no generated codebook notes"
        )
    if notes is not None:
        recommendations = notes.get("recommendations", [])
        if not isinstance(recommendations, list):
            recommendations = []
        recommendation_ids = [
            item.get("recommendation_id")
            for item in recommendations
            if isinstance(item, Mapping)
        ]
        if len(recommendation_ids) != len(set(recommendation_ids)):
            errors.append(f"{model_root}: codebook notes contain duplicate IDs")
        summary = notes.get("summary", {})
        if isinstance(summary, Mapping):
            reconciliations = {
                "recommendation_count": len(recommendations),
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
            for key, expected in reconciliations.items():
                if summary.get(key) != expected:
                    errors.append(
                        f"{model_root}: codebook summary `{key}` does not reconcile"
                    )
        decision_entries = (
            decisions.get("decisions", [])
            if isinstance(decisions, Mapping)
            else []
        )
        decision_by_id = {
            item.get("recommendation_id"): item
            for item in decision_entries
            if isinstance(item, Mapping)
        }
        if len(decision_by_id) != len(decision_entries):
            errors.append(f"{model_root}: decision register contains duplicate IDs")
        recommendation_by_id = {
            item.get("recommendation_id"): item
            for item in recommendations
            if isinstance(item, Mapping)
        }
        unknown_decisions = sorted(set(decision_by_id) - set(recommendation_by_id))
        if unknown_decisions:
            errors.append(
                f"{model_root}: decision register references unknown recommendation(s)"
            )
        for recommendation_id, recommendation in recommendation_by_id.items():
            decision = decision_by_id.get(recommendation_id)
            if decision is None:
                if recommendation.get("decision_source") != "generated-default":
                    errors.append(
                        f"{model_root}: codebook recommendation `{recommendation_id}` "
                        "has a stale human decision"
                    )
                continue
            comparisons = {
                "disposition": "disposition",
                "decision_rationale": "rationale",
                "reviewer": "reviewer",
                "decided_at": "decided_at",
            }
            if recommendation.get("decision_source") != "human-decision-register":
                errors.append(
                    f"{model_root}: codebook recommendation `{recommendation_id}` "
                    "does not record its human decision source"
                )
            for note_field, decision_field in comparisons.items():
                if recommendation.get(note_field) != decision.get(decision_field):
                    errors.append(
                        f"{model_root}: codebook recommendation `{recommendation_id}` "
                        "is stale relative to the decision register"
                    )
                    break

    completion = artifacts.get("completion/completion-checklist.json")
    if completion is not None:
        checks = completion.get("checks", [])
        if not isinstance(checks, list):
            checks = []
        failed_check_ids = [
            item.get("check_id")
            for item in checks
            if isinstance(item, Mapping) and item.get("status") != "pass"
        ]
        summary = completion.get("summary", {})
        expected_status = "complete" if not failed_check_ids else "blocked"
        if completion.get("status") != expected_status:
            errors.append(
                f"{model_root}: completion status does not reconcile with checks"
            )
        if isinstance(summary, Mapping):
            reconciliations = {
                "check_count": len(checks),
                "passed_count": len(checks) - len(failed_check_ids),
                "failed_count": len(failed_check_ids),
                "failed_check_ids": failed_check_ids,
            }
            for key, expected in reconciliations.items():
                if summary.get(key) != expected:
                    errors.append(
                        f"{model_root}: completion summary `{key}` does not reconcile"
                    )
        if completion.get("status") == "complete":
            commands = completion.get("required_commands", [])
            commands_pass = isinstance(commands, list) and all(
                isinstance(item, Mapping)
                and item.get("status") == "pass"
                and item.get("exit_code") == 0
                for item in commands
            )
            if not commands_pass:
                errors.append(
                    f"{model_root}: complete checklist has unpassed repository commands"
                )

    invalid_count = sum(
        entry.get("status") == "invalid"
        for entry in submissions
        if isinstance(entry, Mapping)
    )
    return len(runs), invalid_count


def evaluate_case(
    root: Path,
    case_id: str,
    *,
    validate_existing_status: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    case_root = root / "cases" / case_id
    model_root = case_root / "quality" / "model-reliability"
    errors: list[str] = []
    warnings: list[str] = []
    if not case_root.is_dir():
        errors.append(f"unknown case `{case_id}`")
    artifacts: dict[str, Mapping[str, Any]] = {}
    present_files = (
        sorted(
            path
            for path in model_root.rglob("*")
            if path.is_file() and path.name != "status.json"
        )
        if model_root.exists()
        else []
    )
    for relative, schema_name in ARTIFACT_SCHEMAS.items():
        if relative == "status.json" and not validate_existing_status:
            continue
        path = model_root / relative
        if not path.exists():
            continue
        value = _read(path, errors)
        if value is None:
            continue
        artifacts[relative] = value
        schema = _schema(root, schema_name, errors)
        if schema is not None:
            _validate_schema(path, value, schema, errors)
        if value.get("case_id") != case_id:
            errors.append(f"{path}: case_id does not match `{case_id}`")

    manifest = artifacts.get("packets/packet-manifest.json")
    if manifest is not None:
        _validate_packet(root, case_id, manifest, errors)

    reports = _validation_reports(root, model_root, case_id, errors)
    run_count, invalid_count = _cross_validate(
        case_id, model_root, artifacts, reports, errors
    )
    submission_count = len(
        artifacts.get("submissions/submission-register.json", {}).get(
            "submissions", []
        )
    )
    complete_present = all((model_root / path).is_file() for path in COMPLETE_ARTIFACTS)
    sample_present = (model_root / "sample" / "sample-manifest.json").is_file()
    packet_present = manifest is not None

    if errors or invalid_count:
        state = "invalid"
        if invalid_count:
            warnings.append(f"{invalid_count} invalid submission(s) require review.")
    elif run_count >= 2 and complete_present:
        state = "complete"
    elif submission_count or run_count or any(
        relative.startswith(("normalized/", "comparisons/", "review-queue/"))
        for relative in artifacts
    ):
        state = "partial"
        warnings.append(
            "Reliability execution has started, but required downstream artifacts "
            "are incomplete."
        )
    elif sample_present and packet_present:
        state = "designed"
        warnings.append(
            "Blind packets are ready; no valid external model submissions are present."
        )
    elif present_files:
        state = "partial"
        warnings.append("Reliability design artifacts are incomplete.")
    else:
        state = "absent"
        warnings.append("Multi-model reliability has not been designed for this case.")

    return {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "generator": STATUS_GENERATOR,
        "state": state,
        "valid": not errors and invalid_count == 0,
        "counts": {
            "submissions": submission_count,
            "valid_runs": run_count,
            "invalid_submissions": invalid_count,
        },
        "artifacts": {
            "sample": sample_present,
            "packets": packet_present,
            "agreement": "comparisons/agreement-results.json" in artifacts,
            "disagreements": "comparisons/disagreement-log.json" in artifacts,
            "review_queue": "review-queue/model-review-queue.json" in artifacts,
            "report": "comparisons/consensus-report.json" in artifacts,
            "codebook_notes": "codebook/codebook-revision-notes.json" in artifacts,
        },
        "warnings": warnings,
        "errors": errors,
    }


def write_case_status(root: Path, case_id: str) -> dict[str, Any]:
    status = evaluate_case(root, case_id, validate_existing_status=False)
    case_root = root.resolve() / "cases" / case_id
    path = safe_output_path(case_root, "quality/model-reliability/status.json")
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
        f"{args.case_id}: model reliability is `{result['state']}` "
        f"with {len(result['errors'])} error(s)"
    )
    for warning in result["warnings"]:
        print(f"WARNING: {warning}")
    return 1 if result["state"] == "invalid" else 0


if __name__ == "__main__":
    raise SystemExit(main())
