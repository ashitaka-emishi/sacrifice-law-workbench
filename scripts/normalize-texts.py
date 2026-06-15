#!/usr/bin/env python3
"""Normalize case raw texts into Markdown with YAML frontmatter."""
from __future__ import annotations

import argparse
import re

from pipeline_common import (
    case_ids,
    document_id,
    documents,
    frontmatter_for,
    raw_path_for,
    text_path_for,
    write_json,
    case_dir,
    now_iso,
)

_HEADER_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_\s]+:")
_SEPARATOR_RE = re.compile(r"^={4,}\s*$")
_CONTINUATION_RE = re.compile(r"^\s+\S")


def strip_provenance_header(text: str) -> str:
    """Strip the acquisition provenance block from the top of a raw corpus file.

    Handles two layouts:
      - KEY: value lines (with optional indented continuations), then blank line(s)
      - Free prose lines followed by a ====...==== separator line

    Returns the document body text, stripped.
    """
    lines = text.split("\n")

    # If a === separator exists in the first 30 lines, use it as the definitive boundary.
    for sep_idx in range(min(30, len(lines))):
        if _SEPARATOR_RE.match(lines[sep_idx]):
            return "\n".join(lines[sep_idx + 1:]).strip()

    # Otherwise: skip KEY: lines (with optional indented continuations) until a blank
    # line that is NOT followed by another KEY: line, then return the rest.
    i = 0
    while i < len(lines):
        line = lines[i]
        if _HEADER_KEY_RE.match(line) or _CONTINUATION_RE.match(line):
            i += 1
            continue
        if line.strip() == "":
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines) and (_HEADER_KEY_RE.match(lines[j]) or _CONTINUATION_RE.match(lines[j])):
                i = j
                continue
            i += 1
            break
        break
    return "\n".join(lines[i:]).strip()


def normalize_case(case_id: str, strict: bool = False) -> dict:
    records = []
    written = 0
    skipped = 0
    errors = []

    for doc in documents(case_id):
        doc_id = document_id(doc)
        raw_path = raw_path_for(case_id, doc)
        out_path = text_path_for(case_id, doc)
        if not doc_id:
            errors.append("Manifest document missing document_id/id")
            continue
        if not raw_path.exists():
            skipped += 1
            message = f"{case_id}/{doc_id}: missing raw text at {raw_path}"
            if strict:
                errors.append(message)
            records.append(
                {
                    "document_id": doc_id,
                    "status": "skipped_missing_raw",
                    "raw_path": str(raw_path),
                    "output_path": str(out_path),
                }
            )
            continue

        body = strip_provenance_header(raw_path.read_text(encoding="utf-8"))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(frontmatter_for(case_id, doc, raw_path) + body + "\n", encoding="utf-8")
        written += 1
        records.append(
            {
                "document_id": doc_id,
                "status": "written",
                "raw_path": str(raw_path),
                "output_path": str(out_path),
            }
        )

    status = {
        "case_id": case_id,
        "stage": "normalize-texts",
        "status": "error" if errors else "ready",
        "generated_at": now_iso(),
        "documents_in_manifest": len(documents(case_id)),
        "written": written,
        "skipped_missing_raw": skipped,
        "errors": errors,
        "records": records,
    }
    write_json(case_dir(case_id) / "status" / "normalization-status.json", status)
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", default=None, help="Optional case id")
    parser.add_argument("--strict", action="store_true", help="Fail on missing expected inputs")
    args = parser.parse_args()

    exit_code = 0
    for case_id in case_ids(args.case_id):
        status = normalize_case(case_id, strict=args.strict)
        print(
            f"{case_id}: normalized {status['written']} document(s); "
            f"skipped {status['skipped_missing_raw']}."
        )
        if status["errors"]:
            exit_code = 1
            for error in status["errors"]:
                print(f"ERROR: {error}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
