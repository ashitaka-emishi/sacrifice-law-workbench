#!/usr/bin/env python3
"""Build case-level concordances from annotated documents."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from pipeline_common import (
    MIPVU_CONFIRMED_METAPHOR_DECISIONS,
    MIPVU_METAPHOR_OR_UNCERTAIN_DECISIONS,
    case_dir,
    case_ids,
    cmt_mappings_path_for,
    documents,
    get_nested,
    iter_cmt_mappings,
    iter_instances_from_annotated,
    iter_mipvu_records,
    mipvu_path_for,
    now_iso,
    read_json,
    valid_cluster_ids,
    write_json,
)


def add_index(index: dict[str, list[str]], key: Any, instance_id: str) -> None:
    if key in (None, ""):
        return
    if isinstance(key, list):
        for item in key:
            add_index(index, item, instance_id)
        return
    index.setdefault(str(key), []).append(instance_id)


def annotated_files(case_id: str) -> list[Path]:
    return sorted((case_dir(case_id) / "corpus" / "annotated").glob("*_annotated.json"))


def confidence_bucket(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "missing"
    if value >= 0.9:
        return "high"
    if value >= 0.7:
        return "medium"
    return "low"


def build_mipvu_profile(case_id: str) -> dict[str, Any]:
    units: list[dict[str, Any]] = []
    document_registers: dict[str, str] = {}
    files = 0

    for doc in documents(case_id):
        doc_id = str(doc.get("document_id") or doc.get("id") or "")
        path = mipvu_path_for(case_id, doc)
        if not path.exists():
            continue
        files += 1
        data = read_json(path, {}) or {}
        meta = data.get("meta", {}) if isinstance(data, dict) else {}
        register = meta.get("register") if isinstance(meta, dict) else None
        if register:
            document_registers[doc_id] = str(register)
        for unit in iter_mipvu_records(data):
            unit = dict(unit)
            if register and not unit.get("document_register"):
                unit["document_register"] = str(register)
            units.append(unit)

    total_units = len(units)
    reviewed = [unit for unit in units if unit.get("decision_type")]
    confirmed = [
        unit for unit in units if unit.get("decision_type") in MIPVU_CONFIRMED_METAPHOR_DECISIONS
    ]
    including_uncertain = [
        unit for unit in units if unit.get("decision_type") in MIPVU_METAPHOR_OR_UNCERTAIN_DECISIONS
    ]
    pending = [
        unit for unit in units if not unit.get("decision_type") or unit.get("review_status") == "pending"
    ]

    return {
        "mipvu_files": files,
        "total_lexical_units": total_units,
        "reviewed_lexical_units": len(reviewed),
        "pending_lexical_units": len(pending),
        "confirmed_metaphor_units": len(confirmed),
        "metaphor_or_uncertain_units": len(including_uncertain),
        "metaphor_rate_confirmed": round(len(confirmed) / total_units, 4) if total_units else None,
        "metaphor_rate_including_uncertain": round(len(including_uncertain) / total_units, 4) if total_units else None,
        "reviewed_metaphor_rate_confirmed": round(len(confirmed) / len(reviewed), 4) if reviewed else None,
        "reviewed_metaphor_rate_including_uncertain": (
            round(len(including_uncertain) / len(reviewed), 4) if reviewed else None
        ),
        "by_document": count_simple(units, lambda unit: unit.get("document_id")),
        "by_register": count_simple(units, lambda unit: unit.get("document_register")),
        "by_language": count_simple(units, lambda unit: unit.get("language")),
        "by_decision_type": count_simple(units, lambda unit: unit.get("decision_type") or "pending"),
        "by_confidence": count_simple(units, lambda unit: confidence_bucket(unit.get("confidence"))),
    }


def build_cmt_profile(case_id: str) -> dict[str, Any]:
    path = cmt_mappings_path_for(case_id)
    data = read_json(path, {}) or {}
    mappings = list(iter_cmt_mappings(data))
    return {
        "mapping_file": str(path.relative_to(case_dir(case_id))) if path.exists() else None,
        "mapping_count": len(mappings),
        "by_cluster": count_simple(mappings, lambda item: item.get("cluster_id")),
        "by_source_domain": count_simple(mappings, lambda item: item.get("source_domain_primary")),
        "by_target_domain": count_simple(mappings, lambda item: item.get("target_domain")),
        "by_conceptual_metaphor": count_simple(mappings, lambda item: item.get("conceptual_metaphor")),
        "by_document": count_simple(mappings, lambda item: item.get("document_id")),
        "by_salience": count_simple(mappings, lambda item: item.get("rhetorical_salience")),
        "by_status": count_simple(mappings, lambda item: item.get("mapping_status") or "unspecified"),
    }


def count_simple(items: list[dict[str, Any]], getter) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = getter(item)
        if value in (None, ""):
            continue
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])))


def build_case_concordance(case_id: str, strict: bool = False) -> dict:
    case_path = case_dir(case_id)
    files = annotated_files(case_id)
    cluster_ids = valid_cluster_ids(case_id)
    errors: list[str] = []
    instances: list[dict[str, Any]] = []
    processed_documents: set[str] = set()
    total_sentences = 0
    indexes: dict[str, dict[str, list[str]] | list[str]] = {
        "by_cluster": {cluster_id: [] for cluster_id in sorted(cluster_ids)},
        "by_document": {},
        "by_register": {},
        "by_fantasy_type": {},
        "by_violence_logic": {},
        "by_absence_flag": {},
        "high_confidence_only": [],
        "suppression_instances": [],
    }

    if strict and documents(case_id) and not files:
        errors.append(f"{case_id}: no annotated files found")

    for path in files:
        data = read_json(path, {})
        if not isinstance(data, dict) and not isinstance(data, list):
            errors.append(f"{path}: annotated file must be object or list")
            continue
        document_id = data.get("document_id") if isinstance(data, dict) else None
        register = get_nested(data, "meta", "register") if isinstance(data, dict) else None
        register = register or get_nested(data, "metadata", "register") or "unknown"
        if isinstance(data, dict):
            for section in data.get("sections", []) or []:
                for para in section.get("paragraphs", []) or []:
                    total_sentences += len(para.get("sentences", []) or [])

        for inst, sentence_id in iter_instances_from_annotated(data):
            instance_id = str(inst.get("instance_id") or "")
            if not instance_id:
                errors.append(f"{path}: annotation missing instance_id")
                continue
            inst_doc = str(inst.get("document_id") or document_id or path.name.removesuffix("_annotated.json"))
            inst["document_id"] = inst_doc
            if sentence_id and not inst.get("sentence_id"):
                inst["sentence_id"] = sentence_id
            inst.setdefault("case_id", case_id)
            if register != "unknown":
                inst.setdefault("document_register", register)
            processed_documents.add(inst_doc)
            instances.append(inst)

            cluster_id = get_nested(inst, "cmt", "cluster_id")
            if cluster_id:
                add_index(indexes["by_cluster"], cluster_id, instance_id)  # type: ignore[arg-type]
            add_index(indexes["by_document"], inst_doc, instance_id)  # type: ignore[arg-type]
            add_index(indexes["by_register"], inst.get("document_register", register), instance_id)  # type: ignore[arg-type]
            add_index(indexes["by_fantasy_type"], get_nested(inst, "koenigsberg", "fantasy_type"), instance_id)  # type: ignore[arg-type]
            add_index(indexes["by_violence_logic"], get_nested(inst, "koenigsberg", "violence_logic"), instance_id)  # type: ignore[arg-type]
            add_index(indexes["by_absence_flag"], get_nested(inst, "koenigsberg", "absence_flags"), instance_id)  # type: ignore[arg-type]

            confidence = get_nested(inst, "meta", "confidence")
            if isinstance(confidence, (int, float)) and confidence >= 0.9:
                indexes["high_confidence_only"].append(instance_id)  # type: ignore[union-attr]
            if get_nested(inst, "meta", "suppression_flag") is True:
                indexes["suppression_instances"].append(instance_id)  # type: ignore[union-attr]

    cmt_profile = build_cmt_profile(case_id)
    has_evidence = bool(instances) or cmt_profile.get("mapping_count", 0) > 0
    concordance = {
        "version": "1.0",
        "case_id": case_id,
        "generated_at": now_iso(),
        "status": "error" if errors else ("complete" if has_evidence else "stub"),
        "mipvu_profile": build_mipvu_profile(case_id),
        "cmt_profile": cmt_profile,
        "total_documents": len(processed_documents),
        "total_sentences": total_sentences,
        "total_instances": len(instances),
        "instances": instances,
        "indexes": indexes,
        "errors": errors,
        "pipeline_log": [
            {
                "stage": "build-concordance",
                "script": "scripts/build-concordance.py",
                "annotated_files": len(files),
                "generated_at": now_iso(),
            }
        ],
    }
    write_json(case_path / "analysis" / "concordance.json", concordance)
    return concordance


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", default=None, help="Optional case id")
    parser.add_argument("--strict", action="store_true", help="Fail on missing expected inputs")
    args = parser.parse_args()

    exit_code = 0
    for case_id in case_ids(args.case_id):
        concordance = build_case_concordance(case_id, strict=args.strict)
        print(
            f"{case_id}: indexed {concordance['total_instances']} instance(s) "
            f"from {concordance['total_documents']} document(s)."
        )
        if concordance["errors"]:
            exit_code = 1
            for error in concordance["errors"]:
                print(f"ERROR: {error}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
