#!/usr/bin/env python3
"""Compare human coder values with accepted or reviewable references."""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

try:
    from scripts.human_reliability.boundaries import safe_output_path
    from scripts.human_reliability.compute_agreement import (
        AgreementError,
        FIELD_SPECS,
        POSITIVE_DECISIONS,
        SAFE_COMPONENT,
        _cohort_manifest_path,
        _comparable_metadata,
        _response_index,
        _submission,
        _vocabularies,
        _verify_raw_registrations,
    )
    from scripts.human_reliability.ingest_submission import (
        IngestionError,
        load_cohort_context,
    )
    from scripts.human_reliability.submission_contract import validate_submission
except ModuleNotFoundError:
    from boundaries import safe_output_path  # type: ignore
    from compute_agreement import (  # type: ignore
        AgreementError,
        FIELD_SPECS,
        POSITIVE_DECISIONS,
        SAFE_COMPONENT,
        _cohort_manifest_path,
        _comparable_metadata,
        _response_index,
        _submission,
        _vocabularies,
        _verify_raw_registrations,
    )
    from ingest_submission import IngestionError, load_cohort_context  # type: ignore
    from submission_contract import validate_submission  # type: ignore


ROOT = Path(__file__).resolve().parents[2]
GENERATOR_PATH = "scripts/human_reliability/compare_references.py"
GENERATOR_VERSION = "1.0.0"
REFERENCE_FIELDS = {
    "identification": {
        "identification.decision_type",
        "identification.boundary_response",
        "identification.selected_unit_boundary",
    },
    "cmt": {
        "cmt.source_domain_primary",
        "cmt.source_domain_secondary",
        "cmt.target_domain",
        "cmt.conceptual_mapping",
        "cmt.entailments",
        "cmt.cluster_id",
    },
    "interpretation": {
        "interpretation.violence_logic",
        "interpretation.obligatory_frame",
    },
}
QUALITATIVE_FIELDS = {
    field
    for values in FIELD_SPECS.values()
    for field, family, _ in values
    if family == "qualitative_only"
}


class ReferenceComparisonError(ValueError):
    """Raised when reference comparison inputs are unsafe or inconsistent."""


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReferenceComparisonError(f"{path}: unable to read JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ReferenceComparisonError(f"{path}: expected a JSON object")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def code_revision(root: Path) -> str:
    for workdir in (root, ROOT):
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workdir,
            check=False,
            capture_output=True,
            text=True,
        )
        revision = result.stdout.strip()
        if result.returncode == 0 and revision:
            return revision
    raise ReferenceComparisonError("unable to determine repository code revision")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _equal(left: Any, right: Any) -> bool:
    if isinstance(left, list) and isinstance(right, list):
        return {_canonical(value) for value in left} == {
            _canonical(value) for value in right
        }
    return left == right


def _authority(value: Mapping[str, Any], default: str) -> str:
    status = str(
        value.get("review_status")
        or value.get("mapping_status")
        or value.get("status")
        or ""
    )
    if status == "accepted":
        return "accepted"
    if status in {"reviewed", "in_review"}:
        return "reviewed"
    return default


def _bool_judgment(value: Any) -> str | None:
    if value is True:
        return "present"
    if value is False:
        return "absent"
    return None


def _put_reference(
    references: dict[tuple[str, str | None, str], dict[str, Any]],
    key: tuple[str, str | None, str],
    value: Any,
    authority: str,
) -> None:
    candidate = {"value": value, "authority": authority}
    existing = references.get(key)
    if existing is not None and existing != candidate:
        raise ReferenceComparisonError(
            f"conflicting reference values for `{key[0]}` `{key[2]}`"
        )
    references[key] = candidate


