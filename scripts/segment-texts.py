#!/usr/bin/env python3
"""Segment normalized case texts into stable section/paragraph/sentence JSON."""
from __future__ import annotations

import argparse

from pipeline_common import (
    case_dir,
    case_ids,
    document_id,
    documents,
    now_iso,
    parse_markdown_with_frontmatter,
    segmented_path_for,
    split_sentences,
    text_path_for,
    write_json,
)


def build_segmented_document(case_id: str, doc_id: str, meta: dict, body: str) -> dict:
    word_offset = 0
    char_cursor = 0
    section_id = f"{doc_id}_s01"
    paragraphs = []

    for paragraph_ordinal, paragraph in enumerate(
        [item.strip() for item in body.split("\n\n") if item.strip()],
        start=1,
    ):
        para_id = f"{section_id}_p{paragraph_ordinal:02d}"
        sentences = []
        for sentence_ordinal, sentence in enumerate(split_sentences(paragraph), start=1):
            found_at = body.find(sentence, char_cursor)
            if found_at < 0:
                found_at = char_cursor
            char_end = found_at + len(sentence)
            word_count = len(sentence.split())
            sentences.append(
                {
                    "sentence_id": f"{para_id}_s{sentence_ordinal:02d}",
                    "sentence_ordinal": sentence_ordinal,
                    "text": sentence,
                    "word_offset_start": word_offset,
                    "word_offset_end": word_offset + word_count,
                    "char_offset_start": found_at,
                    "char_offset_end": char_end,
                    "authorship_note": meta.get("authorship_note"),
                    "metaphor_instances": [],
                }
            )
            word_offset += word_count
            char_cursor = char_end
        if sentences:
            paragraphs.append(
                {
                    "paragraph_id": para_id,
                    "paragraph_ordinal": paragraph_ordinal,
                    "sentences": sentences,
                }
            )

    return {
        "case_id": case_id,
        "document_id": doc_id,
        "meta": meta,
        "sections": [
            {
                "section_id": section_id,
                "section_label": "body",
                "section_ordinal": 1,
                "paragraphs": paragraphs,
            }
        ],
        "pipeline_log": [
            {
                "stage": "segment-texts",
                "script": "scripts/segment-texts.py",
                "generated_at": now_iso(),
                "sentence_count": sum(len(p["sentences"]) for p in paragraphs),
            }
        ],
    }


def segment_case(case_id: str, strict: bool = False) -> dict:
    records = []
    written = 0
    skipped = 0
    errors = []

    for doc in documents(case_id):
        doc_id = document_id(doc)
        in_path = text_path_for(case_id, doc)
        out_path = segmented_path_for(case_id, doc)
        if not in_path.exists():
            skipped += 1
            message = f"{case_id}/{doc_id}: missing normalized text at {in_path}"
            if strict:
                errors.append(message)
            records.append(
                {
                    "document_id": doc_id,
                    "status": "skipped_missing_text",
                    "input_path": str(in_path),
                    "output_path": str(out_path),
                }
            )
            continue

        meta, body = parse_markdown_with_frontmatter(in_path.read_text(encoding="utf-8"))
        segmented = build_segmented_document(case_id, doc_id, meta, body)
        write_json(out_path, segmented)
        sentence_count = sum(
            len(paragraph["sentences"])
            for section in segmented["sections"]
            for paragraph in section["paragraphs"]
        )
        written += 1
        records.append(
            {
                "document_id": doc_id,
                "status": "written",
                "sentence_count": sentence_count,
                "input_path": str(in_path),
                "output_path": str(out_path),
            }
        )

    status = {
        "case_id": case_id,
        "stage": "segment-texts",
        "status": "error" if errors else "ready",
        "generated_at": now_iso(),
        "documents_in_manifest": len(documents(case_id)),
        "written": written,
        "skipped_missing_text": skipped,
        "errors": errors,
        "records": records,
    }
    write_json(case_dir(case_id) / "status" / "segmentation-status.json", status)
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", default=None, help="Optional case id")
    parser.add_argument("--strict", action="store_true", help="Fail on missing expected inputs")
    args = parser.parse_args()

    exit_code = 0
    for case_id in case_ids(args.case_id):
        status = segment_case(case_id, strict=args.strict)
        print(
            f"{case_id}: segmented {status['written']} document(s); "
            f"skipped {status['skipped_missing_text']}."
        )
        if status["errors"]:
            exit_code = 1
            for error in status["errors"]:
                print(f"ERROR: {error}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
