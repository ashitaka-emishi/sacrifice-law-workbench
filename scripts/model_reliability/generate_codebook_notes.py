#!/usr/bin/env python3
"""Generate human-governed codebook revision notes from model instability."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from scripts.model_reliability.compare_runs import (
        read_json_object,
        safe_output_path,
        write_json,
    )
except ModuleNotFoundError:
    try:
        from model_reliability.compare_runs import (
            read_json_object,
            safe_output_path,
            write_json,
        )
    except ModuleNotFoundError:
        from compare_runs import read_json_object, safe_output_path, write_json  # type: ignore


GENERATOR_PATH = "scripts/model_reliability/generate_codebook_notes.py"
AGREEMENT_GENERATOR = "scripts/model_reliability/compare_runs.py"
DISAGREEMENT_GENERATOR = "scripts/model_reliability/classify_disagreements.py"
QUEUE_GENERATOR = "scripts/model_reliability/generate_review_queue.py"
DISPOSITIONS = {"accepted", "rejected", "deferred"}


class CodebookNotesError(ValueError):
    """Raised when revision-note inputs or human decisions are inconsistent."""


def _stable_findings(agreement: Mapping[str, Any]) -> list[dict[str, Any]]:
    families = agreement.get("comparison_families")
    model_family = (
        families.get("model_vs_model")
        if isinstance(families, Mapping)
        else None
    )
    pairs = model_family.get("pairs") if isinstance(model_family, Mapping) else []
    stable: dict[tuple[str, str, str], dict[str, Any]] = {}
    unstable: set[tuple[str, str, str]] = set()
    for pair in pairs if isinstance(pairs, list) else []:
        summaries = pair.get("summaries") if isinstance(pair, Mapping) else []
        for summary in summaries if isinstance(summaries, list) else []:
            if not isinstance(summary, Mapping) or summary.get("document_id") is not None:
                continue
            key = (
                str(summary.get("source_language", "")),
                str(summary.get("task_layer", "")),
                str(summary.get("field", "")),
            )
            metric = summary.get("metric")
            if not isinstance(metric, Mapping) or metric.get("status") != "defined":
                continue
            value = metric.get("value")
            name = metric.get("name")
            perfect = value == (0 if name == "mean_absolute_difference" else 1)
            if not perfect:
                unstable.add(key)
                stable.pop(key, None)
                continue
            if key not in unstable:
                stable[key] = {
                    "source_language": key[0],
                    "task_layer": key[1],
                    "field": key[2],
                    "comparable_count": int(summary.get("comparable_count", 0)),
                    "metric_name": str(name),
                    "metric_value": value,
                }
    return [stable[key] for key in sorted(stable)]


def _recommendation_text(category: str, field: str) -> str:
    if category == "hallucination-instability":
        return "Add an explicit identifier-copying check and a worked valid-ID example."
    if category == "schema-instability":
        return "Clarify the required output shape and add a format-only calibration exercise."
    if category == "boundary-instability":
        return "Add boundary inclusion/exclusion examples and an edge-case calibration item."
    if category == "metaphor-identification-instability":
        return "Clarify the MIPVU decision rule with contrasting positive and negative examples."
    if category in {"domain-instability", "target-domain-instability", "cluster-instability"}:
        return "Clarify domain and cluster distinctions with contrastive mapping examples."
    if category in {"violence-instability", "obligation-instability", "agency-absence-instability"}:
        return "Add a decision tree and calibration examples for the interpretive distinction."
    if category == "reference-challenge":
        return "Review the reference and codebook wording independently; do not adopt the model value by vote."
    if category == "confidence-instability":
        return "Add confidence anchors and examples for adjacent confidence levels."
    return f"Clarify the decision rule for `{field}` with contrastive examples."


def _has_multilingual_risk(entries: Sequence[Mapping[str, Any]]) -> bool:
    languages = {str(entry.get("source_language", "")) for entry in entries}
    risk_flags = {
        str(flag)
        for entry in entries
        for flag in entry.get("source_risk_flags", [])
    }
    return any(language and language != "en" for language in languages) or bool(
        risk_flags
        & {
            "translation-check",
            "translation-risk",
            "ocr-risk",
            "transcription-risk",
        }
    )


def _candidate_findings(queue: Mapping[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[Mapping[str, Any]]] = {}
    entries = queue.get("entries")
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, Mapping):
            continue
        key = (
            str(entry.get("source_language", "")),
            str(entry.get("task_layer", "")),
            str(entry.get("field", "")),
            str(entry.get("category", "")),
        )
        grouped.setdefault(key, []).append(entry)
    findings: list[dict[str, Any]] = []
    for key in sorted(grouped):
        values = grouped[key]
        category = key[3]
        base = {
            "source_language": key[0],
            "task_layer": key[1],
            "field": key[2],
            "categories": [category],
            "disagreement_ids": sorted(
                str(entry.get("disagreement_id")) for entry in values
            ),
            "queue_ids": sorted(str(entry.get("queue_id")) for entry in values),
            "evidence_count": len(values),
            "observation": (
                f"{len(values)} queued `{category}` item(s) affect "
                f"`{key[2]}` in `{key[0] or 'unspecified'}`."
            ),
            "recommended_change": _recommendation_text(category, key[2]),
            "training_use": (
                "Use the reviewed examples as a contrastive calibration set; "
                "retain source language and uncertainty notes."
            ),
        }
        findings.append(
            {
                "finding_type": (
                    "common-model-error"
                    if category
                    in {"hallucination-instability", "schema-instability"}
                    else "ambiguous-instruction"
                ),
                **base,
            }
        )
        if _has_multilingual_risk(values):
            findings.append(
                {
                    "finding_type": "multilingual-problem",
                    **base,
                    "observation": (
                        f"The `{key[2]}` instability occurs in source language "
                        f"`{key[0] or 'unspecified'}` or carries a language/source "
                        "risk flag."
                    ),
                    "recommended_change": (
                        "Add source-language calibration examples and require "
                        "review of gloss, translation, OCR, or transcription risk."
                    ),
                }
            )
    return findings


def _decisions(path: Path | None, case_id: str) -> dict[str, Mapping[str, Any]]:
    if path is None or not path.exists():
        return {}
    value = read_json_object(path)
    if value.get("schema_version") != "1.0.0":
        raise CodebookNotesError("decision register has an unsupported schema_version")
    if value.get("case_id") != case_id:
        raise CodebookNotesError("decision register case_id does not match requested case")
    if value.get("decision_authority") != "human-only":
        raise CodebookNotesError("decision register must declare human-only authority")
    decisions = value.get("decisions")
    if not isinstance(decisions, list):
        raise CodebookNotesError("decision register has no decisions array")
    result: dict[str, Mapping[str, Any]] = {}
    for decision in decisions:
        if not isinstance(decision, Mapping):
            raise CodebookNotesError("decision register contains a non-object decision")
        recommendation_id = decision.get("recommendation_id")
        disposition = decision.get("disposition")
        if not isinstance(recommendation_id, str) or not recommendation_id:
            raise CodebookNotesError("decision is missing recommendation_id")
        if recommendation_id in result:
            raise CodebookNotesError(f"duplicate decision for `{recommendation_id}`")
        if disposition not in DISPOSITIONS:
            raise CodebookNotesError(f"invalid disposition for `{recommendation_id}`")
        if disposition in {"accepted", "rejected"} and (
            not decision.get("reviewer")
            or not decision.get("rationale")
            or not decision.get("decided_at")
        ):
            raise CodebookNotesError(
                f"`{recommendation_id}` requires reviewer, rationale, and decided_at"
            )
        result[recommendation_id] = decision
    return result


def _recommendation_id(case_id: str, finding: Mapping[str, Any]) -> str:
    identity = json.dumps(
        {
            "case_id": case_id,
            "finding_type": finding["finding_type"],
            "source_language": finding["source_language"],
            "task_layer": finding["task_layer"],
            "field": finding["field"],
            "categories": finding["categories"],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "codebook-rec-" + hashlib.sha256(identity).hexdigest()[:12]


def build_codebook_notes(
    case_id: str,
    agreement: Mapping[str, Any],
    disagreement_log: Mapping[str, Any],
    queue: Mapping[str, Any],
    decisions: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if any(
        value.get("case_id") != case_id
        for value in (agreement, disagreement_log, queue)
    ):
        raise CodebookNotesError("all source artifacts must match the requested case")
    if agreement.get("generator") != AGREEMENT_GENERATOR:
        raise CodebookNotesError("agreement artifact has an untrusted generator")
    if disagreement_log.get("generator") != DISAGREEMENT_GENERATOR:
        raise CodebookNotesError("disagreement artifact has an untrusted generator")
    if queue.get("generator") != QUEUE_GENERATOR:
        raise CodebookNotesError("review queue has an untrusted generator")
    run_ids = sorted(str(run_id) for run_id in agreement.get("run_ids", []))
    if run_ids != sorted(disagreement_log.get("run_ids", [])) or run_ids != sorted(
        queue.get("run_ids", [])
    ):
        raise CodebookNotesError("source artifact run_ids do not match")

    findings: list[dict[str, Any]] = []
    for stable in _stable_findings(agreement):
        findings.append(
            {
                "finding_type": "stable-category",
                **stable,
                "categories": [],
                "disagreement_ids": [],
                "queue_ids": [],
                "evidence_count": stable["comparable_count"],
                "observation": (
                    f"All defined model-pair diagnostics were stable for "
                    f"`{stable['field']}`."
                ),
                "recommended_change": (
                    "Retain the current rule for now and preserve this field as "
                    "a positive calibration example."
                ),
                "training_use": (
                    "Use as a stable positive example, while preserving the "
                    "original source and task context."
                ),
            }
        )
    findings.extend(_candidate_findings(queue))
    findings.sort(
        key=lambda item: (
            item["finding_type"],
            item["source_language"],
            item["task_layer"],
            item["field"],
            ",".join(item["categories"]),
        )
    )
    decisions = decisions or {}
    recommendations: list[dict[str, Any]] = []
    for finding in findings:
        recommendation_id = _recommendation_id(case_id, finding)
        decision = decisions.get(recommendation_id)
        recommendations.append(
            {
                "recommendation_id": recommendation_id,
                "case_id": case_id,
                **finding,
                "disposition": (
                    str(decision.get("disposition")) if decision else "deferred"
                ),
                "decision_rationale": (
                    str(decision.get("rationale"))
                    if decision
                    else "Awaiting explicit human review."
                ),
                "reviewer": (
                    str(decision.get("reviewer"))
                    if decision and decision.get("reviewer")
                    else None
                ),
                "decided_at": (
                    str(decision.get("decided_at"))
                    if decision and decision.get("decided_at")
                    else None
                ),
                "decision_source": (
                    "human-decision-register" if decision else "generated-default"
                ),
            }
        )
    unknown = sorted(
        set(decisions)
        - {item["recommendation_id"] for item in recommendations}
    )
    if unknown:
        raise CodebookNotesError(
            "decision register references unknown recommendation(s): "
            + ", ".join(unknown)
        )
    disposition_counts = Counter(item["disposition"] for item in recommendations)
    type_counts = Counter(item["finding_type"] for item in recommendations)
    return {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "generator": GENERATOR_PATH,
        "source_generators": {
            "agreement": AGREEMENT_GENERATOR,
            "disagreements": DISAGREEMENT_GENERATOR,
            "review_queue": QUEUE_GENERATOR,
        },
        "run_ids": run_ids,
        "authority": {
            "decision_authority": "human-only",
            "retroactive_change_permitted": False,
            "notice": (
                "Recommendations document training and codebook proposals only. "
                "They do not alter accepted annotations or adjudicate queue items."
            ),
        },
        "summary": {
            "recommendation_count": len(recommendations),
            "accepted_count": disposition_counts["accepted"],
            "rejected_count": disposition_counts["rejected"],
            "deferred_count": disposition_counts["deferred"],
            "stable_category_count": type_counts["stable-category"],
            "ambiguous_instruction_count": type_counts["ambiguous-instruction"],
            "common_model_error_count": type_counts["common-model-error"],
            "multilingual_problem_count": type_counts["multilingual-problem"],
        },
        "recommendations": recommendations,
    }


def render_codebook_notes(notes: Mapping[str, Any]) -> str:
    sections: list[str] = []
    recommendations = notes.get("recommendations", [])
    for disposition in ("accepted", "rejected", "deferred"):
        entries = [
            entry
            for entry in recommendations
            if isinstance(entry, Mapping) and entry.get("disposition") == disposition
        ]
        lines = [f"## {disposition.title()} recommendations", ""]
        if not entries:
            lines.append("None.")
        for entry in entries:
            lines.extend(
                [
                    f"### `{entry['recommendation_id']}` — `{entry['field']}`",
                    "",
                    f"- Finding: `{entry['finding_type']}`",
                    f"- Layer / language: `{entry['task_layer']}` / `{entry['source_language'] or 'unspecified'}`",
                    f"- Observation: {entry['observation']}",
                    f"- Proposed change: {entry['recommended_change']}",
                    f"- Training/calibration use: {entry['training_use']}",
                    f"- Human decision rationale: {entry['decision_rationale']}",
                    f"- Reviewer: `{entry['reviewer'] or 'not assigned'}`",
                    "",
                ]
            )
        sections.append("\n".join(lines))
    summary = notes["summary"]
    return f"""# Codebook Revision Notes: {notes['case_id']}