def load_references(
    root: Path,
    case_id: str,
    task_layer: str,
) -> tuple[dict[tuple[str, str | None, str], dict[str, Any]], list[dict[str, Any]]]:
    case_root = root / "cases" / case_id
    references: dict[tuple[str, str | None, str], dict[str, Any]] = {}
    sources: list[dict[str, Any]] = []
    for path in (
        sorted((case_root / "corpus" / "mipvu").glob("*_mipvu.json"))
        if task_layer == "identification"
        else []
    ):
        document = read_json_object(path)
        used = False
        all_units = [
            unit
            for unit in document.get("lexical_units", [])
            if isinstance(unit, Mapping)
        ]
        all_by_sentence: dict[str, list[Mapping[str, Any]]] = {}
        reviewed_by_sentence: dict[str, list[Mapping[str, Any]]] = {}
        for unit in all_units:
            sentence_id = str(unit.get("sentence_id") or "")
            all_by_sentence.setdefault(sentence_id, []).append(unit)
            if not isinstance(unit, Mapping):
                continue
            if str(unit.get("review_status") or "") not in {"accepted", "reviewed"}:
                continue
            unit_id = str(unit.get("mipvu_id") or "")
            if not unit_id:
                continue
            authority = _authority(unit, "reviewed")
            _put_reference(
                references,
                (sentence_id, unit_id, "identification.decision_type"),
                unit.get("decision_type"),
                authority,
            )
            _put_reference(
                references,
                (sentence_id, unit_id, "identification.boundary_response"),
                "exact",
                authority,
            )
            reviewed_by_sentence.setdefault(sentence_id, []).append(unit)
            used = True
        for sentence_id, units in reviewed_by_sentence.items():
            if len(units) != len(all_by_sentence.get(sentence_id, [])):
                continue
            selected = sorted(
                str(unit["mipvu_id"])
                for unit in units
                if unit.get("decision_type") in POSITIVE_DECISIONS
            )
            authority = (
                "accepted"
                if all(_authority(unit, "reviewed") == "accepted" for unit in units)
                else "reviewed"
            )
            _put_reference(
                references,
                (sentence_id, None, "identification.selected_unit_boundary"),
                selected,
                authority,
            )
        if used:
            sources.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "hash": sha256_bytes(path.read_bytes()),
                    "authority_status": "accepted"
                    if all(
                        str(unit.get("review_status") or "") == "accepted"
                        for unit in document.get("lexical_units", [])
                        if isinstance(unit, Mapping)
                    )
                    else "reviewed",
                }
            )
    for path in (
        sorted((case_root / "corpus" / "annotated").glob("*_annotated.json"))
        if task_layer in {"cmt", "interpretation"}
        else []
    ):
        document = read_json_object(path)
        used = False
        source_authority = "reviewable_reference"
        for instance in document.get("instances", []):
            if not isinstance(instance, Mapping):
                continue
            instance_id = str(instance.get("instance_id") or "")
            if not instance_id:
                continue
            authority = _authority(instance, "reviewable_reference")
            if authority == "accepted":
                source_authority = "accepted"
            elif authority == "reviewed" and source_authority != "accepted":
                source_authority = "reviewed"
            cmt = instance.get("cmt")
            if isinstance(cmt, Mapping):
                aliases = {
                    "source_domain_primary": "source_domain_primary",
                    "source_domain_secondary": "source_domain_secondary",
                    "target_domain": "target_domain",
                    "conceptual_mapping": "conceptual_metaphor",
                    "entailments": "entailments",
                    "cluster_id": "cluster_id",
                }
                for human_name, reference_name in aliases.items():
                    if reference_name in cmt:
                        _put_reference(
                            references,
                            (instance_id, None, f"cmt.{human_name}"),
                            cmt[reference_name],
                            authority,
                        )
                        used = True
            interpretation = instance.get("koenigsberg")
            if isinstance(interpretation, Mapping):
                for name in ("violence_logic", "obligatory_frame"):
                    judgment = _bool_judgment(interpretation.get(name))
                    if judgment is not None:
                        _put_reference(
                            references,
                            (instance_id, None, f"interpretation.{name}"),
                            judgment,
                            authority,
                        )
                        used = True
        if used:
            sources.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "hash": sha256_bytes(path.read_bytes()),
                    "authority_status": source_authority,
                }
            )
    return references, sources


