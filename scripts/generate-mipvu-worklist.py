#!/usr/bin/env python3
"""Generate MIPVU lexical-unit worklists from segmented documents."""
from __future__ import annotations

import argparse
import re
from typing import Any, Optional

from pipeline_common import (
    case_dir,
    case_ids,
    document_id,
    documents,
    iter_sentence_nodes,
    mipvu_path_for,
    now_iso,
    read_json,
    segmented_path_for,
    write_json,
)

TOKEN_RE = re.compile(r"[^\W_]+(?:[-'’][^\W_]+)*", re.UNICODE)
PRESERVED_FIELDS = {
    "decision_type",
    "contextual_meaning",
    "basic_meaning",
    "basic_meaning_source",
    "contrast_explanation",
    "comparison_basis",
    "confidence",
    "review_notes",
    "gloss_en",
    "gloss_notes",
    "compound_unit_id",
    "semantic_shift_risk",
    "candidate_source_domain",
    "candidate_target_domain",
    "review_batch",
    "annotator",
    "review_status",
}


def metadata_value(key: str, *sources: dict[str, Any], default: str | None = None) -> str | None:
    for source in sources:
        if not isinstance(source, dict):
            continue
        value = source.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def existing_records(path) -> dict[str, dict[str, Any]]:
    data = read_json(path, {}) or {}
    records = data.get("lexical_units", []) if isinstance(data, dict) else []
    return {
        str(item.get("mipvu_id")): item
        for item in records
        if isinstance(item, dict) and item.get("mipvu_id")
    }


def case_config(case_id: str) -> dict[str, Any]:
    data = read_json(case_dir(case_id) / "config" / "case-config.json", {}) or {}
    return data if isinstance(data, dict) else {}


def source_language(meta: dict[str, Any], doc: dict[str, Any], config: dict[str, Any]) -> str:
    return (
        metadata_value("source_language", meta, doc, config)
        or metadata_value("language", meta, doc, config)
        or "en"
    )


def annotation_language_policy(meta: dict[str, Any], doc: dict[str, Any], config: dict[str, Any]) -> str:
    return metadata_value("annotation_language_policy", meta, doc, config) or "source-language"


def lexical_records(
    case_id: str,
    segmented: dict[str, Any],
    doc: dict[str, Any],
    config: dict[str, Any],
    force: bool = False,
) -> list[dict[str, Any]]:
    doc_id = str(segmented.get("document_id") or "")
    meta = segmented.get("meta", {}) if isinstance(segmented.get("meta"), dict) else {}
    language = source_language(meta, doc, config)
    old = {} if force else existing_records(mipvu_path_for(case_id, doc_id))
    records: list[dict[str, Any]] = []
    unit_ordinal = 1

    for sentence in iter_sentence_nodes(segmented):
        sentence_id = str(sentence.get("sentence_id") or "")
        text = str(sentence.get("text") or "")
        sentence_start = sentence.get("char_offset_start")
        absolute_sentence_start = sentence_start if isinstance(sentence_start, int) else 0
        sentence_unit_ordinal = 1

        for match in TOKEN_RE.finditer(text):
            lexical_unit = match.group(0)
            mipvu_id = f"{sentence_id}_lu{sentence_unit_ordinal:03d}"
            record = {
                "mipvu_id": mipvu_id,
                "case_id": case_id,
                "document_id": doc_id,
                "sentence_id": sentence_id,
                "lexical_unit": lexical_unit,
                "lemma": lexical_unit.lower(),
                "language": language,
                "unit_ordinal": unit_ordinal,
                "sentence_unit_ordinal": sentence_unit_ordinal,
                "char_offset_start": absolute_sentence_start + match.start(),
                "char_offset_end": absolute_sentence_start + match.end(),
                "sentence_char_offset_start": match.start(),
                "sentence_char_offset_end": match.end(),
                "review_status": "pending",
            }

            previous = old.get(mipvu_id)
            if previous and previous.get("lexical_unit") == lexical_unit:
                for field in PRESERVED_FIELDS:
                    if field in previous:
                        record[field] = previous[field]

            records.append(record)
            unit_ordinal += 1
            sentence_unit_ordinal += 1

    return records


