#!/usr/bin/env python3
"""Ingest and normalize one independent human adjudication submission."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

try:
    from scripts.human_reliability.boundaries import protect_accepted_artifacts, safe_output_path
    from scripts.human_reliability.compute_agreement import (
        SAFE_COMPONENT,
        _cohort_manifest_path,
    )
    from scripts.human_reliability.generate_packets import sha256_bytes
    from scripts.human_reliability.ingest_submission import (
        IngestionError,
        _contains_sensitive_data,
        load_cohort_context,
        read_json_object,
        schema_errors,
        utc_now,
        write_json,
    )
except ModuleNotFoundError:
    from boundaries import protect_accepted_artifacts, safe_output_path  # type: ignore
    from compute_agreement import SAFE_COMPONENT, _cohort_manifest_path  # type: ignore
    from generate_packets import sha256_bytes  # type: ignore
    from ingest_submission import (  # type: ignore
        IngestionError,
        _contains_sensitive_data,
        load_cohort_context,
        read_json_object,
        schema_errors,
        utc_now,
        write_json,
    )


ROOT = Path(__file__).resolve().parents[2]
QUEUE_GENERATOR = "scripts/human_reliability/generate_adjudication_queue.py"
CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MIN_RATIONALE_LENGTH = 20
JUDGMENT_VALUES = {"present", "absent", "uncertain", "not_applicable"}
IDENTIFICATION_VALUES = {
    "mipvu_indirect",
    "mipvu_direct",
    "mipvu_implicit",
    "mipvu_personification",
    "non_metaphor",
    "excluded_nonlexical",
    "uncertain",
}
BOUNDARY_VALUES = {
    "exact",
    "expand",
    "contract",
    "split",
    "merge",
    "no_valid_span",
    "uncertain",
}
UNCERTAINTY_VALUES = {"none", "low", "material", "unresolved"}


class AdjudicationIngestionError(ValueError):
    """Raised when adjudication cannot be preserved or safely normalized."""


def _path(parts: Iterable[Any]) -> str:
    rendered = "$"
    for part in parts:
        rendered += f"[{part}]" if isinstance(part, int) else f".{part}"
    return rendered


def parse_json_adjudication(path: Path) -> tuple[dict[str, Any], bytes, list[str]]:
    raw = path.read_bytes()
    errors: list[str] = []
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"$: invalid JSON adjudication submission: {exc}")
        value = {}
    if not isinstance(value, dict):
        errors.append("$: adjudication submission must be an object")
        value = {}
    return value, raw, errors


def _canonical(value: Any) -> str:
    if isinstance(value, list):
        value = sorted(
            value,
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True),
        )
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _equal(left: Any, right: Any) -> bool:
    return _canonical(left) == _canonical(right)


def _nullable_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _nullable_sha256(value: Any) -> str | None:
    if isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        return value
    return None


def _queue_context(
    root: Path,
    case_root: Path,
    case_id: str,
    cohort_id: str,
    cohort_version: str,
) -> tuple[dict[str, Any], Path, str]:
    queue_path = (
        case_root
        / "quality"
        / "human-reliability"
        / "comparisons"
        / f"{cohort_id}-{cohort_version}"
        / "adjudication-queue.json"
    )
    queue = read_json_object(queue_path)
    queue_schema = read_json_object(
        root / "schemas" / "human-reliability" / "adjudication-queue-schema.json"
    )
    errors = schema_errors(queue, queue_schema)
    if errors:
        raise AdjudicationIngestionError(
            "adjudication queue fails schema validation: " + "; ".join(errors)
        )
    for field, expected in (
        ("case_id", case_id),
        ("cohort_id", cohort_id),
        ("cohort_version", cohort_version),
    ):
        if queue.get(field) != expected:
            raise AdjudicationIngestionError(
                f"adjudication queue differs from requested context on `{field}`"
            )
    queue_ids = [
        entry.get("queue_id")
        for entry in queue.get("entries", [])
        if isinstance(entry, Mapping)
    ]
    if (
        len(queue_ids) != queue.get("summary", {}).get("queue_count")
        or not all(isinstance(queue_id, str) and queue_id for queue_id in queue_ids)
        or len(queue_ids) != len(set(queue_ids))
    ):
        raise AdjudicationIngestionError(
            "adjudication queue has missing, duplicate, or unreconciled queue IDs"
        )
    generator = queue.get("generator")
    generator_path = root / QUEUE_GENERATOR
    if not generator_path.is_file():
        generator_path = ROOT / QUEUE_GENERATOR
    if (
        not isinstance(generator, Mapping)
        or generator.get("script") != QUEUE_GENERATOR
        or generator.get("script_hash") != sha256_bytes(generator_path.read_bytes())
    ):
        raise AdjudicationIngestionError(
            "adjudication queue has an unexpected or stale generator"
        )
    return queue, queue_path, sha256_bytes(queue_path.read_bytes())


def _vocabularies(root: Path) -> dict[str, set[str]]:
    value = read_json_object(root / "config" / "controlled-vocabularies.json")
    return {
        key: {
            str(item["id"])
            for item in values
            if isinstance(item, Mapping) and item.get("id")
        }
        for key, values in value.items()
        if isinstance(values, list)
    }


def _validate_value(
    field: str,
    value: Any,
    vocabularies: Mapping[str, set[str]],
    prefix: str,
) -> list[str]:
    errors: list[str] = []
    allowed: set[str] | None = None
    if field == "identification.decision_type":
        allowed = IDENTIFICATION_VALUES
    elif field == "identification.boundary_response":
        allowed = BOUNDARY_VALUES
    elif field == "identification.selected_unit_boundary":
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item for item in value
        ) or len(value) != len(set(value)):
            errors.append(
                f"{prefix}: selected boundary must be a unique string array"
            )
        return errors
    elif field in {"cmt.source_domain_primary"}:
        allowed = vocabularies.get("source_domains", set())
    elif field == "cmt.source_domain_secondary":
        if not isinstance(value, list) or not all(
            isinstance(item, str)
            and item in vocabularies.get("source_domains", set())
            for item in value
        ):
            errors.append(f"{prefix}: contains an unknown source-domain value")
        return errors
    elif field == "cmt.target_domain":
        allowed = vocabularies.get("target_domains", set())
    elif field == "cmt.cluster_id":
        if value is not None and (not isinstance(value, str) or not value):
            errors.append(f"{prefix}: cluster ID must be a non-empty string or null")
        return errors
    elif field.startswith("interpretation.") and field.split(".", 1)[1] in {
        "sacred_object",
        "sacrificial_body",
        "enemy_as_bringer_of_death",
        "violence_logic",
        "obligatory_frame",
        "purification",
        "absence_decision",
    }:
        allowed = JUDGMENT_VALUES
    elif field == "uncertainty":
        allowed = UNCERTAINTY_VALUES
    elif field == "disposition":
        allowed = {"coded", "out_of_scope"}
    elif field == "confidence":
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
            errors.append(f"{prefix}: confidence must be a number from 0 through 1")
        return errors
    elif field.startswith(("identification.", "cmt.", "interpretation.")):
        if field in {
            "cmt.entailments",
            "interpretation.agents",
            "interpretation.patients",
            "interpretation.beneficiaries",
            "interpretation.excluded_agents",
        }:
            if not isinstance(value, list) or not all(
                isinstance(item, str) and item for item in value
            ) or len(value) != len(set(value)):
                errors.append(f"{prefix}: must be a unique string array")
        elif not isinstance(value, str) or not value.strip():
            errors.append(f"{prefix}: must be a non-empty string")
        return errors
    if allowed is not None and value not in allowed:
        errors.append(f"{prefix}: unknown controlled value `{value}`")
    return errors


def validate_adjudication(
    root: Path,
    submission: Mapping[str, Any],
    queue: Mapping[str, Any],
    queue_path: Path,
    queue_hash: str,
    cohort: Mapping[str, Any],
    *,
    schema: Mapping[str, Any] | None = None,
) -> list[str]:
    active_schema = schema or read_json_object(
        root / "schemas" / "human-reliability" / "adjudication-decision-schema.json"
    )
    validator = Draft202012Validator(active_schema, format_checker=FormatChecker())
    errors = [
        f"{_path(error.absolute_path)}: {error.message}"
        for error in sorted(
            validator.iter_errors(submission),
            key=lambda error: list(error.absolute_path),
        )
    ]
    for field in (
        "case_id",
        "cohort_id",
        "cohort_version",
        "source_language",
        "task_layer",
    ):
        if submission.get(field) != queue.get(field):
            errors.append(f"$.{field}: does not match the frozen adjudication queue")
    adjudicator = submission.get("adjudicator")
    if isinstance(adjudicator, Mapping):
        adjudicator_id = adjudicator.get("adjudicator_id")
        primary_ids = set(cohort.get("primary_coder_ids", []))
        if adjudicator.get("primary_coder_for_cohort") != (
            isinstance(adjudicator_id, str) and adjudicator_id in primary_ids
        ):
            errors.append(
                "$.adjudicator.primary_coder_for_cohort: does not match cohort assignments"
            )

    snapshot = submission.get("queue_snapshot")
    if isinstance(snapshot, Mapping):
        expected_source = queue_path.relative_to(root / "cases" / queue["case_id"]).as_posix()
        generator = queue.get("generator", {})
        expected = {
            "queue_schema_version": queue.get("schema_version"),
            "queue_source": expected_source,
            "queue_sha256": queue_hash,
            "queue_generator_script": generator.get("script"),
            "queue_generator_version": generator.get("version"),
            "queue_generator_script_hash": generator.get("script_hash"),
            "queue_code_revision": generator.get("code_revision"),
        }
        for field, expected_value in expected.items():
            if snapshot.get(field) != expected_value:
                errors.append(
                    f"$.queue_snapshot.{field}: does not match the frozen queue"
                )
        try:
            frozen_at = dt.datetime.fromisoformat(
                str(snapshot.get("frozen_at")).replace("Z", "+00:00")
            )
            submitted_at = dt.datetime.fromisoformat(
                str(submission.get("submitted_at")).replace("Z", "+00:00")
            )
            if frozen_at > submitted_at:
                errors.append(
                    "$.queue_snapshot.frozen_at: cannot be later than submitted_at"
                )
        except (ValueError, TypeError):
            pass

    queue_entries = {
        str(entry.get("queue_id") or ""): entry
        for entry in queue.get("entries", [])
        if isinstance(entry, Mapping)
    }
    decisions = submission.get("decisions")
    if not isinstance(decisions, list):
        return list(dict.fromkeys(errors))
    seen_queue: set[str] = set()
    seen_adjudication: set[str] = set()
    seen_candidates: set[str] = set()
    seen_evidence: set[str] = set()
    vocabularies = _vocabularies(root)
    for index, decision in enumerate(decisions):
        if not isinstance(decision, Mapping):
            continue
        prefix = f"$.decisions[{index}]"
        queue_id = str(decision.get("queue_id") or "")
        adjudication_id = str(decision.get("adjudication_id") or "")
        if queue_id in seen_queue:
            errors.append(f"{prefix}.queue_id: duplicate queue ID `{queue_id}`")
        seen_queue.add(queue_id)
        if adjudication_id in seen_adjudication:
            errors.append(
                f"{prefix}.adjudication_id: duplicate adjudication ID `{adjudication_id}`"
            )
        seen_adjudication.add(adjudication_id)
        expected = queue_entries.get(queue_id)
        if expected is None:
            errors.append(f"{prefix}.queue_id: unknown queue ID `{queue_id}`")
            continue
        for field in (
            "disagreement_id",
            "item_id",
            "reference_id",
            "unit_id",
            "field",
        ):
            if decision.get(field) != expected.get(field):
                errors.append(f"{prefix}.{field}: does not match queue entry `{queue_id}`")
        rationale = decision.get("rationale")
        if not isinstance(rationale, str) or len(rationale.strip()) < MIN_RATIONALE_LENGTH:
            errors.append(
                f"{prefix}.rationale: must contain at least "
                f"{MIN_RATIONALE_LENGTH} non-whitespace characters"
            )
        if isinstance(rationale, str) and CONTROL_CHARACTER_PATTERN.search(rationale):
            errors.append(f"{prefix}.rationale: contains a prohibited control character")
        evidence = decision.get("evidence_consulted")
        if isinstance(evidence, list):
            evidence_ids = [
                item.get("evidence_id")
                for item in evidence
                if isinstance(item, Mapping)
            ]
            valid_evidence_ids = [
                evidence_id
                for evidence_id in evidence_ids
                if isinstance(evidence_id, str) and evidence_id
            ]
            if len(valid_evidence_ids) != len(set(valid_evidence_ids)):
                errors.append(f"{prefix}.evidence_consulted: duplicate evidence IDs")
            repeated = sorted(
                {
                    evidence_id
                    for evidence_id in valid_evidence_ids
                    if evidence_id in seen_evidence
                }
            )
            if repeated:
                errors.append(
                    f"{prefix}.evidence_consulted: evidence ID(s) already used: "
                    + ", ".join(repeated)
                )
            seen_evidence.update(valid_evidence_ids)

        basis = decision.get("selected_basis")
        adjudicated_value = decision.get("adjudicated_value")
        coder_values = expected.get("coder_values", [])
        reference = expected.get("reference_summary", {})
        if decision.get("status") == "accepted":
            if basis == "left_coder" and (
                not coder_values or not _equal(adjudicated_value, coder_values[0].get("value"))
            ):
                errors.append(f"{prefix}.adjudicated_value: differs from left coder value")
            if basis == "right_coder" and (
                len(coder_values) < 2
                or not _equal(adjudicated_value, coder_values[1].get("value"))
            ):
                errors.append(f"{prefix}.adjudicated_value: differs from right coder value")
            if basis == "reference" and (
                not isinstance(reference, Mapping)
                or reference.get("status") != "available"
                or not _equal(adjudicated_value, reference.get("value"))
            ):
                errors.append(
                    f"{prefix}.adjudicated_value: differs from the available reference"
                )
            errors.extend(
                _validate_value(
                    str(expected.get("field") or ""),
                    adjudicated_value,
                    vocabularies,
                    f"{prefix}.adjudicated_value",
                )
            )

        queue_claims = {
            str(item.get("claim_id") or "")
            for item in expected.get("affected_claims", [])
            if isinstance(item, Mapping)
        }
        decision_claims = decision.get("affected_claims")
        if isinstance(decision_claims, list):
            claim_ids = [
                str(item.get("claim_id") or "")
                for item in decision_claims
                if isinstance(item, Mapping)
            ]
            if len(claim_ids) != len(set(claim_ids)):
                errors.append(f"{prefix}.affected_claims: duplicate claim IDs")
            if set(claim_ids) != queue_claims:
                errors.append(
                    f"{prefix}.affected_claims: must cover queue-linked claims exactly"
                )
        if not _equal(
            decision.get("affected_claim_dimensions", []),
            expected.get("affected_claim_dimensions", []),
        ):
            errors.append(
                f"{prefix}.affected_claim_dimensions: does not match queue entry"
            )

        candidate = decision.get("correction_candidate")
        if isinstance(candidate, Mapping) and candidate.get("status") == "candidate":
            candidate_id = str(candidate.get("candidate_id") or "")
            if candidate_id in seen_candidates:
                errors.append(
                    f"{prefix}.correction_candidate.candidate_id: duplicate candidate ID"
                )
            seen_candidates.add(candidate_id)
            if decision.get("status") != "accepted":
                errors.append(
                    f"{prefix}.correction_candidate: only accepted decisions may emit a candidate"
                )
            if not isinstance(reference, Mapping) or reference.get("status") != "available":
                errors.append(
                    f"{prefix}.correction_candidate: requires an available queue reference"
                )
            target = candidate.get("target")
            if isinstance(target, Mapping):
                if not str(target.get("canonical_artifact") or "").startswith(
                    f"cases/{queue['case_id']}/"
                ):
                    errors.append(
                        f"{prefix}.correction_candidate.target.canonical_artifact: "
                        "does not belong to the adjudicated case"
                    )
                if target.get("target_id") != expected.get("reference_id"):
                    errors.append(
                        f"{prefix}.correction_candidate.target.target_id: "
                        "does not match the queue reference ID"
                    )
                if target.get("field") != expected.get("field"):
                    errors.append(
                        f"{prefix}.correction_candidate.target.field: "
                        "does not match the queue field"
                    )
                if not _equal(target.get("current_value"), reference.get("value")):
                    errors.append(
                        f"{prefix}.correction_candidate.target.current_value: "
                        "does not match the queue reference"
                    )
                if not _equal(target.get("proposed_value"), adjudicated_value):
                    errors.append(
                        f"{prefix}.correction_candidate.target.proposed_value: "
                        "does not match the adjudicated value"
                    )

    missing = sorted(set(queue_entries) - seen_queue)
    if missing:
        errors.append("$.decisions: missing queue item(s): " + ", ".join(missing))
    try:
        submitted_at = dt.datetime.fromisoformat(
            str(submission.get("submitted_at")).replace("Z", "+00:00")
        )
        raw_snapshot = submission.get("queue_snapshot")
        frozen_at = dt.datetime.fromisoformat(
            str(
                raw_snapshot.get("frozen_at")
                if isinstance(raw_snapshot, Mapping)
                else None
            ).replace("Z", "+00:00")
        )
        for index, decision in enumerate(decisions):
            if not isinstance(decision, Mapping):
                continue
            decided_at = dt.datetime.fromisoformat(
                str(decision.get("decided_at")).replace("Z", "+00:00")
            )
            if decided_at > submitted_at:
                errors.append(
                    f"$.decisions[{index}].decided_at: cannot be later than submitted_at"
                )
            if decided_at < frozen_at:
                errors.append(
                    f"$.decisions[{index}].decided_at: cannot predate the frozen queue"
                )
    except (ValueError, TypeError):
        pass
    return list(dict.fromkeys(errors))


def _decision_results(
    submission: Mapping[str, Any], errors: Sequence[str]
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for index, decision in enumerate(submission.get("decisions", [])):
        if not isinstance(decision, Mapping):
            continue
        prefix = f"$.decisions[{index}]"
        item_errors = [error for error in errors if error.startswith(prefix)]
        results.append(
            {
                "index": index,
                "adjudication_id": decision.get("adjudication_id"),
                "queue_id": decision.get("queue_id"),
                "status": "invalid" if item_errors else "valid",
                "errors": item_errors,
            }
        )
    return results


def _summary(decisions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(decision.get("status") or "") for decision in decisions)
    unresolved = counts["deferred"] + counts["unresolved"]
    return {
        "decision_count": len(decisions),
        "accepted_count": counts["accepted"],
        "rejected_count": counts["rejected"],
        "deferred_count": counts["deferred"],
        "unresolved_count": counts["unresolved"],
        "correction_candidate_count": sum(
            decision.get("correction_candidate", {}).get("status") == "candidate"
            for decision in decisions
        ),
        "state": "unresolved" if unresolved else "complete",
    }


def _assert_schema(
    root: Path, value: Mapping[str, Any], schema_name: str, label: str
) -> None:
    schema = read_json_object(
        root / "schemas" / "human-reliability" / schema_name
    )
    errors = schema_errors(value, schema)
    if errors:
        raise AdjudicationIngestionError(
            f"{label} fails schema validation: " + "; ".join(errors)
        )


def _write_candidate_csv(path: Path, candidates: Sequence[Mapping[str, Any]]) -> None:
    fields = [
        "candidate_id",
        "adjudication_id",
        "queue_id",
        "disagreement_id",
        "item_id",
        "reference_id",
        "target",
        "rationale",
        "affected_claims",
        "affected_claim_dimensions",
        "promotion_status",
        "promotion_id",
        "direct_write_permitted",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for candidate in candidates:
            row = dict(candidate)
            for field in ("target", "affected_claims", "affected_claim_dimensions"):
                row[field] = json.dumps(
                    candidate[field], ensure_ascii=False, sort_keys=True
                )
            writer.writerow({field: row.get(field) for field in fields})


def _markdown_report(report: Mapping[str, Any]) -> str:
    lines = [
        f"# Human Adjudication Validation: {report['registration_id']}",
        "",
        f"- Status: **{report['status']}**",
        f"- Adjudication state: **{report['adjudication_state']}**",
        f"- Submission ID: `{report.get('adjudication_submission_id') or 'missing'}`",
        f"- Adjudicator ID: `{report.get('adjudicator_id') or 'missing'}`",
        f"- Errors: {len(report['errors'])}",
        "",
    ]
    if report["errors"]:
        lines.extend(["## Errors", ""])
        lines.extend(f"- {error}" for error in report["errors"])
        lines.append("")
    return "\n".join(lines)


@protect_accepted_artifacts
def ingest_adjudication(
    root: Path,
    case_id: str,
    cohort_id: str,
    cohort_version: str,
    source_path: Path,
) -> dict[str, Any]:
    root = root.resolve()
    for label, value in (
        ("case_id", case_id),
        ("cohort_id", cohort_id),
        ("cohort_version", cohort_version),
    ):
        if not SAFE_COMPONENT.fullmatch(value):
            raise AdjudicationIngestionError(f"unsafe {label} `{value}`")
    case_root = root / "cases" / case_id
    if not case_root.is_dir():
        raise AdjudicationIngestionError(f"unknown case `{case_id}`")
    submission, raw, parse_errors = parse_json_adjudication(source_path)
    if _contains_sensitive_data({"adjudication.json": raw}):
        raise AdjudicationIngestionError(
            "refusing to store adjudication that appears to contain credentials"
        )
    cohort_path = _cohort_manifest_path(case_root, cohort_id, cohort_version)
    try:
        cohort_context = load_cohort_context(root, case_id, cohort_path)
    except IngestionError as exc:
        raise AdjudicationIngestionError(str(exc)) from exc
    if (
        cohort_context.manifest.get("storage_policy") == "local_only"
        and (root / ".git").exists()
    ):
        for relative in (
            f"cases/{case_id}/quality/human-reliability/adjudication",
            f"cases/{case_id}/quality/human-reliability/correction-candidates",
        ):
            ignored = subprocess.run(
                ["git", "check-ignore", "--quiet", relative],
                cwd=root,
                check=False,
            )
            if ignored.returncode != 0:
                raise AdjudicationIngestionError(
                    f"local_only adjudication output is not gitignored: {relative}"
                )
    queue, queue_path, queue_hash = _queue_context(
        root, case_root, case_id, cohort_id, cohort_version
    )
    for field in ("source_language", "task_layer", "packet_id"):
        if queue.get(field) != cohort_context.manifest.get(field):
            raise AdjudicationIngestionError(
                f"adjudication queue differs from the approved cohort on `{field}`"
            )
    for entry in queue.get("entries", []):
        if not isinstance(entry, Mapping):
            continue
        if entry.get("storage_policy") != cohort_context.manifest.get(
            "storage_policy"
        ):
            raise AdjudicationIngestionError(
                "adjudication queue storage policy differs from the approved cohort"
            )
        if sorted(entry.get("rights_constraints", [])) != sorted(
            cohort_context.manifest.get("rights_constraints", [])
        ):
            raise AdjudicationIngestionError(
                "adjudication queue rights constraints differ from the approved cohort"
            )
    errors = list(parse_errors)
    errors.extend(
        validate_adjudication(
            root,
            submission,
            queue,
            queue_path,
            queue_hash,
            cohort_context.manifest,
        )
    )

    raw_hash = sha256_bytes(raw)
    registration_id = (
        "adjudication-registration-" + raw_hash.removeprefix("sha256:")[:16]
    )
    decisions_root = "quality/human-reliability/adjudication/decisions"
    register_path = safe_output_path(
        case_root, f"{decisions_root}/adjudication-register.json"
    )
    register = read_json_object(register_path) if register_path.exists() else {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "submissions": [],
    }
    entries = register.get("submissions")
    if register.get("case_id") != case_id or not isinstance(entries, list):
        raise AdjudicationIngestionError("adjudication register is malformed")
    existing = next(
        (
            entry
            for entry in entries
            if entry.get("registration_id") == registration_id
        ),
        None,
    )
    raw_path = safe_output_path(
        case_root, f"{decisions_root}/raw/{registration_id}/adjudication.json"
    )
    report_path = safe_output_path(
        case_root, f"{decisions_root}/validation-reports/{registration_id}.json"
    )
    if existing:
        if not raw_path.is_file() or raw_path.read_bytes() != raw:
            raise AdjudicationIngestionError(
                f"immutable raw adjudication registration was altered: {raw_path}"
            )
        return read_json_object(report_path)

    submission_id = _nullable_string(
        submission.get("adjudication_submission_id")
    )
    adjudicator = submission.get("adjudicator")
    adjudicator_id = _nullable_string(
        adjudicator.get("adjudicator_id")
        if isinstance(adjudicator, Mapping)
        else None
    )
    submitted_cohort_id = _nullable_string(submission.get("cohort_id"))
    submitted_cohort_version = _nullable_string(
        submission.get("cohort_version")
    )
    submitted_queue_sha = _nullable_sha256(
        submission.get("queue_snapshot", {}).get("queue_sha256")
        if isinstance(submission.get("queue_snapshot"), Mapping)
        else None
    )
    for entry in entries:
        if entry.get("status") != "valid":
            continue
        if submission_id and entry.get("adjudication_submission_id") == submission_id:
            errors.append(
                "$.adjudication_submission_id: duplicate valid submission ID "
                f"`{submission_id}`"
            )
        if (
            entry.get("cohort_id") == cohort_id
            and entry.get("cohort_version") == cohort_version
            and entry.get("queue_sha256") == queue_hash
        ):
            errors.append(
                "$.queue_snapshot.queue_sha256: a valid adjudication already "
                "exists for this frozen queue"
            )
    errors = list(dict.fromkeys(errors))
    status = "valid" if not errors else "invalid"
    registered_at = utc_now()
    decision_values = [
        decision
        for decision in submission.get("decisions", [])
        if isinstance(decision, Mapping)
    ]
    adjudication_state = (
        _summary(decision_values)["state"] if status == "valid" else "invalid"
    )
    report = {
        "schema_version": "1.0.0",
        "registration_id": registration_id,
        "registered_at": registered_at,
        "case_id": case_id,
        "cohort_id": submitted_cohort_id,
        "cohort_version": submitted_cohort_version,
        "adjudication_submission_id": submission_id,
        "adjudicator_id": adjudicator_id,
        "queue_sha256": submitted_queue_sha,
        "raw_hash": raw_hash,
        "status": status,
        "errors": errors,
        "decision_results": _decision_results(submission, errors),
        "adjudication_state": adjudication_state,
    }
    entry = {
        "registration_id": registration_id,
        "registered_at": registered_at,
        "cohort_id": submitted_cohort_id,
        "cohort_version": submitted_cohort_version,
        "adjudication_submission_id": submission_id,
        "adjudicator_id": adjudicator_id,
        "queue_sha256": submitted_queue_sha,
        "raw_hash": raw_hash,
        "status": status,
        "validation_report": report_path.relative_to(case_root).as_posix(),
    }
    future_register = {**register, "submissions": [*entries, entry]}
    _assert_schema(
        root,
        future_register,
        "adjudication-register-schema.json",
        "adjudication register",
    )
    _assert_schema(
        root,
        report,
        "adjudication-ingestion-report-schema.json",
        "adjudication ingestion report",
    )

    raw_path.parent.mkdir(parents=True, exist_ok=False)
    raw_path.write_bytes(raw)
    raw_path.chmod(0o444)
    write_json(report_path, report)
    report_path.with_suffix(".md").write_text(
        _markdown_report(report), encoding="utf-8"
    )
    entries.append(entry)
    register["submissions"] = entries
    write_json(register_path, register)

    if status == "valid":
        queue_index = {
            str(item["queue_id"]): item
            for item in queue["entries"]
            if isinstance(item, Mapping)
        }
        normalized_decisions = [
            {
                "queue_entry": queue_index[str(decision["queue_id"])],
                "decision": decision,
            }
            for decision in decision_values
        ]
        summary = _summary(decision_values)
        results = {
            "schema_version": "1.0.0",
            "case_id": case_id,
            "cohort_id": cohort_id,
            "cohort_version": cohort_version,
            "source_language": queue["source_language"],
            "task_layer": queue["task_layer"],
            "queue_snapshot": submission["queue_snapshot"],
            "registration_id": registration_id,
            "registered_at": registered_at,
            "raw_hash": raw_hash,
            "adjudication_submission_id": submission_id,
            "adjudicator": adjudicator,
            "summary": summary,
            "decisions": normalized_decisions,
        }
        _assert_schema(
            root,
            results,
            "adjudication-results-schema.json",
            "normalized adjudication results",
        )
        results_path = safe_output_path(
            case_root,
            "quality/human-reliability/adjudication/results/"
            f"{cohort_id}-{cohort_version}/adjudication-results.json",
        )
        write_json(results_path, results)

        candidates = []
        for decision in decision_values:
            candidate = decision.get("correction_candidate", {})
            if not isinstance(candidate, Mapping) or candidate.get("status") != "candidate":
                continue
            candidates.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "adjudication_id": decision["adjudication_id"],
                    "queue_id": decision["queue_id"],
                    "disagreement_id": decision["disagreement_id"],
                    "item_id": decision["item_id"],
                    "reference_id": decision["reference_id"],
                    "target": candidate["target"],
                    "rationale": candidate["rationale"],
                    "affected_claims": decision["affected_claims"],
                    "affected_claim_dimensions": decision[
                        "affected_claim_dimensions"
                    ],
                    "promotion_status": candidate["promotion_status"],
                    "promotion_id": candidate["promotion_id"],
                    "direct_write_permitted": candidate[
                        "direct_write_permitted"
                    ],
                }
            )
        candidate_document = {
            "schema_version": "1.0.0",
            "case_id": case_id,
            "cohort_id": cohort_id,
            "cohort_version": cohort_version,
            "source_registration_id": registration_id,
            "source_queue_sha256": queue_hash,
            "authority": {
                "layer": "dedicated_review_only",
                "promotion_permitted": False,
                "notice": (
                    "Correction candidates are proposals only and cannot update "
                    "accepted artifacts without separate authorization."
                ),
            },
            "candidates": candidates,
        }
        _assert_schema(
            root,
            candidate_document,
            "correction-candidates-schema.json",
            "correction candidates",
        )
        candidate_root = (
            "quality/human-reliability/correction-candidates/"
            f"{cohort_id}-{cohort_version}"
        )
        write_json(
            safe_output_path(
                case_root, f"{candidate_root}/correction-candidates.json"
            ),
            candidate_document,
        )
        _write_candidate_csv(
            safe_output_path(
                case_root, f"{candidate_root}/correction-candidates.csv"
            ),
            candidates,
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument("--cohort", dest="cohort_id", required=True)
    parser.add_argument("--cohort-version", required=True)
    parser.add_argument("--json", dest="source_path", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = ingest_adjudication(
            ROOT,
            args.case_id,
            args.cohort_id,
            args.cohort_version,
            args.source_path,
        )
    except (AdjudicationIngestionError, IngestionError, OSError) as exc:
        parser.error(str(exc))
    print(
        f"{args.case_id}: adjudication registration "
        f"`{report['registration_id']}` is {report['status']}"
    )
    return 0 if report["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
