#!/usr/bin/env python3
"""Generate a deterministic human review queue from classified disagreements."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from scripts.model_reliability.compare_runs import (
        read_json_object,
        safe_output_path,
        write_json,
    )
except ModuleNotFoundError:  # Direct execution from scripts/model_reliability/.
    from compare_runs import read_json_object, safe_output_path, write_json  # type: ignore


GENERATOR_PATH = "scripts/model_reliability/generate_review_queue.py"
DISAGREEMENT_GENERATOR = "scripts/model_reliability/classify_disagreements.py"
PRIORITY_WEIGHT = {"high": 300, "medium": 200, "low": 100}


class ReviewQueueError(ValueError):
    """Raised when queue inputs are stale, malformed, or unsafe."""


def read_json_lines(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ReviewQueueError(f"{path}:{line_number}: expected an object")
            records.append(value)
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewQueueError(f"{path}: unable to read JSONL: {exc}") from exc
    return records


def packet_context(case_root: Path) -> dict[str, Mapping[str, Any]]:
    packet_root = case_root / "quality" / "model-reliability" / "packets"
    index: dict[str, Mapping[str, Any]] = {}
    for path in sorted(packet_root.glob("*-packet.jsonl")):
        for item in read_json_lines(path):
            item_id = item.get("item_id")
            if isinstance(item_id, str):
                index[item_id] = item
    return index


def validation_context(case_root: Path) -> dict[str, Mapping[str, Any]]:
    report_root = (
        case_root
        / "quality"
        / "model-reliability"
        / "normalized"
        / "validation-reports"
    )
    index: dict[str, Mapping[str, Any]] = {}
    for path in sorted(report_root.glob("*.json")):
        report = read_json_object(path)
        for result in report.get("item_results", []):
            if not isinstance(result, Mapping):
                continue
            raw_item = result.get("raw_item")
            if not isinstance(raw_item, Mapping):
                continue
            item_id = raw_item.get("item_id")
            if isinstance(item_id, str):
                index.setdefault(item_id, raw_item)
    return index


def segmented_context(case_root: Path) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for path in sorted((case_root / "corpus" / "segmented").glob("*.json")):
        data = read_json_object(path)
        for section in data.get("sections", []):
            if not isinstance(section, Mapping):
                continue
            for paragraph in section.get("paragraphs", []):
                if not isinstance(paragraph, Mapping):
                    continue
                for sentence in paragraph.get("sentences", []):
                    if not isinstance(sentence, Mapping):
                        continue
                    sentence_id = sentence.get("sentence_id")
                    if isinstance(sentence_id, str):
                        index[sentence_id] = {
                            "source_text": str(sentence.get("text", "")),
                            "gloss_en": str(sentence.get("gloss_en", "")),
                        }
    return index


def document_rights(case_root: Path) -> dict[str, dict[str, Any]]:
    path = case_root / "metadata" / "document-manifest.json"
    if not path.exists():
        return {}
    manifest = read_json_object(path)
    rights: dict[str, dict[str, Any]] = {}
    for document in manifest.get("documents", []):
        if not isinstance(document, Mapping):
            continue
        document_id = document.get("document_id")
        if not isinstance(document_id, str):
            continue
        rights[document_id] = {
            "rights_status": str(document.get("rights_status", "unknown")),
            "storage_policy": str(document.get("storage_policy", "unspecified")),
            "risk_flags": sorted(
                str(flag) for flag in document.get("risk_flags", [])
            ),
        }
    return rights


def claim_traces(root: Path, case_id: str) -> list[Mapping[str, Any]]:
    candidates = [
        root / "publication" / "audit" / "claim-traceability.json",
        root / "cases" / case_id / "quality" / "claim-traceability.json",
    ]
    traces: list[Mapping[str, Any]] = []
    for path in candidates:
        if not path.exists():
            continue
        data = read_json_object(path)
        for trace in data.get("traces", []):
            if isinstance(trace, Mapping) and trace.get("case_id") == case_id:
                traces.append(trace)
    return traces


def trace_matches(
    disagreement: Mapping[str, Any], traces: Iterable[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    unit_id = disagreement.get("unit_id")
    sentence_id = disagreement.get("sentence_id")
    document_id = disagreement.get("document_id")
    cluster_id = disagreement.get("cluster_id")
    matched: dict[str, dict[str, Any]] = {}
    for trace in traces:
        reasons: list[str] = []
        mipvu_ids = trace.get("mipvu_ids")
        if unit_id and isinstance(mipvu_ids, list) and unit_id in mipvu_ids:
            reasons.append("unit_id")
        if sentence_id and trace.get("sentence_id") == sentence_id:
            reasons.append("sentence_id")
        if cluster_id and trace.get("cluster_id") == cluster_id:
            reasons.append("cluster_id")
        if document_id and trace.get("document_id") == document_id:
            reasons.append("document_id")
        if not reasons or reasons == ["document_id"]:
            continue
        claim_id = trace.get("claim_id")
        if not isinstance(claim_id, str):
            continue
        entry = matched.setdefault(
            claim_id,
            {
                "claim_id": claim_id,
                "claim_text": str(trace.get("claim_text", "")),
                "claim_status": str(trace.get("claim_status", "")),
                "support_dimension": str(trace.get("support_dimension", "")),
                "match_reasons": [],
            },
        )
        entry["match_reasons"] = sorted(
            set(entry["match_reasons"]) | set(reasons)
        )
    return [matched[claim_id] for claim_id in sorted(matched)]


def cross_case_impacts(disagreement: Mapping[str, Any]) -> list[str]:
    category = disagreement.get("category")
    field = str(disagreement.get("field", ""))
    impacts: set[str] = set()
    if category in {
        "metaphor-identification-instability",
        "boundary-instability",
    }:
        impacts.add("cross-case:metaphor-presence")
    if category in {
        "domain-instability",
        "target-domain-instability",
        "cluster-instability",
    }:
        impacts.add("cross-case:metaphor-mapping")
    if "sacrificial_body" in field or "sacred_object" in field:
        impacts.add("cross-case:sacrifice")
    if "purification" in field:
        impacts.add("cross-case:purification")
    if "obligatory_frame" in field:
        impacts.add("cross-case:obligation")
    if category == "agency-absence-instability":
        impacts.add("cross-case:agency-absence")
    if category in {"context-instability", "reference-challenge"}:
        impacts.add("cross-case:language-or-reference")
    if category in {"hallucination-instability", "schema-instability"}:
        impacts.add("pipeline:input-integrity")
    return sorted(impacts)


def focal_text(context: Mapping[str, Any], unit_id: str) -> str:
    for lexical_unit in context.get("lexical_units", []):
        if not isinstance(lexical_unit, Mapping):
            continue
        if lexical_unit.get("lexical_unit_id") == unit_id:
            return str(lexical_unit.get("source_text", ""))
        if lexical_unit.get("span_id") == unit_id:
            return str(lexical_unit.get("source_text", ""))
    return ""


def priority(
    disagreement: Mapping[str, Any],
    affected_claims: list[Mapping[str, Any]],
    cross_case: list[str],
) -> tuple[str, int, list[str]]:
    base = str(disagreement.get("review_priority", "low"))
    reasons = [f"classified-{base}-priority"]
    score = PRIORITY_WEIGHT.get(base, 0)
    if disagreement.get("unanimous_reference_challenge"):
        score += 80
        reasons.append("unanimous-reference-challenge")
    if affected_claims:
        score += 60
        reasons.append("claim-audit-impact")
    if cross_case:
        score += 100
        reasons.append("cross-case-impact")
    if disagreement.get("category") in {
        "metaphor-identification-instability",
        "violence-instability",
        "obligation-instability",
        "agency-absence-instability",
    }:
        score += 30
        reasons.append("methodologically-sensitive-field")
    if disagreement.get("possible_codebook_ambiguity"):
        score += 20
        reasons.append("possible-codebook-ambiguity")
    derived = "high" if score >= 300 else "medium" if score >= 200 else "low"
    return derived, score, reasons


def build_queue(
    root: Path,
    case_id: str,
    disagreement_log: Mapping[str, Any],
) -> dict[str, Any]:
    if disagreement_log.get("case_id") != case_id:
        raise ReviewQueueError("disagreement log case_id does not match requested case")
    if disagreement_log.get("generator") != DISAGREEMENT_GENERATOR:
        raise ReviewQueueError(
            "disagreement-log.json was not produced by the classification stage"
        )
    disagreements = disagreement_log.get("disagreements")
    if not isinstance(disagreements, list):
        raise ReviewQueueError("disagreement log has no disagreements array")
    if not all(isinstance(record, Mapping) for record in disagreements):
        raise ReviewQueueError("disagreement log contains a non-object record")
    run_ids = disagreement_log.get("run_ids")
    if (
        not isinstance(run_ids, list)
        or len(run_ids) < 2
        or not all(isinstance(run_id, str) and run_id for run_id in run_ids)
        or len(run_ids) != len(set(run_ids))
    ):
        raise ReviewQueueError("disagreement log has invalid run_ids")
    summary = disagreement_log.get("summary")
    if not isinstance(summary, Mapping) or summary.get("total_disagreements") != len(
        disagreements
    ):
        raise ReviewQueueError(
            "disagreement log summary does not reconcile with disagreement records"
        )
    disagreement_ids = [
        record.get("disagreement_id")
        for record in disagreements
    ]
    if (
        not all(
            isinstance(disagreement_id, str) and disagreement_id
            for disagreement_id in disagreement_ids
        )
        or len(disagreement_ids) != len(set(disagreement_ids))
    ):
        raise ReviewQueueError("disagreement log contains duplicate disagreement IDs")
    case_root = root / "cases" / case_id
    packets = packet_context(case_root)
    rejected_items = validation_context(case_root)
    sentences = segmented_context(case_root)
    rights = document_rights(case_root)
    traces = claim_traces(root, case_id)
    entries: list[dict[str, Any]] = []
    for disagreement in disagreements:
        if not isinstance(disagreement, Mapping):
            continue
        item_id = str(disagreement.get("item_id", ""))
        unit_id = str(disagreement.get("unit_id", ""))
        packet = packets.get(item_id) or rejected_items.get(item_id, {})
        document_id = str(
            disagreement.get("document_id") or packet.get("document_id") or ""
        )
        sentence_id = str(
            disagreement.get("sentence_id") or packet.get("sentence_id") or ""
        )
        fallback = sentences.get(sentence_id, {})
        enriched_disagreement = {
            **disagreement,
            "document_id": document_id,
            "sentence_id": sentence_id,
        }
        affected_claims = trace_matches(enriched_disagreement, traces)
        cross_case = cross_case_impacts(disagreement)
        queue_priority, score, reasons = priority(
            disagreement, affected_claims, cross_case
        )
        document_rights_record = rights.get(
            document_id,
            {
                "rights_status": "unknown",
                "storage_policy": "unspecified",
                "risk_flags": [],
            },
        )
        entries.append(
            {
                "queue_id": "",
                "queue_rank": 0,
                "disagreement_id": disagreement.get("disagreement_id"),
                "case_id": case_id,
                "source_language": (
                    disagreement.get("source_language")
                    or packet.get("source_language")
                    or ""
                ),
                "document_id": document_id,
                "sentence_id": sentence_id,
                "item_id": item_id,
                "unit_id": unit_id,
                "cluster_id": disagreement.get("cluster_id"),
                "task_layer": disagreement.get("task_layer"),
                "field": disagreement.get("field"),
                "category": disagreement.get("category"),
                "agreement_pattern": disagreement.get("agreement_pattern"),
                "source_text": str(
                    packet.get("sentence_source_text")
                    or fallback.get("source_text", "")
                ),
                "gloss_en": str(
                    packet.get("sentence_gloss_en")
                    or fallback.get("gloss_en", "")
                ),
                "focal_text": focal_text(packet, unit_id),
                "source_risk_flags": sorted(
                    {
                        *(str(flag) for flag in packet.get("source_risk_flags", [])),
                        *document_rights_record["risk_flags"],
                    }
                ),
                "rights_status": document_rights_record["rights_status"],
                "storage_policy": document_rights_record["storage_policy"],
                "reference_value": disagreement.get("reference_value"),
                "model_values": disagreement.get("run_values", {}),
                "value_groups": disagreement.get("value_groups", []),
                "missing_run_ids": disagreement.get("missing_run_ids", []),
                "affected_claims": affected_claims,
                "cross_case_impacts": cross_case,
                "priority": queue_priority,
                "priority_score": score,
                "priority_reasons": reasons,
                "review_question": disagreement.get("review_question"),
                "review_status": "pending-human-review",
                "decision_authority": "human-only",
                "adjudication_note": (
                    "Model agreement and majority patterns are diagnostic only; "
                    "this queue contains no adjudication decision."
                ),
            }
        )
    entries.sort(
        key=lambda entry: (
            -entry["priority_score"],
            entry["case_id"],
            entry["document_id"],
            entry["sentence_id"],
            entry["field"],
            entry["disagreement_id"],
        )
    )
    for rank, entry in enumerate(entries, start=1):
        entry["queue_rank"] = rank
        entry["queue_id"] = f"review-{rank:04d}"
    return {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "generator": GENERATOR_PATH,
        "source_disagreement_generator": disagreement_log.get("generator"),
        "run_ids": disagreement_log.get("run_ids", []),
        "queue_policy": (
            "Deterministic human-review prioritization only. Model votes do not "
            "constitute adjudication and cannot update accepted annotations."
        ),
        "summary": {
            "queue_count": len(entries),
            "high_priority_count": sum(
                entry["priority"] == "high" for entry in entries
            ),
            "claim_linked_count": sum(
                bool(entry["affected_claims"]) for entry in entries
            ),
            "cross_case_impact_count": sum(
                bool(entry["cross_case_impacts"]) for entry in entries
            ),
        },
        "entries": entries,
    }


def write_queue_csv(path: Path, entries: Iterable[Mapping[str, Any]]) -> None:
    fields = [
        "queue_id",
        "queue_rank",
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
        "source_text",
        "gloss_en",
        "focal_text",
        "source_risk_flags",
        "rights_status",
        "storage_policy",
        "reference_value",
        "model_values",
        "value_groups",
        "missing_run_ids",
        "affected_claims",
        "cross_case_impacts",
        "priority",
        "priority_score",
        "priority_reasons",
        "review_question",
        "review_status",
        "decision_authority",
        "adjudication_note",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for entry in entries:
            row = dict(entry)
            for field in (
                "source_risk_flags",
                "reference_value",
                "model_values",
                "value_groups",
                "missing_run_ids",
                "affected_claims",
                "cross_case_impacts",
                "priority_reasons",
            ):
                row[field] = json.dumps(
                    entry.get(field), ensure_ascii=False, sort_keys=True
                )
            writer.writerow({field: row.get(field) for field in fields})


def generate_case_review_queue(root: Path, case_id: str) -> dict[str, Any]:
    root = root.resolve()
    case_root = root / "cases" / case_id
    if not case_root.is_dir():
        raise ReviewQueueError(f"unknown case `{case_id}`")
    disagreement_path = (
        case_root
        / "quality"
        / "model-reliability"
        / "comparisons"
        / "disagreement-log.json"
    )
    disagreement_log = read_json_object(disagreement_path)
    queue = build_queue(root, case_id, disagreement_log)
    json_path = safe_output_path(
        case_root, "quality/model-reliability/review-queue/model-review-queue.json"
    )
    csv_path = safe_output_path(
        case_root, "quality/model-reliability/review-queue/model-review-queue.csv"
    )
    write_json(json_path, queue)
    write_queue_csv(csv_path, queue["entries"])
    return queue


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    queue = generate_case_review_queue(args.root, args.case_id)
    print(f"Generated {queue['summary']['queue_count']} review queue item(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