> Human-governed methodological notes only. Model agreement is not evidence,
> these recommendations do not adjudicate review items, and no entry changes an
> accepted annotation retroactively.

## Summary

| Recommendations | Accepted | Rejected | Deferred | Stable categories | Ambiguous instructions | Common model errors | Multilingual problems |
|---:|---:|---:|---:|---:|---:|---:|---:|
| {summary['recommendation_count']} | {summary['accepted_count']} | {summary['rejected_count']} | {summary['deferred_count']} | {summary['stable_category_count']} | {summary['ambiguous_instruction_count']} | {summary['common_model_error_count']} | {summary['multilingual_problem_count']} |

All generated recommendations default to **deferred**. Accepted and rejected
statuses require an explicit human decision register with a reviewer and
rationale. Accepted recommendations authorize a future codebook-edit workflow;
they do not themselves edit the codebook or prior decisions.

{chr(10).join(sections)}
"""


def generate_case_codebook_notes(
    root: Path,
    case_id: str,
) -> dict[str, Any]:
    root = root.resolve()
    case_root = root / "cases" / case_id
    if not case_root.is_dir():
        raise CodebookNotesError(f"unknown case `{case_id}`")
    model_root = case_root / "quality" / "model-reliability"
    agreement = read_json_object(model_root / "comparisons" / "agreement-results.json")
    disagreement_log = read_json_object(
        model_root / "comparisons" / "disagreement-log.json"
    )
    queue = read_json_object(model_root / "review-queue" / "model-review-queue.json")
    default_decisions = model_root / "codebook" / "recommendation-decisions.json"
    decisions = _decisions(default_decisions, case_id)
    notes = build_codebook_notes(
        case_id, agreement, disagreement_log, queue, decisions
    )
    json_path = safe_output_path(
        case_root, "quality/model-reliability/codebook/codebook-revision-notes.json"
    )
    markdown_path = safe_output_path(
        case_root, "quality/model-reliability/codebook/codebook-revision-notes.md"
    )
    write_json(json_path, notes)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_codebook_notes(notes), encoding="utf-8")
    return notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    notes = generate_case_codebook_notes(args.root, args.case_id)
    print(
        f"Generated {notes['summary']['recommendation_count']} codebook "
        "recommendation(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