def _human_values(
    submission: Mapping[str, Any],
) -> dict[tuple[str, str, str | None, str], Any]:
    layer = str(submission.get("task_layer") or "")
    values: dict[tuple[str, str, str | None, str], Any] = {}
    for item_id, response in _response_index(submission).items():
        reference_id = (
            str(response.get("sentence_id") or "")
            if layer == "identification"
            else str(response.get("source_span_id") or item_id)
        )
        values[(item_id, reference_id, None, "disposition")] = response.get(
            "disposition"
        )
        if response.get("disposition") != "coded":
            continue
        values[(item_id, reference_id, None, "uncertainty")] = response.get(
            "uncertainty"
        )
        if layer == "identification":
            selected: list[str] = []
            for unit in response.get("lexical_unit_responses", []):
                if not isinstance(unit, Mapping):
                    continue
                unit_id = str(unit.get("lexical_unit_id") or "")
                for name in (
                    "decision_type",
                    "boundary_response",
                    "contextual_meaning",
                    "basic_meaning",
                    "basic_meaning_source",
                    "contrast_explanation",
                    "comparison_basis",
                ):
                    if unit.get(name) is not None:
                        values[
                            (item_id, reference_id, unit_id, f"identification.{name}")
                        ] = unit.get(name)
                if unit.get("decision_type") in POSITIVE_DECISIONS:
                    selected.append(unit_id)
            values[
                (
                    item_id,
                    reference_id,
                    None,
                    "identification.selected_unit_boundary",
                )
            ] = sorted(selected)
        else:
            payload = response.get(f"{layer}_response")
            if isinstance(payload, Mapping):
                for name, value in payload.items():
                    if value is not None:
                        values[(item_id, reference_id, None, f"{layer}.{name}")] = value
    return values


def _uncertain(value: Any, field: str) -> bool:
    if field == "identification.decision_type":
        return value == "uncertain"
    if field == "uncertainty":
        return value in {"material", "unresolved"}
    return False


