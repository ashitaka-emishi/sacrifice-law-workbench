#!/usr/bin/env python3
"""Generate a consensus and instability report from reliability diagnostics."""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:
    from scripts.model_reliability.compare_runs import (
        read_json_object,
        safe_output_path,
        write_json,
    )
except ModuleNotFoundError:  # Direct execution from scripts/model_reliability/.
    from compare_runs import read_json_object, safe_output_path, write_json  # type: ignore


GENERATOR_PATH = "scripts/model_reliability/generate_consensus_report.py"
AGREEMENT_GENERATOR = "scripts/model_reliability/compare_runs.py"
DISAGREEMENT_GENERATOR = "scripts/model_reliability/classify_disagreements.py"
QUEUE_GENERATOR = "scripts/model_reliability/generate_review_queue.py"
DIAGNOSTIC_NOTICE = (
    "Multi-model consensus is a diagnostic stress-test result, not scholarly "
    "evidence, validation, or authority to alter accepted annotations."
)


class ConsensusReportError(ValueError):
    """Raised when report inputs are stale, malformed, or inconsistent."""


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConsensusReportError(f"{label} must be an object")
    return value


def _require_records(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not all(
        isinstance(record, Mapping) for record in value
    ):
        raise ConsensusReportError(f"{label} must be an array of objects")
    return list(value)


def _run_ids(artifact: Mapping[str, Any], label: str) -> list[str]:
    run_ids = artifact.get("run_ids")
    if (
        not isinstance(run_ids, list)
        or len(run_ids) < 2
        or not all(isinstance(run_id, str) and run_id for run_id in run_ids)
        or len(run_ids) != len(set(run_ids))
    ):
        raise ConsensusReportError(f"{label} has invalid run_ids")
    return sorted(run_ids)


def _aggregate_summaries(
    agreement: Mapping[str, Any], family: str
) -> list[Mapping[str, Any]]:
    families = _require_mapping(
        agreement.get("comparison_families"), "agreement comparison_families"
    )
    selected = _require_mapping(families.get(family), f"agreement {family}")
    container_key = "pairs" if family == "model_vs_model" else "runs"
    containers = _require_records(
        selected.get(container_key), f"agreement {family}.{container_key}"
    )
    summaries: list[Mapping[str, Any]] = []
    for container in containers:
        rows = _require_records(
            container.get("summaries"), f"agreement {family} summaries"
        )
        summaries.extend(row for row in rows if row.get("document_id") is None)
    return summaries


def _metric_value(summary: Mapping[str, Any]) -> float | None:
    metric = _require_mapping(summary.get("metric"), "agreement metric")
    if metric.get("status") != "defined":
        return None
    value = metric.get("value")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ConsensusReportError("defined agreement metric has no numeric value")
    return float(value)


def _group_summaries(
    summaries: Iterable[Mapping[str, Any]],
) -> dict[tuple[str, str, str], list[Mapping[str, Any]]]:
    groups: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for summary in summaries:
        key = (
            str(summary.get("source_language", "")),
            str(summary.get("task_layer", "")),
            str(summary.get("field", "")),
        )
        if not all(key):
            raise ConsensusReportError("agreement summary is missing a grouping field")
        groups[key].append(summary)
    return dict(groups)


def model_stability(
    case_id: str, summaries: Iterable[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for (language, layer, field), rows in sorted(
        _group_summaries(summaries).items()
    ):
        values = [
            value for row in rows if (value := _metric_value(row)) is not None
        ]
        if not values:
            status = "insufficient-data"
        elif all(value == 1.0 for value in values):
            status = "stable"
        else:
            status = "unstable"
        results.append(
            {
                "case_id": case_id,
                "source_language": language,
                "task_layer": layer,
                "field": field,
                "status": status,
                "pair_count": len(rows),
                "defined_pair_count": len(values),
                "comparable_count": sum(
                    int(row.get("comparable_count", 0)) for row in rows
                ),
                "minimum_agreement": min(values) if values else None,
                "maximum_agreement": max(values) if values else None,
            }
        )
    return results


def reference_diagnostics(
    case_id: str,
    summaries: Iterable[Mapping[str, Any]],
    disagreements: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    challenge_counts: dict[tuple[str, str], int] = defaultdict(int)
    for disagreement in disagreements:
        if disagreement.get("unanimous_reference_challenge"):
            challenge_counts[
                (
                    str(disagreement.get("task_layer", "")),
                    str(disagreement.get("field", "")),
                )
            ] += 1
    results: list[dict[str, Any]] = []
    for (language, layer, field), rows in sorted(
        _group_summaries(summaries).items()
    ):
        values = [
            value for row in rows if (value := _metric_value(row)) is not None
        ]
        challenge_count = challenge_counts[(layer, field)]
        if challenge_count:
            status = "challenged-reference"
        elif not values:
            status = "insufficient-data"
        elif all(value == 1.0 for value in values):
            status = "supports-reference"
        elif all(value < 1.0 for value in values):
            status = "diverges-from-reference"
        else:
            status = "mixed-reference-alignment"
        results.append(
            {
                "case_id": case_id,
                "source_language": language,
                "task_layer": layer,
                "field": field,
                "status": status,
                "run_count": len(rows),
                "defined_run_count": len(values),
                "comparable_count": sum(
                    int(row.get("comparable_count", 0)) for row in rows
                ),
                "exact_match_count": sum(
                    int(row.get("exact_match_count", 0)) for row in rows
                ),
                "minimum_agreement": min(values) if values else None,
                "maximum_agreement": max(values) if values else None,
                "unanimous_reference_challenge_count": challenge_count,
            }
        )
    return results


def _risk_rollup(
    disagreements: Sequence[Mapping[str, Any]],
    queue_entries: Sequence[Mapping[str, Any]],
    field: str,
) -> list[dict[str, Any]]:
    counts: dict[str, dict[str, Any]] = {}
    for disagreement in disagreements:
        value = str(disagreement.get(field) or "unassigned")
        row = counts.setdefault(
            value,
            {
                field: value,
                "disagreement_count": 0,
                "unanimous_reference_challenge_count": 0,
                "high_priority_review_count": 0,
            },
        )
        row["disagreement_count"] += 1
        row["unanimous_reference_challenge_count"] += int(
            bool(disagreement.get("unanimous_reference_challenge"))
        )
    for entry in queue_entries:
        value = str(entry.get(field) or "unassigned")
        row = counts.setdefault(
            value,
            {
                field: value,
                "disagreement_count": 0,
                "unanimous_reference_challenge_count": 0,
                "high_priority_review_count": 0,
            },
        )
        row["high_priority_review_count"] += int(entry.get("priority") == "high")
    return sorted(
        counts.values(),
        key=lambda row: (
            -row["high_priority_review_count"],
            -row["disagreement_count"],
            row[field],
        ),
    )


def review_priorities(
    entries: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    ordered = sorted(
        entries,
        key=lambda entry: (
            int(entry.get("queue_rank", 0)),
            str(entry.get("queue_id", "")),
        ),
    )
    return [
        {
            "queue_id": entry.get("queue_id"),
            "queue_rank": entry.get("queue_rank"),
            "priority": entry.get("priority"),
            "disagreement_id": entry.get("disagreement_id"),
            "document_id": entry.get("document_id"),
            "source_language": entry.get("source_language"),
            "cluster_id": entry.get("cluster_id"),
            "task_layer": entry.get("task_layer"),
            "field": entry.get("field"),
            "category": entry.get("category"),
            "review_question": entry.get("review_question"),
            "decision_authority": "human-only",
        }
        for entry in ordered
    ]


def build_consensus_report(
    case_id: str,
    agreement: Mapping[str, Any],
    disagreement_log: Mapping[str, Any],
    review_queue: Mapping[str, Any],
) -> dict[str, Any]:
    for label, artifact, generator in (
        ("agreement results", agreement, AGREEMENT_GENERATOR),
        ("disagreement log", disagreement_log, DISAGREEMENT_GENERATOR),
        ("review queue", review_queue, QUEUE_GENERATOR),
    ):
        if artifact.get("case_id") != case_id:
            raise ConsensusReportError(f"{label} case_id does not match requested case")
        if artifact.get("generator") != generator:
            raise ConsensusReportError(f"{label} has an untrusted generator")
    if disagreement_log.get("agreement_generator") != AGREEMENT_GENERATOR:
        raise ConsensusReportError(
            "disagreement log does not identify the trusted agreement generator"
        )
    if (
        review_queue.get("source_disagreement_generator")
        != DISAGREEMENT_GENERATOR
    ):
        raise ConsensusReportError(
            "review queue does not identify the trusted disagreement generator"
        )
    agreement_runs = _run_ids(agreement, "agreement results")
    if _run_ids(disagreement_log, "disagreement log") != agreement_runs:
        raise ConsensusReportError("disagreement log run_ids do not match agreement")
    if _run_ids(review_queue, "review queue") != agreement_runs:
        raise ConsensusReportError("review queue run_ids do not match agreement")

    disagreements = _require_records(
        disagreement_log.get("disagreements"), "disagreement log disagreements"
    )
    disagreement_summary = _require_mapping(
        disagreement_log.get("summary"), "disagreement log summary"
    )
    if disagreement_summary.get("total_disagreements") != len(disagreements):
        raise ConsensusReportError("disagreement summary does not reconcile")

    entries = _require_records(review_queue.get("entries"), "review queue entries")
    queue_summary = _require_mapping(review_queue.get("summary"), "review queue summary")
    if queue_summary.get("queue_count") != len(entries):
        raise ConsensusReportError("review queue summary does not reconcile")
    disagreement_id_list = [
        record.get("disagreement_id") for record in disagreements
    ]
    queued_id_list = [entry.get("disagreement_id") for entry in entries]
    if (
        not all(
            isinstance(identifier, str) and identifier
            for identifier in disagreement_id_list + queued_id_list
        )
        or len(disagreement_id_list) != len(set(disagreement_id_list))
        or len(queued_id_list) != len(set(queued_id_list))
    ):
        raise ConsensusReportError(
            "disagreement log or review queue has invalid disagreement IDs"
        )
    disagreement_ids = set(disagreement_id_list)
    queued_ids = set(queued_id_list)
    if disagreement_ids != queued_ids:
        raise ConsensusReportError(
            "review queue disagreement IDs do not match disagreement log"
        )

    stability = model_stability(
        case_id, _aggregate_summaries(agreement, "model_vs_model")
    )
    reference = reference_diagnostics(
        case_id,
        _aggregate_summaries(agreement, "model_vs_reference"),
        disagreements,
    )
    priorities = review_priorities(entries)
    return {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "generator": GENERATOR_PATH,
        "source_generators": {
            "agreement": agreement.get("generator"),
            "disagreements": disagreement_log.get("generator"),
            "review_queue": review_queue.get("generator"),
        },
        "run_ids": agreement_runs,
        "authority": {
            "consensus_is_evidence": False,
            "decision_authority": "human-only",
            "notice": DIAGNOSTIC_NOTICE,
        },
        "summary": {
            "field_count": len(stability),
            "stable_field_count": sum(
                row["status"] == "stable" for row in stability
            ),
            "unstable_field_count": sum(
                row["status"] == "unstable" for row in stability
            ),
            "insufficient_data_field_count": sum(
                row["status"] == "insufficient-data" for row in stability
            ),
            "reference_support_field_count": sum(
                row["status"] == "supports-reference" for row in reference
            ),
            "reference_divergence_field_count": sum(
                row["status"] == "diverges-from-reference" for row in reference
            ),
            "mixed_reference_alignment_field_count": sum(
                row["status"] == "mixed-reference-alignment" for row in reference
            ),
            "challenged_reference_field_count": sum(
                row["status"] == "challenged-reference" for row in reference
            ),
            "unanimous_reference_challenge_count": sum(
                int(row["unanimous_reference_challenge_count"])
                for row in reference
            ),
            "review_queue_count": len(priorities),
            "high_priority_review_count": sum(
                row["priority"] == "high" for row in priorities
            ),
        },
        "model_stability": stability,
        "reference_diagnostics": reference,
        "risk_dimensions": {
            "by_document": _risk_rollup(disagreements, entries, "document_id"),
            "by_cluster": _risk_rollup(disagreements, entries, "cluster_id"),
            "by_language": _risk_rollup(
                disagreements, entries, "source_language"
            ),
        },
        "review_priorities": priorities,
        "limitations": [
            "Consensus may reflect shared model bias or shared prompt effects.",
            "Reference support is diagnostic alignment, not independent evidence.",
            "Reference challenges require human source and codebook review.",
            "Undefined or sparse metrics are reported as insufficient data.",
            "Invalid submissions remain visible but are not pooled into agreement metrics.",
        ],
    }


def _field_table(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    lines = [
        "| layer | field | status | minimum | maximum | comparable |",
        "|---|---|---|---:|---:|---:|",
    ]
    for row in rows:
        minimum = (
            "—"
            if row["minimum_agreement"] is None
            else f"{row['minimum_agreement']:.3f}"
        )
        maximum = (
            "—"
            if row["maximum_agreement"] is None
            else f"{row['maximum_agreement']:.3f}"
        )
        lines.append(
            f"| `{row['task_layer']}` | `{row['field']}` | "
            f"{row['status']} | {minimum} | {maximum} | "
            f"{row['comparable_count']} |"
        )
    return lines


def render_consensus_report(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        f"# Multi-Model Consensus and Instability Report: {report['case_id']}",
        "",
        f"> {report['authority']['notice']}",
        "",
        f"- Compared runs: {len(report['run_ids'])}",
        f"- Stable model-to-model fields: {summary['stable_field_count']}",
        f"- Unstable model-to-model fields: {summary['unstable_field_count']}",
        (
            "- Fields with insufficient model-to-model data: "
            f"{summary['insufficient_data_field_count']}"
        ),
        f"- Fields supporting the reference: {summary['reference_support_field_count']}",
        (
            "- Fields diverging from the reference: "
            f"{summary['reference_divergence_field_count']}"
        ),
        (
            "- Unanimous model challenges to the reference: "
            f"{summary['unanimous_reference_challenge_count']}"
        ),
        f"- Pending human-review items: {summary['review_queue_count']}",
        "",
        "## Model-to-model field stability",
        "",
    ]
    lines.extend(_field_table(report["model_stability"]))
    lines.extend(["", "## Reference diagnostics", ""])
    lines.extend(_field_table(report["reference_diagnostics"]))
    for heading, key, field in (
        ("Document risk", "by_document", "document_id"),
        ("Cluster risk", "by_cluster", "cluster_id"),
        ("Language risk", "by_language", "source_language"),
    ):
        lines.extend(
            [
                "",
                f"## {heading}",
                "",
                f"| {field} | disagreements | unanimous challenges | high priority |",
                "|---|---:|---:|---:|",
            ]
        )
        for row in report["risk_dimensions"][key]:
            lines.append(
                f"| `{row[field]}` | {row['disagreement_count']} | "
                f"{row['unanimous_reference_challenge_count']} | "
                f"{row['high_priority_review_count']} |"
            )
    lines.extend(["", "## Human-review priorities", ""])
    if not report["review_priorities"]:
        lines.append("- No pending review items.")
    else:
        for row in report["review_priorities"]:
            lines.append(
                f"- `{row['queue_id']}` ({row['priority']}) — "
                f"`{row['task_layer']}` / `{row['field']}` / "
                f"`{row['document_id']}`: {row['review_question']}"
            )
    lines.extend(["", "## Interpretation limits", ""])
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    lines.extend(
        [
            "",
            "No count, metric, consensus pattern, or reference-alignment result in "
            "this report may update an accepted annotation without human review.",
            "",
        ]
    )
    return "\n".join(lines)


def generate_case_consensus_report(root: Path, case_id: str) -> dict[str, Any]:
    root = root.resolve()
    case_root = root / "cases" / case_id
    if not case_root.is_dir():
        raise ConsensusReportError(f"unknown case `{case_id}`")
    model_root = case_root / "quality" / "model-reliability"
    agreement = read_json_object(
        model_root / "comparisons" / "agreement-results.json"
    )
    disagreement_log = read_json_object(
        model_root / "comparisons" / "disagreement-log.json"
    )
    review_queue = read_json_object(
        model_root / "review-queue" / "model-review-queue.json"
    )
    report = build_consensus_report(
        case_id, agreement, disagreement_log, review_queue
    )
    json_path = safe_output_path(
        case_root, "quality/model-reliability/comparisons/consensus-report.json"
    )
    markdown_path = safe_output_path(
        case_root, "quality/model-reliability/comparisons/consensus-report.md"
    )
    write_json(json_path, report)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(
        render_consensus_report(report), encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    args = parser.parse_args()
    report = generate_case_consensus_report(args.root, args.case_id)
    print(
        f"Reported {report['summary']['field_count']} field(s) and "
        f"{report['summary']['review_queue_count']} review item(s) for "
        f"{args.case_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
