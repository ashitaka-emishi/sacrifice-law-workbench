#!/usr/bin/env python3
"""Run case-level aggregate analysis from a case concordance."""
from __future__ import annotations

import argparse
from typing import Any

from pipeline_common import (
    case_dir,
    case_ids,
    cluster_config,
    count_by,
    get_nested,
    now_iso,
    read_json,
    write_json,
)


def rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 3)


def existing_cluster(existing: dict[str, Any], cluster_id: str) -> dict[str, Any]:
    for item in existing.get("cluster_analyses", []) or []:
        if item.get("cluster_id") == cluster_id:
            return item
    return {}


def run_case_analysis(case_id: str, strict: bool = False) -> dict:
    case_path = case_dir(case_id)
    concordance_path = case_path / "analysis" / "concordance.json"
    existing = read_json(case_path / "analysis" / "analysis.json", {}) or {}
    concordance = read_json(concordance_path, {}) or {}
    errors: list[str] = []
    if not concordance_path.exists():
        message = f"{case_id}: missing concordance at {concordance_path}"
        if strict:
            errors.append(message)
        instances: list[dict[str, Any]] = []
    else:
        instances = [item for item in concordance.get("instances", []) if isinstance(item, dict)]
    mipvu_profile = concordance.get("mipvu_profile", {}) if isinstance(concordance, dict) else {}

    clusters = cluster_config(case_id)
    cluster_analyses = []
    for cluster in clusters:
        cluster_id = str(cluster.get("id"))
        cluster_instances = [
            item for item in instances if get_nested(item, "cmt", "cluster_id") == cluster_id
        ]
        existing_item = existing_cluster(existing, cluster_id)
        count = len(cluster_instances)
        by_document = count_by(cluster_instances, lambda item: item.get("document_id"))
        by_register = count_by(cluster_instances, lambda item: item.get("document_register"))
        fantasy_counts = count_by(cluster_instances, lambda item: get_nested(item, "koenigsberg", "fantasy_type"))
        violence_counts = count_by(cluster_instances, lambda item: get_nested(item, "koenigsberg", "violence_logic"))
        absence_counts = count_by(cluster_instances, lambda item: get_nested(item, "koenigsberg", "absence_flags"))
        obligatory_count = sum(
            1 for item in cluster_instances if get_nested(item, "koenigsberg", "obligatory_frame") is True
        )
        sacrificial_count = sum(
            1 for item in cluster_instances if get_nested(item, "koenigsberg", "sacrificial_economy") is True
        )

        cluster_analyses.append(
            {
                "cluster_id": cluster_id,
                "cluster_name": cluster.get("name"),
                "status": cluster.get("status", "unknown"),
                "instance_count": count,
                "instance_ids": [item.get("instance_id") for item in cluster_instances],
                "by_document": by_document,
                "by_register": by_register,
                "koenigsberg_profile": {
                    "fantasy_type_distribution": fantasy_counts,
                    "violence_logic_distribution": violence_counts,
                    "obligatory_frame_rate": rate(obligatory_count, count),
                    "sacrificial_economy_rate": rate(sacrificial_count, count),
                    "absence_flags_distribution": absence_counts,
                },
                "analyst_notes": existing_item.get("analyst_notes"),
                "interpretive_summary": existing_item.get("interpretive_summary"),
                "what_metaphor_conceals": existing_item.get("what_metaphor_conceals"),
            }
        )

    analysis = {
        "version": "1.0",
        "case_id": case_id,
        "generated_at": now_iso(),
        "status": "error" if errors else ("complete" if instances else "stub"),
        "total_instances": len(instances),
        "mipvu_profile": mipvu_profile,
        "cluster_analyses": cluster_analyses,
        "corpus_profile": {
            "by_document": count_by(instances, lambda item: item.get("document_id")),
            "by_register": count_by(instances, lambda item: item.get("document_register")),
            "by_cluster": count_by(instances, lambda item: get_nested(item, "cmt", "cluster_id")),
            "by_fantasy_type": count_by(instances, lambda item: get_nested(item, "koenigsberg", "fantasy_type")),
            "by_violence_logic": count_by(instances, lambda item: get_nested(item, "koenigsberg", "violence_logic")),
            "by_absence_flag": count_by(instances, lambda item: get_nested(item, "koenigsberg", "absence_flags")),
            "mipvu_denominator": {
                "total_lexical_units": mipvu_profile.get("total_lexical_units"),
                "reviewed_lexical_units": mipvu_profile.get("reviewed_lexical_units"),
                "confirmed_metaphor_units": mipvu_profile.get("confirmed_metaphor_units"),
                "metaphor_or_uncertain_units": mipvu_profile.get("metaphor_or_uncertain_units"),
                "metaphor_rate_confirmed": mipvu_profile.get("metaphor_rate_confirmed"),
                "metaphor_rate_including_uncertain": mipvu_profile.get("metaphor_rate_including_uncertain"),
                "reviewed_metaphor_rate_confirmed": mipvu_profile.get("reviewed_metaphor_rate_confirmed"),
                "reviewed_metaphor_rate_including_uncertain": mipvu_profile.get(
                    "reviewed_metaphor_rate_including_uncertain"
                ),
            },
        },
        "errors": errors,
        "pipeline_log": [
            {
                "stage": "run-case-analysis",
                "script": "scripts/run-case-analysis.py",
                "generated_at": now_iso(),
            }
        ],
    }
    write_json(case_path / "analysis" / "analysis.json", analysis)
    return analysis


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", default=None, help="Optional case id")
    parser.add_argument("--strict", action="store_true", help="Fail on missing expected inputs")
    args = parser.parse_args()

    exit_code = 0
    for case_id in case_ids(args.case_id):
        analysis = run_case_analysis(case_id, strict=args.strict)
        print(f"{case_id}: analyzed {analysis['total_instances']} instance(s).")
        if analysis["errors"]:
            exit_code = 1
            for error in analysis["errors"]:
                print(f"ERROR: {error}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
