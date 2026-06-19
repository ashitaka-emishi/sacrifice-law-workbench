#!/usr/bin/env python3
"""Classify model disagreements and generate a stratified instability report."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:
    from scripts.model_reliability.compare_runs import (
        NUMERIC_FIELDS,
        SET_FIELDS,
        Observation,
        flatten_run,
        load_references,
        read_json_object,
        safe_output_path,
        write_json,
    )
except ModuleNotFoundError:  # Direct execution from scripts/model_reliability/.
    from compare_runs import (  # type: ignore[no-redef]
        NUMERIC_FIELDS,
        SET_FIELDS,
        Observation,
        flatten_run,
        load_references,
        read_json_object,
        safe_output_path,
        write_json,
    )


GENERATOR_PATH = "scripts/model_reliability/classify_disagreements.py"
CONFIDENCE_DIFFERENCE_THRESHOLD = 0.10


class DisagreementError(ValueError):
    """Raised when disagreement inputs are missing or inconsistent."""


def canonical_value(value: Any) -> str:
    if isinstance(value, list):
        value = sorted(
            value,
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True),
        )
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def canonical_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {canonical_value(item) for item in value}


def values_equal(field: str, left: Any, right: Any) -> bool:
    if field in SET_FIELDS:
        return canonical_set(left) == canonical_set(right)
    return left == right


def grouping_key(field: str, value: Any) -> str:
    if field in SET_FIELDS:
        return canonical_value(sorted(canonical_set(value)))
    return canonical_value(value)


def is_substantive(field: str, values: Sequence[Any]) -> bool:
    if len(values) < 2:
        return False
    if field in NUMERIC_FIELDS:
        numeric = [float(value) for value in values if isinstance(value, (int, float))]
        return bool(numeric) and max(numeric) - min(numeric) >= CONFIDENCE_DIFFERENCE_THRESHOLD
    first = values[0]
    return any(not values_equal(field, first, value) for value in values[1:])


def category_for_field(field: str) -> str:
    if field == "identification.decision":
        return "metaphor-identification-instability"
    if field in {
        "identification.boundary_decision",
        "identification.boundary_span",
    }:
        return "boundary-instability"
    if field in {
        "identification.basic_meaning",
        "identification.contrast_explanation",
    }:
        return "semantic-instability"
    if field in {
        "identification.contextual_meaning",
        "identification.comparison_basis",
    }:
        return "context-instability"
    if field in {
        "cmt.source_domain_primary",
        "cmt.source_domain_secondary",
    }:
        return "domain-instability"
    if field in {"cmt.conceptual_metaphor", "cmt.entailments"}:
        return "semantic-instability"
    if field == "cmt.target_domain":
        return "target-domain-instability"
    if field == "cmt.cluster_id":
        return "cluster-instability"
    if field == "interpretation.functions.violence_logic":
        return "violence-instability"
    if field == "interpretation.functions.obligatory_frame":
        return "obligation-instability"
    if field.startswith("interpretation.agency.") or field.startswith(
        "interpretation.absence."
    ):
        return "agency-absence-instability"
    if field.startswith("interpretation.functions."):
        return "semantic-instability"
    if field == "confidence":
        return "confidence-instability"
    if field == "uncertainty.status":
        return "context-instability"
    return "context-instability"


def priority_for(category: str, pattern: str) -> tuple[str, str, bool]:
    if pattern == "unanimous-reference-challenge":
        return "high", "high", True
    if pattern == "coverage-gap":
        return "medium", "medium", False
    if category in {"hallucination-instability", "schema-instability"}:
        return "high", "high", False
    if category in {
        "violence-instability",
        "obligation-instability",
        "agency-absence-instability",
        "metaphor-identification-instability",
    }:
        return "high", "high", True
    if category == "confidence-instability":
        return "low", "low", False
    if category == "boundary-instability":
        return "medium", "medium", True
    return "medium", "medium", True


def _observation_index(
    flattened: Sequence[tuple[str, Sequence[Observation]]],
) -> tuple[
    dict[tuple[str, str], dict[str, Observation]],
    dict[str, dict[str, Any]],
]:
    by_key: dict[tuple[str, str], dict[str, Observation]] = defaultdict(dict)
    unit_context: dict[str, dict[str, Any]] = defaultdict(dict)
    for run_id, observations in flattened:
        for observation in observations:
            by_key[observation.key][run_id] = observation
            if observation.field == "cmt.cluster_id":
                unit_context[observation.unit_id][run_id] = observation.value
    return by_key, unit_context


def _reference_index(
    references: Sequence[Observation],
) -> dict[tuple[str, str], Observation]:
    return {observation.key: observation for observation in references}


def _common_cluster(
    unit_id: str,
    unit_context: Mapping[str, Mapping[str, Any]],
    reference_index: Mapping[tuple[str, str], Observation],
) -> str | None:
    values = list(unit_context.get(unit_id, {}).values())
    reference = reference_index.get((unit_id, "cmt.cluster_id"))
    if reference is not None:
        values.append(reference.value)
    canonical = {canonical_value(value): value for value in values if value}
    return str(next(iter(canonical.values()))) if len(canonical) == 1 else None


def _agreement_pattern(
    field: str,
    model_values: Sequence[Any],
    reference: Observation | None,
    expected_run_count: int,
) -> tuple[str | None, bool]:
    if len(model_values) < expected_run_count:
        return "coverage-gap", False
    model_disagreement = is_substantive(field, model_values)
    if model_disagreement:
        group_sizes = Counter(
            grouping_key(field, value) for value in model_values
        ).values()
        if expected_run_count == 2:
            return "two-way-split", False
        if max(group_sizes) > 1:
            return "majority-minority-split", False
        return "multi-way-split", False
    if (
        reference is not None
        and model_values
        and is_substantive(field, [model_values[0], reference.value])
    ):
        return "unanimous-reference-challenge", True
    return None, False


def value_groups(
    field: str, run_values: Mapping[str, Any]
) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for run_id, value in run_values.items():
        key = grouping_key(field, value)
        group = groups.setdefault(key, {"value": value, "run_ids": []})
        group["run_ids"].append(run_id)
    return [
        {
            "value": group["value"],
            "run_ids": sorted(group["run_ids"]),
            "run_count": len(group["run_ids"]),
        }
        for _, group in sorted(groups.items())
    ]


def classify_value_disagreements(
    case_id: str,
    flattened: Sequence[tuple[str, Sequence[Observation]]],
    references: Sequence[Observation],
) -> list[dict[str, Any]]:
    run_ids = sorted(run_id for run_id, _ in flattened)
    by_key, unit_context = _observation_index(flattened)
    reference_index = _reference_index(references)
    disagreements: list[dict[str, Any]] = []
    for (unit_id, field), observations in sorted(by_key.items()):
        ordered = [observations[run_id] for run_id in run_ids if run_id in observations]
        values = [observation.value for observation in ordered]
        reference = reference_index.get((unit_id, field))
        pattern, reference_challenge = _agreement_pattern(
            field, values, reference, len(run_ids)
        )
        if pattern is None:
            continue
        representative = ordered[0]
        category = (
            "reference-challenge"
            if reference_challenge
            else category_for_field(field)
        )
        review_priority, claim_impact, codebook_ambiguity = priority_for(
            category, pattern
        )
        run_values = {
            run_id: observations[run_id].value
            for run_id in run_ids
            if run_id in observations
        }
        disagreements.append(
            {
                "disagreement_id": f"disagreement-{len(disagreements) + 1:04d}",
                "case_id": case_id,
                "source_language": representative.source_language,
                "document_id": representative.document_id,
                "sentence_id": representative.sentence_id,
                "item_id": representative.item_id,
                "unit_id": unit_id,
                "cluster_id": _common_cluster(
                    unit_id, unit_context, reference_index
                ),
                "task_layer": representative.task_layer,
                "field": field,
                "category": category,
                "agreement_pattern": pattern,
                "run_values": run_values,
                "value_groups": value_groups(field, run_values),
                "missing_run_ids": [
                    run_id for run_id in run_ids if run_id not in observations
                ],
                "reference_value": reference.value if reference is not None else None,
                "unanimous_reference_challenge": reference_challenge,
                "possible_codebook_ambiguity": codebook_ambiguity,
                "claim_impact": claim_impact,
                "review_priority": review_priority,
                "review_question": review_question(
                    category, pattern, field, unit_id
                ),
                "evidence_source": "normalized-runs",
            }
        )
    return disagreements


def review_question(category: str, pattern: str, field: str, unit_id: str) -> str:
    if pattern == "unanimous-reference-challenge":
        return (
            f"Do the unanimous model values for `{field}` on `{unit_id}` expose "
            "a reference error, a codebook ambiguity, or shared model bias?"
        )
    if category == "hallucination-instability":
        return (
            f"Did the rejected submission invent or misalign an identifier for "
            f"`{unit_id}`?"
        )
    if category == "schema-instability":
        return (
            f"Does the rejected value for `{unit_id}` indicate unclear submission "
            "instructions or a model-format failure?"
        )
    if pattern == "coverage-gap":
        return (
            f"Why did one or more runs omit `{field}` for `{unit_id}`, and is the "
            "packet or submission guidance incomplete?"
        )
    return (
        f"Which value for `{field}` on `{unit_id}` best follows the codebook and "
        "source context?"
    )


def _error_category(error: str) -> str:
    lowered = error.lower()
    if "unknown" in lowered and " id" in lowered:
        return "hallucination-instability"
    return "schema-instability"


def classify_validation_reports(
    case_root: Path,
    start_index: int,
) -> list[dict[str, Any]]:
    report_root = (
        case_root
        / "quality"
        / "model-reliability"
        / "normalized"
        / "validation-reports"
    )
    records: list[dict[str, Any]] = []
    for path in sorted(report_root.glob("*.json")):
        report = read_json_object(path)
        if report.get("status") != "invalid":
            continue
        item_results = report.get("item_results")
        raw_by_error: list[tuple[str, Mapping[str, Any] | None]] = []
        if isinstance(item_results, list):
            for item_result in item_results:
                if not isinstance(item_result, Mapping):
                    continue
                raw_item = item_result.get("raw_item")
                raw_mapping = raw_item if isinstance(raw_item, Mapping) else None
                errors = item_result.get("errors")
                if isinstance(errors, list):
                    raw_by_error.extend(
                        (str(error), raw_mapping) for error in errors if error
                    )
        covered = {error for error, _ in raw_by_error}
        for error in report.get("errors", []):
            if error not in covered:
                raw_by_error.append((str(error), None))
        for error, raw_item in raw_by_error:
            category = _error_category(error)
            priority, impact, ambiguity = priority_for(
                category, "invalid-submission"
            )
            unit_id = (
                str(raw_item.get("item_id"))
                if raw_item and raw_item.get("item_id")
                else str(report.get("registration_id"))
            )
            records.append(
                {
                    "disagreement_id": (
                        f"disagreement-{start_index + len(records):04d}"
                    ),
                    "case_id": str(report.get("case_id", "")),
                    "source_language": (
                        str(raw_item.get("source_language", ""))
                        if raw_item
                        else ""
                    ),
                    "document_id": (
                        str(raw_item.get("document_id", "")) if raw_item else ""
                    ),
                    "sentence_id": (
                        str(raw_item.get("sentence_id", "")) if raw_item else ""
                    ),
                    "item_id": (
                        str(raw_item.get("item_id", "")) if raw_item else ""
                    ),
                    "unit_id": unit_id,
                    "cluster_id": None,
                    "task_layer": (
                        str(raw_item.get("task_layer", "submission"))
                        if raw_item
                        else "submission"
                    ),
                    "field": error.split(":", 1)[0],
                    "category": category,
                    "agreement_pattern": (
                        "hallucinated-identifier"
                        if category == "hallucination-instability"
                        else "invalid-submission"
                    ),
                    "run_values": {
                        str(report.get("run_id") or report.get("registration_id")): error
                    },
                    "value_groups": [
                        {
                            "value": error,
                            "run_ids": [
                                str(
                                    report.get("run_id")
                                    or report.get("registration_id")
                                )
                            ],
                            "run_count": 1,
                        }
                    ],
                    "missing_run_ids": [],
                    "reference_value": None,
                    "unanimous_reference_challenge": False,
                    "possible_codebook_ambiguity": ambiguity,
                    "claim_impact": impact,
                    "review_priority": priority,
                    "review_question": review_question(
                        category, "invalid-submission", error, unit_id
                    ),
                    "evidence_source": "validation-report",
                }
            )
    return records


def _count_by(
    records: Sequence[Mapping[str, Any]], field: str
) -> list[dict[str, Any]]:
    counter = Counter(
        str(record.get(field) or "unassigned") for record in records
    )
    return [
        {field: value, "disagreement_count": count}
        for value, count in sorted(counter.items())
    ]


def build_summary(
    case_id: str,
    run_ids: Sequence[str],
    disagreements: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "total_disagreements": len(disagreements),
        "unanimous_reference_challenges": sum(
            bool(record.get("unanimous_reference_challenge"))
            for record in disagreements
        ),
        "high_priority_count": sum(
            record.get("review_priority") == "high" for record in disagreements
        ),
        "possible_codebook_ambiguity_count": sum(
            bool(record.get("possible_codebook_ambiguity"))
            for record in disagreements
        ),
        "by_case": [{"case_id": case_id, "disagreement_count": len(disagreements)}],
        "by_language": _count_by(disagreements, "source_language"),
        "by_document": _count_by(disagreements, "document_id"),
        "by_cluster": _count_by(disagreements, "cluster_id"),
        "by_layer": _count_by(disagreements, "task_layer"),
        "by_category": _count_by(disagreements, "category"),
        "by_priority": _count_by(disagreements, "review_priority"),
        "run_ids": sorted(run_ids),
    }


def classify_case_disagreements(
    root: Path,
    case_id: str,
    normalized: Mapping[str, Any],
    agreement: Mapping[str, Any],
) -> dict[str, Any]:
    if normalized.get("case_id") != case_id or agreement.get("case_id") != case_id:
        raise DisagreementError("normalized runs and agreement results must match the case")
    if agreement.get("generator") != "scripts/model_reliability/compare_runs.py":
        raise DisagreementError(
            "agreement-results.json was not produced by the comparison stage"
        )
    raw_runs = normalized.get("runs")
    if not isinstance(raw_runs, list) or len(raw_runs) < 2:
        raise DisagreementError("at least two normalized runs are required")
    flattened = [
        flatten_run(run, case_id) for run in raw_runs if isinstance(run, Mapping)
    ]
    run_ids = sorted(run_id for run_id, _ in flattened)
    if sorted(agreement.get("run_ids", [])) != run_ids:
        raise DisagreementError(
            "agreement-results.json run_ids do not match normalized-runs.json"
        )
    references = load_references(root, case_id)
    disagreements = classify_value_disagreements(case_id, flattened, references)
    case_root = root / "cases" / case_id
    disagreements.extend(
        classify_validation_reports(case_root, len(disagreements) + 1)
    )
    return {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "generator": GENERATOR_PATH,
        "agreement_generator": agreement.get("generator"),
        "run_ids": run_ids,
        "summary": build_summary(case_id, run_ids, disagreements),
        "disagreements": disagreements,
    }


def write_disagreement_csv(
    path: Path, disagreements: Iterable[Mapping[str, Any]]
) -> None:
    fields = [
        "disagreement_id",
        "case_id",
        "source_language",
        "document_id",
        "sentence_id",
        "item_id",
        "unit_id",
        "cluster_id",
        "task_layer",
        "field",
        "category",
        "agreement_pattern",
        "run_values",
        "value_groups",
        "missing_run_ids",
        "reference_value",
        "unanimous_reference_challenge",
        "possible_codebook_ambiguity",
        "claim_impact",
        "review_priority",
        "review_question",
        "evidence_source",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for record in disagreements:
            writer.writerow(
                {
                    **{field: record.get(field) for field in fields},
                    "run_values": json.dumps(
                        record.get("run_values"), ensure_ascii=False, sort_keys=True
                    ),
                    "value_groups": json.dumps(
                        record.get("value_groups"),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "missing_run_ids": json.dumps(record.get("missing_run_ids")),
                    "reference_value": json.dumps(
                        record.get("reference_value"),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                }
            )


def _summary_table(rows: Sequence[Mapping[str, Any]], key: str) -> list[str]:
    return [
        f"| `{row[key]}` | {row['disagreement_count']} |"
        for row in rows
    ]


def render_instability_report(result: Mapping[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        f"# Model Instability Report: {result['case_id']}",
        "",
        "> Diagnostic stress-test output only. Model agreement does not validate "
        "an interpretation or alter accepted annotations.",
        "",
        f"- Compared runs: {len(result['run_ids'])}",
        f"- Substantive disagreements: {summary['total_disagreements']}",
        (
            "- Unanimous model challenges to the accepted reference: "
            f"{summary['unanimous_reference_challenges']}"
        ),
        f"- High-priority human review items: {summary['high_priority_count']}",
        (
            "- Possible codebook ambiguities: "
            f"{summary['possible_codebook_ambiguity_count']}"
        ),
        "",
    ]
    for heading, key, field in (
        ("Layer instability", "by_layer", "task_layer"),
        ("Category instability", "by_category", "category"),
        ("Document instability", "by_document", "document_id"),
        ("Cluster instability", "by_cluster", "cluster_id"),
        ("Language instability", "by_language", "source_language"),
    ):
        lines.extend([f"## {heading}", "", f"| {field} | disagreements |", "|---|---:|"])
        lines.extend(_summary_table(summary[key], field))
        lines.append("")
    lines.extend(["## Human-review priorities", ""])
    high_priority = [
        record
        for record in result["disagreements"]
        if record["review_priority"] == "high"
    ]
    if not high_priority:
        lines.append("- No high-priority disagreements.")
    else:
        for record in high_priority:
            lines.append(
                f"- `{record['disagreement_id']}` — **{record['category']}** "
                f"on `{record['unit_id']}`: {record['review_question']}"
            )
    lines.extend(
        [
            "",
            "## Interpretation limits",
            "",
            "- Consensus may reflect shared model bias.",
            "- Reference challenges require human source and codebook review.",
            "- Invalid submissions remain visible but are not pooled with valid-run metrics.",
            "",
        ]
    )
    return "\n".join(lines)


def compute_case_disagreements(root: Path, case_id: str) -> dict[str, Any]:
    root = root.resolve()
    case_root = root / "cases" / case_id
    if not case_root.is_dir():
        raise DisagreementError(f"unknown case `{case_id}`")
    model_root = case_root / "quality" / "model-reliability"
    normalized = read_json_object(
        model_root / "normalized" / "normalized-runs.json"
    )
    agreement = read_json_object(
        model_root / "comparisons" / "agreement-results.json"
    )
    result = classify_case_disagreements(root, case_id, normalized, agreement)
    comparison_root = "quality/model-reliability/comparisons"
    json_path = safe_output_path(
        case_root, f"{comparison_root}/disagreement-log.json"
    )
    csv_path = safe_output_path(
        case_root, f"{comparison_root}/disagreement-log.csv"
    )
    report_path = safe_output_path(
        case_root, f"{comparison_root}/instability-report.md"
    )
    write_json(json_path, result)
    write_disagreement_csv(csv_path, result["disagreements"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_instability_report(result), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    result = compute_case_disagreements(args.root, args.case_id)
    print(
        f"Classified {result['summary']['total_disagreements']} disagreement(s) "
        f"for {args.case_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