def _subject_comparison(
    subject_type: str,
    subject_id: str,
    values: Mapping[tuple[str, str, str | None, str], Any],
    references: Mapping[tuple[str, str | None, str], Mapping[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    summary = Counter()
    for key in sorted(
        values,
        key=lambda value: tuple("" if part is None else str(part) for part in value),
    ):
        item_id, reference_id, unit_id, field = key
        value = values[key]
        reference = references.get((reference_id, unit_id, field))
        notes: list[str] = []
        if field in QUALITATIVE_FIELDS:
            status = "not_comparable"
            alignment = "not_comparable"
            reference_value = reference.get("value") if reference else None
            authority = reference.get("authority") if reference else None
            notes.append("free-text field is reserved for qualitative adjudication review")
        elif reference is None or field not in REFERENCE_FIELDS.get(field.split(".", 1)[0], set()):
            status = "unavailable"
            alignment = "unavailable"
            reference_value = None
            authority = None
            notes.append("no accepted or reviewable reference field is available")
        else:
            status = "available"
            reference_value = reference["value"]
            authority = reference["authority"]
            alignment = "aligned" if _equal(value, reference_value) else "divergent"
            notes.append("alignment is diagnostic and does not establish correctness")
        summary[alignment] += 1
        rows.append(
            {
                "item_id": item_id,
                "reference_id": reference_id,
                "unit_id": unit_id,
                "field": field,
                "subject_value": value,
                "reference_status": status,
                "reference_value": reference_value,
                "alignment": alignment,
                "reference_authority": authority,
                "notes": notes,
            }
        )
    return {
        "subject_type": subject_type,
        "subject_id": subject_id,
        "comparisons": rows,
        "summary": {
            name: summary[name]
            for name in ("aligned", "divergent", "unavailable", "not_comparable")
        },
    }


def _pattern(
    left_value: Any,
    right_value: Any,
    field: str,
    reference: Mapping[str, Any] | None,
) -> tuple[str, bool, str]:
    if _uncertain(left_value, field) != _uncertain(right_value, field):
        return (
            "uncertain_vs_confident",
            True,
            "One coder preserved uncertainty while the other selected a non-uncertain value; neither is presumed correct.",
        )
    if reference is None:
        return (
            "reference_unavailable",
            not _equal(left_value, right_value),
            "No accepted or reviewable reference field is available; coder agreement or disagreement remains independently reviewable.",
        )
    reference_value = reference["value"]
    left_match = _equal(left_value, reference_value)
    right_match = _equal(right_value, reference_value)
    if _equal(left_value, right_value):
        if left_match:
            return (
                "both_with_reference",
                False,
                "Both coders align with the reference, which is corroborative but not self-validating.",
            )
        return (
            "both_against_reference",
            True,
            "Both coders share a value different from the reference; the reference and shared coding both require adjudicative consideration.",
        )
    if left_match or right_match:
        return (
            "split_with_reference",
            True,
            "The coders split and one aligns with the reference; alignment alone does not decide the disagreement.",
        )
    return (
        "split_against_both",
        True,
        "The coders split and neither aligns with the reference; all three positions remain candidates for review.",
    )


def _patterns(
    coder_values: Sequence[
        tuple[str, Mapping[tuple[str, str, str | None, str], Any]]
    ],
    references: Mapping[tuple[str, str | None, str], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for (left_id, left), (right_id, right) in itertools.combinations(coder_values, 2):
        for key in sorted(
            set(left) & set(right),
            key=lambda value: tuple("" if part is None else str(part) for part in value),
        ):
            item_id, reference_id, unit_id, field = key
            left_value = left[key]
            right_value = right[key]
            reference = references.get((reference_id, unit_id, field))
            qualitative = field in QUALITATIVE_FIELDS
            pattern, recommend, interpretation = _pattern(
                left_value,
                right_value,
                field,
                None if qualitative else reference,
            )
            if qualitative:
                recommend = not _equal(left_value, right_value)
                interpretation = (
                    "Free-text values are retained for qualitative adjudication "
                    "and are not treated as reference accuracy categories."
                )
            digest = hashlib.sha256(
                f"{left_id}|{right_id}|{item_id}|{reference_id}|{unit_id}|{field}".encode()
            ).hexdigest()[:16]
            records.append(
                {
                    "pattern_id": f"reference-pattern-{digest}",
                    "left_coder_id": left_id,
                    "right_coder_id": right_id,
                    "item_id": item_id,
                    "reference_id": reference_id,
                    "unit_id": unit_id,
                    "field": field,
                    "pattern": pattern,
                    "left_value": left_value,
                    "right_value": right_value,
                    "reference_status": (
                        "not_comparable"
                        if qualitative
                        else ("available" if reference else "unavailable")
                    ),
                    "reference_value": reference.get("value") if reference else None,
                    "reference_authority": reference.get("authority") if reference else None,
                    "adjudication_recommended": recommend,
                    "neutral_interpretation": interpretation,
                }
            )
    return records


def compare_references(
    root: Path,
    case_id: str,
    normalized: Mapping[str, Any],
    cohort_id: str,
    cohort_version: str,
    *,
    adjudicated: Mapping[str, Any] | None = None,
    revision: str = "in-memory-comparison",
) -> dict[str, Any]:
    runs = [
        run
        for run in normalized.get("runs", [])
        if isinstance(run, Mapping)
        and run.get("cohort_id") == cohort_id
        and run.get("cohort_version") == cohort_version
    ]
    if len(runs) < 2:
        raise ReferenceComparisonError("at least two validated coder runs are required")
    metadata = _comparable_metadata(runs)
    if metadata["case_id"] != case_id:
        raise ReferenceComparisonError("normalized runs do not match requested case")
    references, reference_sources = load_references(
        root, case_id, metadata["task_layer"]
    )
    coder_values = [
        (str(_submission(run)["coder_id"]), _human_values(_submission(run)))
        for run in runs
    ]
    coder_comparisons = [
        _subject_comparison("coder", coder_id, values, references)
        for coder_id, values in coder_values
    ]
    pattern_records = _patterns(coder_values, references)
    adjudicated_comparisons: list[dict[str, Any]] = []
    if adjudicated is not None:
        if (
            adjudicated.get("cohort_id") != cohort_id
            or adjudicated.get("cohort_version") != cohort_version
            or not isinstance(adjudicated.get("responses"), list)
        ):
            raise ReferenceComparisonError(
                "adjudicated result does not match cohort or lacks responses"
            )
        adjudicated_comparisons.append(
            _subject_comparison(
                "adjudicated",
                str(adjudicated.get("adjudication_id") or ""),
                _human_values(
                    {
                        "task_layer": metadata["task_layer"],
                        "responses": adjudicated["responses"],
                    }
                ),
                references,
            )
        )
    return {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "cohort_id": cohort_id,
        "cohort_version": cohort_version,
        "source_language": metadata["source_language"],
        "task_layer": metadata["task_layer"],
        "packet_id": metadata["packet_id"],
        "generator": {
            "script": GENERATOR_PATH,
            "version": GENERATOR_VERSION,
            "script_hash": sha256_bytes(Path(__file__).read_bytes()),
            "code_revision": revision,
        },
        "input_runs": sorted(
            [
                {
                    "registration_id": str(run.get("registration_id") or ""),
                    "raw_hash": str(run.get("raw_hash") or ""),
                    "submission_id": str(_submission(run).get("submission_id") or ""),
                    "coder_id": str(_submission(run).get("coder_id") or ""),
                }
                for run in runs
            ],
            key=lambda value: value["coder_id"],
        ),
        "reference_sources": reference_sources,
        "coder_comparisons": coder_comparisons,
        "pattern_records": pattern_records,
        "pattern_summary": dict(
            sorted(Counter(row["pattern"] for row in pattern_records).items())
        ),
        "adjudicated_comparisons": adjudicated_comparisons,
    }


def write_pattern_csv(path: Path, result: Mapping[str, Any]) -> None:
    fields = [
        "pattern_id", "left_coder_id", "right_coder_id", "item_id",
        "reference_id", "unit_id", "field", "pattern", "left_value", "right_value",
        "reference_status", "reference_value", "reference_authority",
        "adjudication_recommended", "neutral_interpretation",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in result["pattern_records"]:
            writer.writerow(
                {
                    **row,
                    "left_value": _canonical(row["left_value"]),
                    "right_value": _canonical(row["right_value"]),
                    "reference_value": _canonical(row["reference_value"]),
                }
            )


def compute_case_reference_comparison(
    root: Path,
    case_id: str,
    cohort_id: str,
    cohort_version: str,
    *,
    adjudicated_path: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    for label, value in (
        ("case_id", case_id),
        ("cohort_id", cohort_id),
        ("cohort_version", cohort_version),
    ):
        if not SAFE_COMPONENT.fullmatch(value):
            raise ReferenceComparisonError(f"unsafe {label} `{value}`")
    case_root = root / "cases" / case_id
    normalized = read_json_object(
        case_root
        / "quality"
        / "human-reliability"
        / "normalized"
        / "normalized-coder-runs.json"
    )
    normalized_schema = read_json_object(
        root / "schemas" / "human-reliability" / "normalized-coder-runs-schema.json"
    )
    normalized_errors = sorted(
        Draft202012Validator(
            normalized_schema, format_checker=FormatChecker()
        ).iter_errors(normalized),
        key=lambda error: list(error.absolute_path),
    )
    if normalized_errors:
        raise ReferenceComparisonError(
            "normalized coder runs fail schema validation: "
            + "; ".join(error.message for error in normalized_errors)
        )
    relevant_runs = [
        run
        for run in normalized.get("runs", [])
        if isinstance(run, Mapping)
        and run.get("cohort_id") == cohort_id
        and run.get("cohort_version") == cohort_version
    ]
    try:
        _verify_raw_registrations(root, case_root, relevant_runs)
        cohort_path = _cohort_manifest_path(case_root, cohort_id, cohort_version)
        cohort = load_cohort_context(root, case_id, cohort_path)
    except (AgreementError, IngestionError) as exc:
        raise ReferenceComparisonError(str(exc)) from exc
    submission_schema = read_json_object(
        root / "schemas" / "human-reliability" / "submission-schema.json"
    )
    contextual_errors: list[str] = []
    for run in relevant_runs:
        contextual_errors.extend(
            validate_submission(
                _submission(run),
                cohort.validation_context,
                schema=submission_schema,
                vocabularies=_vocabularies(root),
            )
        )
    if contextual_errors:
        raise ReferenceComparisonError(
            "normalized submissions fail cohort validation: "
            + "; ".join(dict.fromkeys(contextual_errors))
        )
    status = read_json_object(
        case_root / "quality" / "human-reliability" / "ingestion-status.json"
    )
    status_schema = read_json_object(
        root / "schemas" / "human-reliability" / "ingestion-status-schema.json"
    )
    status_errors = sorted(
        Draft202012Validator(status_schema).iter_errors(status),
        key=lambda error: list(error.absolute_path),
    )
    if status_errors:
        raise ReferenceComparisonError(
            "ingestion status fails schema validation: "
            + "; ".join(error.message for error in status_errors)
        )
    cohort_status = next(
        (
            value
            for value in status.get("cohorts", [])
            if isinstance(value, Mapping)
            and value.get("cohort_id") == cohort_id
            and value.get("cohort_version") == cohort_version
        ),
        None,
    )
    if not isinstance(cohort_status, Mapping) or cohort_status.get("state") != "complete":
        raise ReferenceComparisonError(
            "cohort ingestion must be `complete` before reference comparison"
        )
    normalized_coders = {
        str(_submission(run).get("coder_id") or "") for run in relevant_runs
    }
    if normalized_coders != set(cohort_status.get("valid_primary_coders", [])):
        raise ReferenceComparisonError(
            "normalized coder IDs do not match completed ingestion status"
        )
    if len(relevant_runs) != cohort_status.get("valid_submission_count"):
        raise ReferenceComparisonError(
            "normalized run count does not match completed ingestion status"
        )
    adjudicated = read_json_object(adjudicated_path) if adjudicated_path else None
    result = compare_references(
        root,
        case_id,
        normalized,
        cohort_id,
        cohort_version,
        adjudicated=adjudicated,
        revision=code_revision(root),
    )
    schema = read_json_object(
        root / "schemas" / "human-reliability" / "reference-comparison-schema.json"
    )
    errors = sorted(
        Draft202012Validator(schema).iter_errors(result),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        raise ReferenceComparisonError(
            "reference comparison fails schema validation: "
            + "; ".join(error.message for error in errors)
        )
    output_root = (
        f"quality/human-reliability/comparisons/"
        f"{cohort_id}-{cohort_version}"
    )
    write_json(
        safe_output_path(case_root, f"{output_root}/reference-comparison.json"),
        result,
    )
    write_pattern_csv(
        safe_output_path(case_root, f"{output_root}/reference-patterns.csv"),
        result,
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument("--cohort", dest="cohort_id", required=True)
    parser.add_argument("--cohort-version", required=True)
    parser.add_argument("--adjudicated", type=Path)
    args = parser.parse_args()
    try:
        result = compute_case_reference_comparison(
            ROOT,
            args.case_id,
            args.cohort_id,
            args.cohort_version,
            adjudicated_path=args.adjudicated,
        )
    except ReferenceComparisonError as exc:
        parser.error(str(exc))
    print(
        f"{args.case_id}: wrote {len(result['pattern_records'])} "
        f"reference pattern record(s) for {result['cohort_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
