#!/usr/bin/env python3
"""Classify substantive human-coder disagreements for adjudication."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

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
    from scripts.human_reliability.generate_packets import (
        canonical_json_bytes,
        sample_hash,
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
    from generate_packets import canonical_json_bytes, sample_hash  # type: ignore


ROOT = Path(__file__).resolve().parents[2]
GENERATOR_PATH = "scripts/human_reliability/classify_disagreements.py"
GENERATOR_VERSION = "1.0.0"
CONFIDENCE_DIFFERENCE_THRESHOLD = 0.10
UPSTREAM_GENERATORS = {
    "agreement": "scripts/human_reliability/compute_agreement.py",
    "reference_comparison": "scripts/human_reliability/compare_references.py",
}
LANGUAGE_SENSITIVE_CATEGORIES = {
    "identification",
    "boundary",
    "semantics",
    "domains",
    "clusters",
    "interpretation",
    "violence_obligation",
    "agency_absence",
}


class HumanDisagreementError(ValueError):
    """Raised when disagreement inputs are missing, stale, or inconsistent."""


def _canonical(value: Any) -> str:
    if isinstance(value, list):
        value = sorted(
            value,
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True),
        )
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _equal(left: Any, right: Any) -> bool:
    return _canonical(left) == _canonical(right)


def category_for_field(field: str) -> str:
    if field == "identification.decision_type":
        return "identification"
    if field in {
        "identification.boundary_response",
        "identification.selected_unit_boundary",
    }:
        return "boundary"
    if field in {
        "identification.contextual_meaning",
        "identification.basic_meaning",
        "identification.basic_meaning_source",
        "identification.contrast_explanation",
        "identification.comparison_basis",
        "cmt.conceptual_mapping",
        "cmt.entailments",
        "cmt.rival_reading",
    }:
        return "semantics"
    if field in {
        "cmt.source_domain_primary",
        "cmt.source_domain_secondary",
        "cmt.target_domain",
    }:
        return "domains"
    if field == "cmt.cluster_id":
        return "clusters"
    if field in {
        "interpretation.violence_logic",
        "interpretation.obligatory_frame",
    }:
        return "violence_obligation"
    if field.startswith("interpretation.") and any(
        token in field
        for token in (
            "agents",
            "patients",
            "beneficiaries",
            "absence_",
            "presence_criterion",
        )
    ):
        return "agency_absence"
    if field.startswith("interpretation."):
        return "interpretation"
    if field in {"confidence", "uncertainty"}:
        return "confidence"
    if field == "disposition":
        return "scope_disposition"
    raise HumanDisagreementError(f"unclassified human reliability field `{field}`")


def _is_substantive(pattern: Mapping[str, Any]) -> bool:
    name = pattern.get("pattern")
    if name == "both_with_reference":
        return False
    if name == "both_against_reference":
        return True
    if pattern.get("field") == "confidence":
        left = pattern.get("left_value")
        right = pattern.get("right_value")
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return abs(float(left) - float(right)) >= CONFIDENCE_DIFFERENCE_THRESHOLD
    return not _equal(pattern.get("left_value"), pattern.get("right_value"))


def _ambiguity_reasons(
    pattern: Mapping[str, Any], sample_item: Mapping[str, Any]
) -> list[str]:
    reasons: list[str] = []
    design_roles = set(sample_item.get("design_roles", []))
    if "ambiguous" in design_roles or "rival_control" in design_roles:
        reasons.append("sample design marks the item as ambiguous or a rival-reading control")
    if pattern.get("pattern") == "uncertain_vs_confident":
        reasons.append("one coder preserved uncertainty while the other did not")
    if pattern.get("reference_status") == "not_comparable":
        reasons.append("the qualitative field requires interpretive rather than exact comparison")
    if pattern.get("pattern") == "split_against_both":
        reasons.append("the coders and available reference preserve three distinct positions")
    return reasons


def _source_language_risk(
    category: str, provenance_risks: Sequence[str]
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if category in LANGUAGE_SENSITIVE_CATEGORIES:
        reasons.append("the disagreement depends on source-language interpretation")
    if provenance_risks:
        reasons.append("the sample records provenance risk: " + ", ".join(provenance_risks))
    if reasons and provenance_risks:
        return "high", reasons
    if reasons:
        return "material", reasons
    return "low", ["no specific source-language or provenance escalation is recorded"]


def _priority(
    *,
    pattern: str,
    claim_impact: str,
    source_language_risk: str,
    ambiguity: bool,
) -> str:
    if claim_impact == "high" or pattern == "both_against_reference":
        return "high"
    if source_language_risk == "high" or pattern == "split_against_both":
        return "high"
    if claim_impact == "moderate" or ambiguity:
        return "medium"
    return "medium" if pattern != "reference_unavailable" else "low"


def _review_question(category: str, pattern: str) -> str:
    if pattern == "both_against_reference":
        return (
            "What evidence supports the shared coder value and the reference value, "
            "and should either the coding guidance or reference be revised?"
        )
    return {
        "identification": "Which identification decision is best supported by the declared MIPVU criteria?",
        "boundary": "Which lexical boundary is supported by the source text and boundary rules?",
        "semantics": "Which semantic account is supported, and does the codebook distinguish the rival readings?",
        "domains": "Which source and target domain assignments are textually supported?",
        "clusters": "Which cluster assignment is supported without collapsing distinct mappings?",
        "interpretation": "Which bounded interpretation is supported by the assigned context?",
        "violence_obligation": "Does the text support violence or obligation under the field-specific criteria?",
        "agency_absence": "Which agency or absence judgment is supported within the declared scope?",
        "confidence": "What evidence warrants the differing confidence or uncertainty judgments?",
        "scope_disposition": "Is the item codable within the assigned scope, or should it remain out of scope?",
    }[category]


def classify_disagreements(
    agreement: Mapping[str, Any],
    reference_comparison: Mapping[str, Any],
    sample: Mapping[str, Any],
    *,
    revision: str = "in-memory-classification",
    input_artifacts: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    identity_fields = (
        "case_id",
        "cohort_id",
        "cohort_version",
        "source_language",
        "task_layer",
        "packet_id",
    )
    for field in identity_fields:
        if agreement.get(field) != reference_comparison.get(field):
            raise HumanDisagreementError(f"upstream artifacts differ on `{field}`")
    if agreement.get("input_runs") != reference_comparison.get("input_runs"):
        raise HumanDisagreementError("upstream artifacts describe different coder runs")
    for field in ("case_id", "source_language", "task_layer"):
        if sample.get(field) != agreement.get(field):
            raise HumanDisagreementError(f"sample and upstream artifacts differ on `{field}`")
    sample_items = sample.get("items")
    if not isinstance(sample_items, list):
        raise HumanDisagreementError("sample manifest lacks items")
    by_item = {
        str(item.get("item_id") or ""): item
        for item in sample_items
        if isinstance(item, Mapping)
    }
    records: list[dict[str, Any]] = []
    for pattern in reference_comparison.get("pattern_records", []):
        if not isinstance(pattern, Mapping) or not _is_substantive(pattern):
            continue
        item_id = str(pattern.get("item_id") or "")
        sample_item = by_item.get(item_id)
        if not isinstance(sample_item, Mapping):
            raise HumanDisagreementError(
                f"reference pattern item `{item_id}` is absent from the sample manifest"
            )
        base_category = category_for_field(str(pattern.get("field") or ""))
        category = (
            "reference_challenge"
            if pattern.get("pattern") == "both_against_reference"
            else base_category
        )
        provenance_risks = sorted(str(value) for value in sample_item.get("provenance_risks", []))
        language_risk, language_reasons = _source_language_risk(
            base_category, provenance_risks
        )
        ambiguity_reasons = _ambiguity_reasons(pattern, sample_item)
        claim_impact = str(sample_item.get("claim_impact") or "")
        priority = _priority(
            pattern=str(pattern.get("pattern") or ""),
            claim_impact=claim_impact,
            source_language_risk=language_risk,
            ambiguity=bool(ambiguity_reasons),
        )
        digest = hashlib.sha256(
            "|".join(
                str(pattern.get(key) or "")
                for key in (
                    "pattern_id",
                    "left_coder_id",
                    "right_coder_id",
                    "item_id",
                    "unit_id",
                    "field",
                )
            ).encode()
        ).hexdigest()[:16]
        records.append(
            {
                "disagreement_id": f"human-disagreement-{digest}",
                "source_pattern_id": pattern["pattern_id"],
                "item_id": item_id,
                "document_id": sample_item["document_id"],
                "sentence_id": sample_item.get("sentence_id"),
                "reference_id": pattern["reference_id"],
                "unit_id": pattern.get("unit_id"),
                "field": pattern["field"],
                "category": category,
                "field_category": base_category,
                "agreement_pattern": pattern["pattern"],
                "coder_values": [
                    {"coder_id": pattern["left_coder_id"], "value": pattern["left_value"]},
                    {"coder_id": pattern["right_coder_id"], "value": pattern["right_value"]},
                ],
                "reference": {
                    "status": pattern["reference_status"],
                    "value": pattern.get("reference_value"),
                    "authority": pattern.get("reference_authority"),
                },
                "design_roles": sorted(str(value) for value in sample_item.get("design_roles", [])),
                "provenance_risks": provenance_risks,
                "source_language_risk": {
                    "level": language_risk,
                    "reasons": language_reasons,
                },
                "claim_impact": claim_impact,
                "major_claim_impact": claim_impact == "high",
                "possible_codebook_ambiguity": bool(ambiguity_reasons),
                "codebook_ambiguity_reasons": ambiguity_reasons,
                "adjudication_priority": priority,
                "adjudication_recommended": True,
                "review_question": _review_question(base_category, str(pattern["pattern"])),
            }
        )
    records.sort(key=lambda row: (row["item_id"], row["field"], row["disagreement_id"]))

    def counts(field: str) -> dict[str, int]:
        return dict(sorted(Counter(str(row[field]) for row in records).items()))

    if input_artifacts is None:
        empty_artifact = {
            "source": "in-memory",
            "sha256": "sha256:" + "0" * 64,
            "generator_script": None,
            "generator_script_hash": None,
        }
        input_artifacts = {
            name: dict(empty_artifact)
            for name in (
                "agreement",
                "reference_comparison",
                "packet_manifest",
                "sample_manifest",
            )
        }
    return {
        "schema_version": "1.0.0",
        "case_id": agreement["case_id"],
        "cohort_id": agreement["cohort_id"],
        "cohort_version": agreement["cohort_version"],
        "source_language": agreement["source_language"],
        "task_layer": agreement["task_layer"],
        "packet_id": agreement["packet_id"],
        "generator": {
            "script": GENERATOR_PATH,
            "version": GENERATOR_VERSION,
            "script_hash": sha256_bytes(Path(__file__).read_bytes()),
            "code_revision": revision,
        },
        "input_artifacts": dict(input_artifacts),
        "summary": {
            "total_disagreements": len(records),
            "by_category": counts("category"),
            "by_claim_impact": counts("claim_impact"),
            "by_priority": counts("adjudication_priority"),
            "by_source_language_risk": dict(
                sorted(Counter(row["source_language_risk"]["level"] for row in records).items())
            ),
            "possible_codebook_ambiguity_count": sum(
                bool(row["possible_codebook_ambiguity"]) for row in records
            ),
            "major_claim_impact_count": sum(bool(row["major_claim_impact"]) for row in records),
        },
        "disagreements": records,
    }


def _validate(path: Path, schema_path: Path) -> dict[str, Any]:
    value = read_json_object(path)
    schema = read_json_object(schema_path)
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        raise HumanDisagreementError(
            f"{path}: schema validation failed: "
            + "; ".join(error.message for error in errors)
        )
    return value


def _artifact_ref(root: Path, path: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        source = path.relative_to(root).as_posix()
    except ValueError:
        source = "coordinator://sample-manifest"
    generator = value.get("generator")
    return {
        "source": source,
        "sha256": sha256_bytes(path.read_bytes()),
        "generator_script": generator.get("script") if isinstance(generator, Mapping) else None,
        "generator_script_hash": generator.get("script_hash") if isinstance(generator, Mapping) else None,
    }


def _verify_upstream_generator(
    root: Path, name: str, artifact: Mapping[str, Any]
) -> None:
    expected = UPSTREAM_GENERATORS[name]
    generator = artifact.get("generator")
    if not isinstance(generator, Mapping) or generator.get("script") != expected:
        raise HumanDisagreementError(f"{name} artifact has an unexpected generator")
    path = root / expected
    if not path.is_file():
        path = ROOT / expected
    if generator.get("script_hash") != sha256_bytes(path.read_bytes()):
        raise HumanDisagreementError(f"{name} artifact generator hash is stale")


def _verify_packet_manifest(root: Path, packet: Mapping[str, Any]) -> None:
    generator = packet.get("generator")
    expected_script = "scripts/human_reliability/generate_packets.py"
    if not isinstance(generator, Mapping) or generator.get("script") != expected_script:
        raise HumanDisagreementError("packet manifest has an unexpected generator")
    generator_path = root / expected_script
    if not generator_path.is_file():
        generator_path = ROOT / expected_script
    if generator.get("script_hash") != sha256_bytes(generator_path.read_bytes()):
        raise HumanDisagreementError("packet manifest generator hash is stale")
    unsigned = {key: value for key, value in packet.items() if key != "packet_hash"}
    expected_hash = sha256_bytes(canonical_json_bytes(unsigned))
    if packet.get("packet_hash") != expected_hash:
        raise HumanDisagreementError("packet manifest self-hash is invalid")


def _find_sample_manifest(
    root: Path,
    case_id: str,
    sample_id: str,
    sample_version: str,
    supplied: Path | None,
) -> Path:
    if supplied is not None:
        return supplied.resolve()
    sample_root = root / "cases" / case_id / "quality" / "human-reliability" / "samples"
    matches: list[Path] = []
    for path in sorted(sample_root.rglob("*.json")):
        try:
            value = read_json_object(path)
        except ValueError:
            continue
        if value.get("sample_id") == sample_id and value.get("sample_version") == sample_version:
            matches.append(path)
    if len(matches) != 1:
        raise HumanDisagreementError(
            f"expected one sample manifest for `{sample_id}` `{sample_version}`, "
            f"found {len(matches)}; provide --sample-manifest for coordinator-held samples"
        )
    return matches[0]


def write_disagreement_csv(path: Path, result: Mapping[str, Any]) -> None:
    fields = [
        "disagreement_id", "source_pattern_id", "item_id", "document_id",
        "sentence_id", "reference_id", "unit_id", "field", "category",
        "field_category", "agreement_pattern", "coder_values", "reference_status",
        "reference_value", "reference_authority", "design_roles", "provenance_risks",
        "source_language_risk", "source_language_risk_reasons", "claim_impact",
        "major_claim_impact", "possible_codebook_ambiguity",
        "codebook_ambiguity_reasons", "adjudication_priority",
        "adjudication_recommended", "review_question",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in result["disagreements"]:
            writer.writerow(
                {
                    **{key: row.get(key) for key in fields},
                    "coder_values": _canonical(row["coder_values"]),
                    "reference_status": row["reference"]["status"],
                    "reference_value": _canonical(row["reference"]["value"]),
                    "reference_authority": row["reference"]["authority"],
                    "design_roles": " | ".join(row["design_roles"]),
                    "provenance_risks": " | ".join(row["provenance_risks"]),
                    "source_language_risk": row["source_language_risk"]["level"],
                    "source_language_risk_reasons": " | ".join(row["source_language_risk"]["reasons"]),
                    "codebook_ambiguity_reasons": " | ".join(row["codebook_ambiguity_reasons"]),
                }
            )


def compute_case_disagreements(
    root: Path,
    case_id: str,
    cohort_id: str,
    cohort_version: str,
    *,
    sample_manifest_path: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    for label, value in (
        ("case_id", case_id),
        ("cohort_id", cohort_id),
        ("cohort_version", cohort_version),
    ):
        if not SAFE_COMPONENT.fullmatch(value):
            raise HumanDisagreementError(f"unsafe {label} `{value}`")
    case_root = root / "cases" / case_id
    comparison_root = (
        case_root / "quality" / "human-reliability" / "comparisons"
        / f"{cohort_id}-{cohort_version}"
    )
    agreement_path = comparison_root / "human-agreement.json"
    reference_path = comparison_root / "reference-comparison.json"
    agreement = _validate(
        agreement_path,
        root / "schemas" / "human-reliability" / "agreement-results-schema.json",
    )
    reference = _validate(
        reference_path,
        root / "schemas" / "human-reliability" / "reference-comparison-schema.json",
    )
    _verify_upstream_generator(root, "agreement", agreement)
    _verify_upstream_generator(root, "reference_comparison", reference)
    cohort_path = _cohort_manifest_path(case_root, cohort_id, cohort_version)
    cohort = _validate(
        cohort_path,
        root / "schemas" / "human-reliability" / "cohort-manifest-schema.json",
    )
    packet_path = (case_root / str(cohort["packet_manifest"])).resolve()
    try:
        packet_path.relative_to(case_root.resolve())
    except ValueError as exc:
        raise HumanDisagreementError("cohort packet manifest escapes the case root") from exc
    packet = _validate(
        packet_path,
        root / "schemas" / "human-reliability" / "packet-manifest-schema.json",
    )
    _verify_packet_manifest(root, packet)
    sample_path = _find_sample_manifest(
        root,
        case_id,
        str(cohort.get("sample_id") or ""),
        str(cohort.get("sample_version") or ""),
        sample_manifest_path,
    )
    sample = _validate(
        sample_path,
        root / "schemas" / "human-reliability" / "sample-manifest-schema.json",
    )
    if (
        sample.get("sample_id") != cohort.get("sample_id")
        or sample.get("sample_version") != cohort.get("sample_version")
        or sample.get("status") != "approved"
    ):
        raise HumanDisagreementError("sample manifest does not match the approved cohort")
    if (
        packet.get("packet_id") != agreement.get("packet_id")
        or packet.get("sample_id") != sample.get("sample_id")
        or packet.get("sample_version") != sample.get("sample_version")
        or packet.get("sample_hash") != sample_hash(sample)
    ):
        raise HumanDisagreementError(
            "sample manifest identity or approved hash differs from the packet manifest"
        )
    artifacts = {
        "agreement": _artifact_ref(root, agreement_path, agreement),
        "reference_comparison": _artifact_ref(root, reference_path, reference),
        "packet_manifest": _artifact_ref(root, packet_path, packet),
        "sample_manifest": _artifact_ref(root, sample_path, sample),
    }
    result = classify_disagreements(
        agreement,
        reference,
        sample,
        revision=code_revision(root),
        input_artifacts=artifacts,
    )
    output_schema = read_json_object(
        root / "schemas" / "human-reliability" / "disagreement-log-schema.json"
    )
    errors = sorted(
        Draft202012Validator(output_schema).iter_errors(result),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        raise HumanDisagreementError(
            "human disagreement log fails schema validation: "
            + "; ".join(error.message for error in errors)
        )
    write_json(
        safe_output_path(case_root, (
            "quality/human-reliability/comparisons/"
            f"{cohort_id}-{cohort_version}/disagreement-log.json"
        )),
        result,
    )
    write_disagreement_csv(
        safe_output_path(case_root, (
            "quality/human-reliability/comparisons/"
            f"{cohort_id}-{cohort_version}/disagreement-log.csv"
        )),
        result,
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument("--cohort", dest="cohort_id", required=True)
    parser.add_argument("--cohort-version", required=True)
    parser.add_argument("--sample-manifest", type=Path)
    args = parser.parse_args()
    try:
        result = compute_case_disagreements(
            ROOT,
            args.case_id,
            args.cohort_id,
            args.cohort_version,
            sample_manifest_path=args.sample_manifest,
        )
    except (HumanDisagreementError, ValueError) as exc:
        parser.error(str(exc))
    print(
        f"{args.case_id}: wrote {result['summary']['total_disagreements']} "
        f"human disagreement record(s) for {result['cohort_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
