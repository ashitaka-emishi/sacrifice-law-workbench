#!/usr/bin/env python3
"""Generate a deterministic independent-adjudication queue for human coding."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

try:
    from scripts.human_reliability.boundaries import safe_output_path
    from scripts.human_reliability.compute_agreement import (
        SAFE_COMPONENT,
        _cohort_manifest_path,
        code_revision,
        read_json_object,
        sha256_bytes,
        write_json,
    )
    from scripts.human_reliability.generate_packets import canonical_json_bytes
    from scripts.human_reliability.ingest_submission import (
        IngestionError,
        load_cohort_context,
    )
except ModuleNotFoundError:
    from boundaries import safe_output_path  # type: ignore
    from compute_agreement import (  # type: ignore
        SAFE_COMPONENT,
        _cohort_manifest_path,
        code_revision,
        read_json_object,
        sha256_bytes,
        write_json,
    )
    from generate_packets import canonical_json_bytes  # type: ignore
    from ingest_submission import IngestionError, load_cohort_context  # type: ignore


ROOT = Path(__file__).resolve().parents[2]
GENERATOR_PATH = "scripts/human_reliability/generate_adjudication_queue.py"
GENERATOR_VERSION = "1.0.0"
DISAGREEMENT_GENERATOR = "scripts/human_reliability/classify_disagreements.py"
PRIORITY_WEIGHT = {"high": 300, "medium": 200, "low": 100}
MODEL_FIELD_ALIASES = {
    "identification.decision_type": {"identification.decision"},
    "identification.boundary_response": {"identification.boundary_decision"},
    "identification.selected_unit_boundary": {"identification.boundary_span"},
    "cmt.conceptual_mapping": {"cmt.conceptual_metaphor"},
    "interpretation.sacred_object": {"interpretation.functions.sacred_object"},
    "interpretation.sacrificial_body": {"interpretation.functions.sacrificial_body"},
    "interpretation.enemy_as_bringer_of_death": {
        "interpretation.functions.enemy_as_bringer_of_death"
    },
    "interpretation.violence_logic": {"interpretation.functions.violence_logic"},
    "interpretation.obligatory_frame": {"interpretation.functions.obligatory_frame"},
    "interpretation.purification": {"interpretation.functions.purification"},
    "interpretation.agents": {"interpretation.agency.agents"},
    "interpretation.patients": {"interpretation.agency.patients"},
    "interpretation.beneficiaries": {"interpretation.agency.beneficiaries"},
    "interpretation.excluded_agents": {"interpretation.agency.excluded_agents"},
    "interpretation.absence_decision": {"interpretation.absence.status"},
    "interpretation.presence_criterion": {"interpretation.absence.expected_presence"},
    "uncertainty": {"uncertainty.status"},
}
PRESENCE_FIELDS = {
    "identification.decision_type",
    "interpretation.sacred_object",
    "interpretation.sacrificial_body",
    "interpretation.enemy_as_bringer_of_death",
    "interpretation.violence_logic",
    "interpretation.obligatory_frame",
    "interpretation.purification",
    "interpretation.absence_decision",
}
PRESENCE_VALUES = {
    "present",
    "mipvu_indirect",
    "mipvu_direct",
    "mipvu_implicit",
    "mipvu_personification",
}


class AdjudicationQueueError(ValueError):
    """Raised when queue inputs are unsafe, stale, or inconsistent."""


def _validate(path: Path, schema_path: Path) -> dict[str, Any]:
    value = read_json_object(path)
    schema = read_json_object(schema_path)
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        raise AdjudicationQueueError(
            f"{path}: schema validation failed: "
            + "; ".join(error.message for error in errors)
        )
    return value


def _artifact_ref(root: Path, path: Path) -> dict[str, Any]:
    try:
        source = path.relative_to(root).as_posix()
    except ValueError:
        source = "coordinator://external-artifact"
    return {"source": source, "sha256": sha256_bytes(path.read_bytes())}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise AdjudicationQueueError(f"{path}: unable to read packet: {exc}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AdjudicationQueueError(
                f"{path}:{line_number}: invalid JSON: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise AdjudicationQueueError(f"{path}:{line_number}: expected an object")
        records.append(value)
    return records


def _packet_items(
    root: Path,
    case_root: Path,
    packet_manifest: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], Path]:
    payload = next(
        (
            value
            for value in packet_manifest.get("payloads", [])
            if isinstance(value, Mapping)
            and value.get("media_type") == "application/x-ndjson"
        ),
        None,
    )
    if not isinstance(payload, Mapping):
        raise AdjudicationQueueError("packet manifest lacks its JSONL packet payload")
    packet_path = (case_root / str(payload.get("path") or "")).resolve()
    try:
        packet_path.relative_to(case_root.resolve())
    except ValueError as exc:
        raise AdjudicationQueueError("packet payload escapes the case root") from exc
    if sha256_bytes(packet_path.read_bytes()) != payload.get("hash"):
        raise AdjudicationQueueError("packet payload hash is invalid")
    item_schema = read_json_object(
        root / "schemas" / "human-reliability" / "packet-item-schema.json"
    )
    validator = Draft202012Validator(item_schema)
    index: dict[str, Mapping[str, Any]] = {}
    for item in _read_jsonl(packet_path):
        errors = sorted(validator.iter_errors(item), key=lambda error: list(error.path))
        if errors:
            raise AdjudicationQueueError(
                f"{packet_path}: packet item schema failed: "
                + "; ".join(error.message for error in errors)
            )
        for field in ("packet_id", "case_id", "source_language", "task_layer"):
            if item.get(field) != packet_manifest.get(field):
                raise AdjudicationQueueError(
                    f"packet item differs from manifest on `{field}`"
                )
        item_id = str(item.get("item_id") or "")
        if not item_id or item_id in index:
            raise AdjudicationQueueError(f"packet contains duplicate item `{item_id}`")
        index[item_id] = item
    return index, packet_path


def _verify_packet_manifest(root: Path, packet: Mapping[str, Any]) -> None:
    generator = packet.get("generator")
    expected_script = "scripts/human_reliability/generate_packets.py"
    if not isinstance(generator, Mapping) or generator.get("script") != expected_script:
        raise AdjudicationQueueError("packet manifest has an unexpected generator")
    generator_path = root / expected_script
    if not generator_path.is_file():
        generator_path = ROOT / expected_script
    if generator.get("script_hash") != sha256_bytes(generator_path.read_bytes()):
        raise AdjudicationQueueError("packet manifest generator hash is stale")
    unsigned = {key: value for key, value in packet.items() if key != "packet_hash"}
    if packet.get("packet_hash") != sha256_bytes(canonical_json_bytes(unsigned)):
        raise AdjudicationQueueError("packet manifest self-hash is invalid")


def _verify_disagreement_generator(root: Path, log: Mapping[str, Any]) -> None:
    generator = log.get("generator")
    if not isinstance(generator, Mapping) or generator.get("script") != DISAGREEMENT_GENERATOR:
        raise AdjudicationQueueError("disagreement log has an unexpected generator")
    path = root / DISAGREEMENT_GENERATOR
    if not path.is_file():
        path = ROOT / DISAGREEMENT_GENERATOR
    if generator.get("script_hash") != sha256_bytes(path.read_bytes()):
        raise AdjudicationQueueError("disagreement log generator hash is stale")


def _focal_text(packet: Mapping[str, Any], unit_id: str | None) -> str:
    if not unit_id:
        return ""
    for unit in packet.get("lexical_units", []):
        if isinstance(unit, Mapping) and unit.get("lexical_unit_id") == unit_id:
            return str(unit.get("source_text") or "")
    return ""


def _claim_traces(root: Path, case_id: str) -> tuple[list[Mapping[str, Any]], Path | None]:
    candidates = (
        root / "cases" / case_id / "quality" / "claim-traceability.json",
        root / "publication" / "audit" / "claim-traceability.json",
    )
    for path in candidates:
        if not path.is_file():
            continue
        value = _validate(path, root / "schemas" / "claim-trace-schema.json")
        traces = [
            trace
            for trace in value.get("traces", [])
            if isinstance(trace, Mapping) and trace.get("case_id") == case_id
        ]
        return traces, path
    return [], None


def _affected_claims(
    disagreement: Mapping[str, Any], traces: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    matched: dict[str, dict[str, Any]] = {}
    for trace in traces:
        reasons: list[str] = []
        unit_id = disagreement.get("unit_id")
        sentence_id = disagreement.get("sentence_id")
        reference_id = disagreement.get("reference_id")
        if unit_id and unit_id in trace.get("mipvu_ids", []):
            reasons.append("unit_id")
        if sentence_id and trace.get("sentence_id") == sentence_id:
            reasons.append("sentence_id")
        if reference_id and trace.get("mapping_id") == reference_id:
            reasons.append("reference_id")
        if not reasons:
            continue
        claim_id = trace.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id:
            continue
        record = matched.setdefault(
            claim_id,
            {
                "claim_id": claim_id,
                "claim_text": str(trace.get("claim_text") or ""),
                "claim_status": str(trace.get("claim_status") or ""),
                "support_dimension": str(trace.get("support_dimension") or ""),
                "match_reasons": [],
            },
        )
        record["match_reasons"] = sorted(set(record["match_reasons"]) | set(reasons))
    return [matched[key] for key in sorted(matched)]


def affected_claim_dimensions(disagreement: Mapping[str, Any]) -> list[str]:
    field = str(disagreement.get("field") or "")
    category = disagreement.get("field_category")
    dimensions: set[str] = set()
    if category in {"identification", "boundary"}:
        dimensions.add("metaphor-presence")
    if category in {"semantics", "domains", "clusters"}:
        dimensions.add("metaphor-mapping")
    if "sacred_object" in field or "sacrificial_body" in field:
        dimensions.add("sacrifice")
    if "enemy_as_bringer_of_death" in field:
        dimensions.add("enemy-as-bringer-of-death")
    if "purification" in field:
        dimensions.add("purification")
    if "violence_logic" in field:
        dimensions.add("violence")
    if "obligatory_frame" in field:
        dimensions.add("obligation")
    if category == "agency_absence":
        dimensions.add("agency-absence")
    if disagreement.get("source_language_risk", {}).get("level") in {"material", "high"}:
        dimensions.add("source-language-interpretation")
    if disagreement.get("agreement_pattern") == "both_against_reference":
        dimensions.add("reference-validity")
    return sorted(dimensions)


def _presence_disagreement(disagreement: Mapping[str, Any]) -> bool:
    if disagreement.get("field") not in PRESENCE_FIELDS:
        return False
    return any(
        value.get("value") in PRESENCE_VALUES
        for value in disagreement.get("coder_values", [])
        if isinstance(value, Mapping)
    )


def priority(
    disagreement: Mapping[str, Any],
    affected_claims: Sequence[Mapping[str, Any]],
    dimensions: Sequence[str],
) -> tuple[str, int, list[str]]:
    upstream = str(disagreement.get("adjudication_priority") or "low")
    score = PRIORITY_WEIGHT.get(upstream, 0)
    reasons = [f"classified-{upstream}-priority"]
    pattern = disagreement.get("agreement_pattern")
    field = str(disagreement.get("field") or "")
    category = disagreement.get("field_category")
    claim_impact = disagreement.get("claim_impact")
    language_risk = disagreement.get("source_language_risk", {}).get("level")
    if pattern == "both_against_reference":
        score += 200
        reasons.append("both-against-reference")
    if claim_impact == "high":
        score += 200
        reasons.append("high-claim-impact")
    elif claim_impact == "moderate":
        score += 40
        reasons.append("moderate-claim-impact")
    if affected_claims:
        score += 80
        reasons.append("direct-claim-trace")
    if _presence_disagreement(disagreement):
        score += 140
        reasons.append("presence-disagreement")
    if category == "agency_absence":
        score += 140
        reasons.append("agency-absence")
    if "purification" in field:
        score += 140
        reasons.append("purification")
    if "violence_logic" in field:
        score += 140
        reasons.append("violence")
    if language_risk == "high":
        score += 90
        reasons.append("high-language-uncertainty")
    elif language_risk == "material":
        score += 60
        reasons.append("material-language-uncertainty")
    if pattern == "uncertain_vs_confident" or field == "uncertainty":
        score += 90
        reasons.append("language-uncertainty-split")
    if disagreement.get("possible_codebook_ambiguity"):
        score += 20
        reasons.append("possible-codebook-ambiguity")
    if dimensions and not affected_claims:
        score += 20
        reasons.append("affected-claim-dimension")
    derived = "high" if score >= 300 else "medium" if score >= 180 else "low"
    return derived, score, reasons


def _model_summary(
    disagreement: Mapping[str, Any],
    model_agreement: Mapping[str, Any] | None,
    source: str | None,
) -> dict[str, Any]:
    if model_agreement is None:
        return {
            "status": "unavailable",
            "source": None,
            "run_ids": [],
            "matching_summary_count": 0,
            "summaries": [],
            "note": "No validated model-reliability agreement artifact is available for this case.",
        }
    fields = {str(disagreement.get("field") or "")}
    fields.update(MODEL_FIELD_ALIASES.get(str(disagreement.get("field") or ""), set()))
    summaries: list[dict[str, Any]] = []
    families = model_agreement.get("comparison_families", {})
    for family_name in ("model_vs_model", "model_vs_reference"):
        family = families.get(family_name, {}) if isinstance(families, Mapping) else {}
        groups = family.get("pairs" if family_name == "model_vs_model" else "runs", [])
        for group in groups if isinstance(groups, list) else []:
            if not isinstance(group, Mapping):
                continue
            for summary in group.get("summaries", []):
                if not isinstance(summary, Mapping):
                    continue
                if summary.get("field") not in fields:
                    continue
                if summary.get("task_layer") != disagreement.get("task_layer"):
                    continue
                document_id = summary.get("document_id")
                if document_id not in {None, disagreement.get("document_id")}:
                    continue
                metric = summary.get("metric", {})
                summaries.append(
                    {
                        "comparison_family": family_name,
                        "left_id": str(summary.get("left_id") or ""),
                        "right_id": str(summary.get("right_id") or ""),
                        "field": str(summary.get("field") or ""),
                        "comparable_count": int(summary.get("comparable_count") or 0),
                        "exact_match_count": int(summary.get("exact_match_count") or 0),
                        "metric_name": str(metric.get("name") or "") if isinstance(metric, Mapping) else "",
                        "metric_status": str(metric.get("status") or "") if isinstance(metric, Mapping) else "",
                        "metric_value": metric.get("value") if isinstance(metric, Mapping) else None,
                    }
                )
    summaries.sort(key=lambda row: (row["comparison_family"], row["left_id"], row["right_id"], row["field"]))
    return {
        "status": "available" if summaries else "no_matching_summary",
        "source": source,
        "run_ids": sorted(str(value) for value in model_agreement.get("run_ids", [])),
        "matching_summary_count": len(summaries),
        "summaries": summaries,
        "note": (
            "Model summaries are diagnostic context only and do not vote in adjudication."
            if summaries
            else "A validated model artifact exists, but it has no matching field summary."
        ),
    }


def build_queue(
    disagreement_log: Mapping[str, Any],
    packet_items: Mapping[str, Mapping[str, Any]],
    *,
    claim_traces: Sequence[Mapping[str, Any]] = (),
    model_agreement: Mapping[str, Any] | None = None,
    model_source: str | None = None,
    storage_policy: str = "repository_allowed",
    revision: str = "in-memory-queue",
    input_artifacts: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    disagreements = disagreement_log.get("disagreements")
    if not isinstance(disagreements, list):
        raise AdjudicationQueueError("disagreement log lacks a disagreements array")
    if disagreement_log.get("summary", {}).get("total_disagreements") != len(disagreements):
        raise AdjudicationQueueError("disagreement summary does not reconcile with records")
    ids = [record.get("disagreement_id") for record in disagreements if isinstance(record, Mapping)]
    if len(ids) != len(disagreements) or len(ids) != len(set(ids)):
        raise AdjudicationQueueError("disagreement records have missing or duplicate IDs")
    entries: list[dict[str, Any]] = []
    for disagreement in disagreements:
        if not isinstance(disagreement, Mapping):
            continue
        item_id = str(disagreement.get("item_id") or "")
        packet = packet_items.get(item_id)
        if not isinstance(packet, Mapping):
            raise AdjudicationQueueError(f"queue item `{item_id}` is absent from the packet")
        for field in ("document_id", "sentence_id"):
            if packet.get(field) != disagreement.get(field):
                raise AdjudicationQueueError(
                    f"packet and disagreement differ on `{field}` for `{item_id}`"
                )
        enriched = {**disagreement, "task_layer": disagreement_log["task_layer"]}
        claims = _affected_claims(enriched, claim_traces)
        dimensions = affected_claim_dimensions(enriched)
        queue_priority, score, reasons = priority(enriched, claims, dimensions)
        disagreement_id = str(disagreement["disagreement_id"])
        digest = hashlib.sha256(disagreement_id.encode()).hexdigest()[:16]
        entries.append(
            {
                "queue_id": f"human-queue-{digest}",
                "queue_rank": 0,
                "disagreement_id": disagreement_id,
                "source_pattern_id": disagreement["source_pattern_id"],
                "case_id": disagreement_log["case_id"],
                "cohort_id": disagreement_log["cohort_id"],
                "cohort_version": disagreement_log["cohort_version"],
                "source_language": disagreement_log["source_language"],
                "task_layer": disagreement_log["task_layer"],
                "document_id": disagreement["document_id"],
                "sentence_id": disagreement["sentence_id"],
                "item_id": item_id,
                "reference_id": disagreement["reference_id"],
                "unit_id": disagreement.get("unit_id"),
                "field": disagreement["field"],
                "category": disagreement["category"],
                "field_category": disagreement["field_category"],
                "agreement_pattern": disagreement["agreement_pattern"],
                "source_text": packet["sentence_source_text"],
                "focal_text": _focal_text(packet, disagreement.get("unit_id")),
                "context_scope": packet["context_scope"],
                "rights_constraints": sorted(str(value) for value in packet["rights_constraints"]),
                "storage_policy": storage_policy,
                "coder_values": disagreement["coder_values"],
                "reference_summary": disagreement["reference"],
                "model_summary": _model_summary(enriched, model_agreement, model_source),
                "claim_impact": disagreement["claim_impact"],
                "major_claim_impact": disagreement["major_claim_impact"],
                "affected_claims": claims,
                "affected_claim_dimensions": dimensions,
                "source_language_risk": disagreement["source_language_risk"],
                "possible_codebook_ambiguity": disagreement["possible_codebook_ambiguity"],
                "upstream_priority": disagreement["adjudication_priority"],
                "priority": queue_priority,
                "priority_score": score,
                "priority_reasons": reasons,
                "review_question": disagreement["review_question"],
                "review_status": "pending-independent-adjudication",
                "decision_authority": "authorized-human-adjudicator",
                "adjudication_note": (
                    "Coder, reference, and model evidence remain separate. This queue "
                    "contains no adjudication decision and cannot update references."
                ),
            }
        )
    entries.sort(
        key=lambda row: (
            -row["priority_score"],
            row["document_id"],
            row["sentence_id"] or "",
            row["field"],
            row["disagreement_id"],
        )
    )
    for rank, entry in enumerate(entries, start=1):
        entry["queue_rank"] = rank
    if input_artifacts is None:
        input_artifacts = {
            "disagreement_log": {"status": "in_memory", "source": None, "sha256": None},
            "packet_manifest": {"status": "in_memory", "source": None, "sha256": None},
            "packet_payload": {"status": "in_memory", "source": None, "sha256": None},
            "claim_traces": {"status": "unavailable", "source": None, "sha256": None},
            "model_agreement": {"status": "unavailable", "source": None, "sha256": None},
        }
    return {
        "schema_version": "1.0.0",
        "case_id": disagreement_log["case_id"],
        "cohort_id": disagreement_log["cohort_id"],
        "cohort_version": disagreement_log["cohort_version"],
        "source_language": disagreement_log["source_language"],
        "task_layer": disagreement_log["task_layer"],
        "packet_id": disagreement_log["packet_id"],
        "generator": {
            "script": GENERATOR_PATH,
            "version": GENERATOR_VERSION,
            "script_hash": sha256_bytes(Path(__file__).read_bytes()),
            "code_revision": revision,
        },
        "input_artifacts": dict(input_artifacts),
        "queue_policy": (
            "Deterministic prioritization for independent human adjudication. "
            "Coder values, references, and model summaries remain separate; none "
            "constitutes an adjudication decision."
        ),
        "summary": {
            "queue_count": len(entries),
            "high_priority_count": sum(row["priority"] == "high" for row in entries),
            "claim_linked_count": sum(bool(row["affected_claims"]) for row in entries),
            "major_claim_impact_count": sum(bool(row["major_claim_impact"]) for row in entries),
            "model_summary_available_count": sum(row["model_summary"]["status"] == "available" for row in entries),
            "by_priority": dict(sorted(Counter(row["priority"] for row in entries).items())),
        },
        "entries": entries,
    }


def _optional_model_agreement(
    root: Path, case_root: Path
) -> tuple[dict[str, Any] | None, Path | None]:
    path = case_root / "quality" / "model-reliability" / "comparisons" / "agreement-results.json"
    if not path.is_file():
        return None, None
    value = _validate(
        path,
        root / "schemas" / "model-reliability" / "agreement-results-schema.json",
    )
    if value.get("case_id") != case_root.name:
        raise AdjudicationQueueError("model agreement artifact has the wrong case_id")
    return value, path


def write_queue_csv(path: Path, entries: Iterable[Mapping[str, Any]]) -> None:
    fields = [
        "queue_id", "queue_rank", "disagreement_id", "source_pattern_id",
        "case_id", "cohort_id", "cohort_version", "source_language", "task_layer",
        "document_id", "sentence_id", "item_id", "reference_id", "unit_id",
        "field", "category", "field_category", "agreement_pattern", "source_text",
        "focal_text", "context_scope", "rights_constraints", "storage_policy",
        "coder_values", "reference_summary", "model_summary", "claim_impact",
        "major_claim_impact", "affected_claims", "affected_claim_dimensions",
        "source_language_risk", "possible_codebook_ambiguity", "upstream_priority",
        "priority", "priority_score", "priority_reasons", "review_question",
        "review_status", "decision_authority", "adjudication_note",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for entry in entries:
            row = dict(entry)
            for field in (
                "rights_constraints", "coder_values", "reference_summary",
                "model_summary", "affected_claims", "affected_claim_dimensions",
                "source_language_risk", "priority_reasons",
            ):
                row[field] = json.dumps(entry[field], ensure_ascii=False, sort_keys=True)
            writer.writerow({field: row.get(field) for field in fields})


def generate_case_adjudication_queue(
    root: Path,
    case_id: str,
    cohort_id: str,
    cohort_version: str,
) -> dict[str, Any]:
    root = root.resolve()
    for label, value in (
        ("case_id", case_id),
        ("cohort_id", cohort_id),
        ("cohort_version", cohort_version),
    ):
        if not SAFE_COMPONENT.fullmatch(value):
            raise AdjudicationQueueError(f"unsafe {label} `{value}`")
    case_root = root / "cases" / case_id
    comparison_root = (
        case_root / "quality" / "human-reliability" / "comparisons"
        / f"{cohort_id}-{cohort_version}"
    )
    disagreement_path = comparison_root / "disagreement-log.json"
    disagreement_log = _validate(
        disagreement_path,
        root / "schemas" / "human-reliability" / "disagreement-log-schema.json",
    )
    _verify_disagreement_generator(root, disagreement_log)
    if any(
        disagreement_log.get(field) != expected
        for field, expected in (
            ("case_id", case_id),
            ("cohort_id", cohort_id),
            ("cohort_version", cohort_version),
        )
    ):
        raise AdjudicationQueueError("disagreement log does not match requested cohort")
    cohort_path = _cohort_manifest_path(case_root, cohort_id, cohort_version)
    cohort = _validate(
        cohort_path,
        root / "schemas" / "human-reliability" / "cohort-manifest-schema.json",
    )
    try:
        approved_context = load_cohort_context(root, case_id, cohort_path)
    except IngestionError as exc:
        raise AdjudicationQueueError(str(exc)) from exc
    if approved_context.manifest != cohort:
        raise AdjudicationQueueError("approved cohort changed during queue generation")
    for field, expected in (
        ("case_id", case_id),
        ("cohort_id", cohort_id),
        ("cohort_version", cohort_version),
        ("source_language", disagreement_log["source_language"]),
        ("task_layer", disagreement_log["task_layer"]),
        ("packet_id", disagreement_log["packet_id"]),
    ):
        if cohort.get(field) != expected:
            raise AdjudicationQueueError(
                f"approved cohort differs from disagreement log on `{field}`"
            )
    packet_manifest_path = (case_root / str(cohort["packet_manifest"])).resolve()
    try:
        packet_manifest_path.relative_to(case_root.resolve())
    except ValueError as exc:
        raise AdjudicationQueueError("packet manifest escapes the case root") from exc
    packet_manifest = _validate(
        packet_manifest_path,
        root / "schemas" / "human-reliability" / "packet-manifest-schema.json",
    )
    _verify_packet_manifest(root, packet_manifest)
    for field in ("case_id", "source_language", "task_layer", "packet_id"):
        if packet_manifest.get(field) != disagreement_log.get(field):
            raise AdjudicationQueueError(
                f"packet manifest differs from disagreement log on `{field}`"
            )
    expected_packet_artifact = disagreement_log.get("input_artifacts", {}).get("packet_manifest", {})
    actual_packet_ref = _artifact_ref(root, packet_manifest_path)
    if (
        expected_packet_artifact.get("source") != actual_packet_ref["source"]
        or expected_packet_artifact.get("sha256") != actual_packet_ref["sha256"]
    ):
        raise AdjudicationQueueError("packet manifest differs from disagreement provenance")
    packets, packet_path = _packet_items(root, case_root, packet_manifest)
    traces, trace_path = _claim_traces(root, case_id)
    model, model_path = _optional_model_agreement(root, case_root)
    artifacts = {
        "disagreement_log": {"status": "available", **_artifact_ref(root, disagreement_path)},
        "packet_manifest": {"status": "available", **actual_packet_ref},
        "packet_payload": {"status": "available", **_artifact_ref(root, packet_path)},
        "claim_traces": (
            {"status": "available", **_artifact_ref(root, trace_path)}
            if trace_path else {"status": "unavailable", "source": None, "sha256": None}
        ),
        "model_agreement": (
            {"status": "available", **_artifact_ref(root, model_path)}
            if model_path else {"status": "unavailable", "source": None, "sha256": None}
        ),
    }
    result = build_queue(
        disagreement_log,
        packets,
        claim_traces=traces,
        model_agreement=model,
        model_source=artifacts["model_agreement"]["source"],
        storage_policy=str(cohort["storage_policy"]),
        revision=code_revision(root),
        input_artifacts=artifacts,
    )
    output_schema = read_json_object(
        root / "schemas" / "human-reliability" / "adjudication-queue-schema.json"
    )
    errors = sorted(
        Draft202012Validator(output_schema).iter_errors(result),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        raise AdjudicationQueueError(
            "adjudication queue fails schema validation: "
            + "; ".join(error.message for error in errors)
        )
    write_json(safe_output_path(case_root, (
        "quality/human-reliability/comparisons/"
        f"{cohort_id}-{cohort_version}/adjudication-queue.json"
    )), result)
    write_queue_csv(safe_output_path(case_root, (
        "quality/human-reliability/comparisons/"
        f"{cohort_id}-{cohort_version}/adjudication-queue.csv"
    )), result["entries"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument("--cohort", dest="cohort_id", required=True)
    parser.add_argument("--cohort-version", required=True)
    args = parser.parse_args()
    try:
        result = generate_case_adjudication_queue(
            ROOT, args.case_id, args.cohort_id, args.cohort_version
        )
    except (AdjudicationQueueError, ValueError, OSError) as exc:
        parser.error(str(exc))
    print(
        f"{args.case_id}: wrote {result['summary']['queue_count']} adjudication "
        f"queue item(s) for {result['cohort_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
