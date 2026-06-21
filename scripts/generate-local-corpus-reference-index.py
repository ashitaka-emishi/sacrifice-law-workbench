#!/usr/bin/env python3
"""Generate a text-free index for committed references into local-only corpus files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from local_corpus_reference_index import (
    INDEX_VERSION,
    index_path,
    sha256_json_artifact,
    sha256_record,
)
from pipeline_common import (
    ROOT,
    annotated_path_for,
    case_dir,
    cmt_mappings_path_for,
    document_id,
    documents,
    iter_cmt_mappings,
    iter_instances_from_annotated,
    iter_mipvu_records,
    iter_sentence_nodes,
    mipvu_path_for,
    read_json,
    segmented_path_for,
    write_json,
)


def referenced_ids(case_id: str) -> tuple[set[str], set[str]]:
    sentence_ids: set[str] = set()
    mipvu_ids: set[str] = set()

    cmt = read_json(cmt_mappings_path_for(case_id), {}) or {}
    for mapping in iter_cmt_mappings(cmt):
        if mapping.get("sentence_id"):
            sentence_ids.add(str(mapping["sentence_id"]))
        mipvu_ids.update(str(value) for value in mapping.get("mipvu_ids", []) if value)

    for doc in documents(case_id):
        data = read_json(annotated_path_for(case_id, doc), {}) or {}
        for instance, container_sentence_id in iter_instances_from_annotated(data):
            sentence_id = instance.get("sentence_id") or container_sentence_id
            if sentence_id:
                sentence_ids.add(str(sentence_id))
            mipvu_ids.update(str(value) for value in instance.get("mipvu_ids", []) if value)

    return sentence_ids, mipvu_ids


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def build_index(case_id: str) -> dict[str, Any]:
    required_sentences, required_mipvu = referenced_ids(case_id)
    sentence_records: dict[str, dict[str, Any]] = {}
    mipvu_records: dict[str, dict[str, Any]] = {}
    artifact_records: list[dict[str, Any]] = []

    for doc in documents(case_id):
        doc_id = document_id(doc)
        segmented_path = segmented_path_for(case_id, doc)
        mipvu_path = mipvu_path_for(case_id, doc)
        if not segmented_path.is_file() or not mipvu_path.is_file():
            raise FileNotFoundError(
                f"{doc_id}: authorized local segmented and MIPVU artifacts are required"
            )

        segmented = read_json(segmented_path, {}) or {}
        for sentence in iter_sentence_nodes(segmented):
            sentence_id = str(sentence.get("sentence_id") or "")
            if sentence_id in required_sentences:
                sentence_records[sentence_id] = {
                    "sentence_id": sentence_id,
                    "document_id": doc_id,
                    "record_sha256": sha256_record(sentence),
                }

        mipvu = read_json(mipvu_path, {}) or {}
        for unit in iter_mipvu_records(mipvu):
            mipvu_id = str(unit.get("mipvu_id") or "")
            if mipvu_id in required_mipvu:
                mipvu_records[mipvu_id] = {
                    "mipvu_id": mipvu_id,
                    "document_id": str(unit.get("document_id") or ""),
                    "sentence_id": str(unit.get("sentence_id") or ""),
                    "decision_type": str(unit.get("decision_type") or ""),
                    "record_sha256": sha256_record(unit),
                }

        artifact_records.append(
            {
                "document_id": doc_id,
                "segmented_artifact": {
                    "path": relative(segmented_path),
                    "sha256": sha256_json_artifact(segmented_path),
                },
                "mipvu_artifact": {
                    "path": relative(mipvu_path),
                    "sha256": sha256_json_artifact(mipvu_path),
                },
            }
        )

    missing_sentences = sorted(required_sentences - sentence_records.keys())
    missing_mipvu = sorted(required_mipvu - mipvu_records.keys())
    if missing_sentences or missing_mipvu:
        details = []
        if missing_sentences:
            details.append(f"{len(missing_sentences)} sentence ID(s)")
        if missing_mipvu:
            details.append(f"{len(missing_mipvu)} MIPVU ID(s)")
        raise ValueError("local artifacts do not resolve " + " and ".join(details))

    return {
        "version": INDEX_VERSION,
        "case_id": case_id,
        "status": "public-safe-reference-index",
        "rights_boundary": {
            "source_text": "local-only",
            "segmented_records": "local-only",
            "mipvu_records": "local-only",
            "public_fields": [
                "stable identifiers",
                "document and sentence relationships",
                "MIPVU decision type",
                "SHA-256 integrity hashes",
            ],
            "prohibited_public_content": "source text, lexical text, glosses, and evidence snippets",
        },
        "artifacts": sorted(artifact_records, key=lambda item: item["document_id"]),
        "sentences": sorted(sentence_records.values(), key=lambda item: item["sentence_id"]),
        "mipvu_units": sorted(mipvu_records.values(), key=lambda item: item["mipvu_id"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, dest="case_id")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    output = args.output or index_path(ROOT, args.case_id)
    write_json(output, build_index(args.case_id))
    print(f"Wrote {output.relative_to(ROOT) if output.is_relative_to(ROOT) else output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
