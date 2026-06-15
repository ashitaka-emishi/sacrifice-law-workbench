#!/usr/bin/env python3
"""Preflight CMT/Koenigsbergian annotations against MIPVU evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional

from pipeline_common import (
    case_dir,
    case_ids,
    documents,
    get_nested,
    iter_instances_from_annotated,
    iter_mipvu_records,
    mipvu_path_for,
    read_json,
)

METAPHOR_DECISIONS = {
    "mipvu_indirect",
    "mipvu_direct",
    "mipvu_implicit",
    "mipvu_personification",
    "uncertain",
}


def annotated_files(case_id: str, doc_id: Optional[str] = None) -> list[Path]:
    files = sorted((case_dir(case_id) / "corpus" / "annotated").glob("*_annotated.json"))
    if doc_id:
        return [path for path in files if path.name == f"{doc_id}_annotated.json"]
    return files


def mipvu_lookup(case_id: str) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for doc in documents(case_id):
        path = mipvu_path_for(case_id, doc)
        data = read_json(path, {}) or {}
        for unit in iter_mipvu_records(data):
            mipvu_id = unit.get("mipvu_id")
            if mipvu_id:
                lookup[str(mipvu_id)] = unit
    return lookup


def check_case(case_id: str, doc_id: Optional[str] = None, exploratory: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checked_instances = 0
    files = annotated_files(case_id, doc_id=doc_id)
    lookup = mipvu_lookup(case_id)

    if not files:
        return {
            "case_id": case_id,
            "document_id": doc_id,
            "status": "ready" if lookup or exploratory else "blocked",
            "checked_instances": 0,
            "errors": [] if lookup or exploratory else ["no annotations found and no MIPVU worklists available"],
            "warnings": ["no annotated files found"],
        }

    if not lookup and not exploratory:
        errors.append("no MIPVU worklists available; run scripts/generate-mipvu-worklist.py first")

    for path in files:
        data = read_json(path, {}) or {}
        for inst, sentence_id in iter_instances_from_annotated(data):
            checked_instances += 1
            instance_id = inst.get("instance_id") or "unknown"
            if get_nested(inst, "meta", "exploratory_without_mipvu") is True or exploratory:
                warnings.append(f"{path.name}:{instance_id}: exploratory without MIPVU backing")
                continue
            mipvu_ids = inst.get("mipvu_ids")
            if not isinstance(mipvu_ids, list) or not mipvu_ids:
                errors.append(f"{path.name}:{instance_id}: missing mipvu_ids")
                continue
            for mipvu_id in mipvu_ids:
                unit = lookup.get(str(mipvu_id))
                if not unit:
                    errors.append(f"{path.name}:{instance_id}: mipvu_id {mipvu_id!r} not found")
                    continue
                if sentence_id and unit.get("sentence_id") != sentence_id:
                    errors.append(f"{path.name}:{instance_id}: mipvu_id {mipvu_id!r} belongs to another sentence")
                if unit.get("decision_type") not in METAPHOR_DECISIONS:
                    errors.append(f"{path.name}:{instance_id}: mipvu_id {mipvu_id!r} is not metaphor-related or uncertain")

    return {
        "case_id": case_id,
        "document_id": doc_id,
        "status": "blocked" if errors else "ready",
        "checked_instances": checked_instances,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", default=None, help="Optional case id")
    parser.add_argument("--doc", dest="doc_id", default=None, help="Optional document id")
    parser.add_argument(
        "--exploratory",
        action="store_true",
        help="Allow exploratory annotation checks without MIPVU backing",
    )
    args = parser.parse_args()

    results = [
        check_case(case_id, doc_id=args.doc_id, exploratory=args.exploratory)
        for case_id in case_ids(args.case_id)
    ]
    print(json.dumps({"script": Path(__file__).name, "results": results}, indent=2, ensure_ascii=False))
    return 1 if any(result["status"] == "blocked" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