def generate_case(case_id: str, doc_filter: Optional[str] = None, force: bool = False, strict: bool = False) -> dict:
    records = []
    errors: list[str] = []
    written = 0
    total_units = 0
    config = case_config(case_id)

    for doc in documents(case_id):
        doc_id = document_id(doc)
        if doc_filter and doc_id != doc_filter:
            continue

        segmented_path = segmented_path_for(case_id, doc)
        out_path = mipvu_path_for(case_id, doc)
        if not segmented_path.exists():
            message = f"{case_id}/{doc_id}: missing segmented document at {segmented_path}"
            if strict:
                errors.append(message)
            records.append(
                {
                    "document_id": doc_id,
                    "status": "skipped_missing_segmented",
                    "input_path": str(segmented_path),
                    "output_path": str(out_path),
                }
            )
            continue

        segmented = read_json(segmented_path, {}) or {}
        if not isinstance(segmented, dict):
            errors.append(f"{segmented_path}: segmented document must be an object")
            continue

        units = lexical_records(case_id, segmented, doc, config, force=force)
        meta = segmented.get("meta", {}) if isinstance(segmented.get("meta"), dict) else {}
        language = source_language(meta, doc, config)
        policy = annotation_language_policy(meta, doc, config)
        output_meta = {
            "title": meta.get("title"),
            "short_title": meta.get("short_title"),
            "register": meta.get("register"),
            "date": meta.get("date"),
            "source_url": meta.get("source_url"),
            "annotation_language_policy": policy,
        }
        if config.get("gloss_terms"):
            output_meta["gloss_terms"] = config["gloss_terms"]

        mipvu_doc = {
            "version": "1.0",
            "case_id": case_id,
            "document_id": doc_id,
            "source_language": language,
            "generated_at": now_iso(),
            "status": "worklist",
            "meta": output_meta,
            "lexical_units": units,
            "pipeline_log": [
                {
                    "stage": "generate-mipvu-worklist",
                    "script": "scripts/generate-mipvu-worklist.py",
                    "generated_at": now_iso(),
                    "lexical_unit_count": len(units),
                }
            ],
        }
        write_json(out_path, mipvu_doc)
        written += 1
        total_units += len(units)
        records.append(
            {
                "document_id": doc_id,
                "status": "written",
                "lexical_units": len(units),
                "input_path": str(segmented_path),
                "output_path": str(out_path),
            }
        )

    status = {
        "case_id": case_id,
        "stage": "generate-mipvu-worklist",
        "status": "error" if errors else "ready",
        "generated_at": now_iso(),
        "documents_in_manifest": len(documents(case_id)),
        "written": written,
        "lexical_units": total_units,
        "errors": errors,
        "records": records,
    }
    write_json(case_dir(case_id) / "status" / "mipvu-status.json", status)
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", default=None, help="Optional case id")
    parser.add_argument("--doc", dest="doc_id", default=None, help="Optional document id")
    parser.add_argument("--force", action="store_true", help="Regenerate without preserving previous decisions")
    parser.add_argument("--strict", action="store_true", help="Fail on missing segmented inputs")
    args = parser.parse_args()

    exit_code = 0
    for case_id in case_ids(args.case_id):
        status = generate_case(case_id, doc_filter=args.doc_id, force=args.force, strict=args.strict)
        print(
            f"{case_id}: wrote {status['written']} MIPVU worklist(s); "
            f"{status['lexical_units']} lexical unit(s)."
        )
        if status["errors"]:
            exit_code = 1
            for error in status["errors"]:
                print(f"ERROR: {error}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
