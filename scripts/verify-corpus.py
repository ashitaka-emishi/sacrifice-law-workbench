#!/usr/bin/env python3
"""Verify downloaded corpus files are present, non-trivial, and contain the correct content.

For each document in a case manifest, checks:
  1. FILE PRESENT   — expected_raw_path exists and is non-empty
  2. WORD COUNT     — body word count >= verification.min_words
  3. PHRASES        — all strings in verification.required_phrases appear in the file

The verification spec lives in each document entry under a "verification" key:

  "verification": {
    "min_words": 1100,
    "required_phrases": ["We hold these truths", "sacred Honor"]
  }

Documents without a "verification" key get a file-present check only (with a warning).

Usage:
  python3 scripts/verify-corpus.py                  # all cases
  python3 scripts/verify-corpus.py --case hitler     # one case
  python3 scripts/verify-corpus.py --json            # machine-readable output
  python3 scripts/verify-corpus.py --fail-fast       # exit 1 on first failure
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline_common import ROOT, CASES_ROOT, case_ids, now_iso, documents, raw_path_for

PROVENANCE_SEPARATORS = ("=" * 20, "SOURCE:", "EXTRACTION", "TITRE:", "---\n")


def body_text(text: str) -> str:
    """Strip provenance header (everything before the ==== separator line)."""
    for sep in ("=" * 20, "========"):
        idx = text.find(sep)
        if idx >= 0:
            after = text[idx + len(sep):]
            return after.lstrip("\n")
    return text


def check_document(case_id: str, doc: dict) -> dict:
    doc_id = doc.get("document_id", "unknown")
    raw = raw_path_for(case_id, doc)
    spec = doc.get("verification") or {}

    result: dict = {
        "document_id": doc_id,
        "path": str(raw.relative_to(ROOT) if raw.is_relative_to(ROOT) else raw),
        "checks": {},
        "status": "PASS",
        "warnings": [],
    }

    # --- Check 1: file present and non-empty ---
    if not raw.exists():
        result["checks"]["file_present"] = {"status": "FAIL", "detail": "file not found"}
        result["status"] = "FAIL"
        return result
    if raw.stat().st_size == 0:
        result["checks"]["file_present"] = {"status": "FAIL", "detail": "file is empty (0 bytes)"}
        result["status"] = "FAIL"
        return result
    result["checks"]["file_present"] = {"status": "PASS"}

    text = raw.read_text(encoding="utf-8", errors="replace")
    body = body_text(text)
    word_count = len(body.split())
    result["word_count"] = word_count

    if not spec:
        result["warnings"].append("no verification spec — file-present check only")
        return result

    # --- Check 2: minimum word count ---
    min_words = spec.get("min_words", 0)
    if min_words:
        if word_count >= min_words:
            result["checks"]["min_words"] = {
                "status": "PASS",
                "detail": f"{word_count} words >= {min_words}",
            }
        else:
            result["checks"]["min_words"] = {
                "status": "FAIL",
                "detail": f"{word_count} words < required {min_words}",
            }
            result["status"] = "FAIL"

    # --- Check 3: required phrases ---
    phrases = spec.get("required_phrases") or []
    phrase_results = {}
    for phrase in phrases:
        found = phrase in text
        phrase_results[phrase] = "PASS" if found else "FAIL"
        if not found:
            result["status"] = "FAIL"
    if phrases:
        result["checks"]["required_phrases"] = {
            "status": "PASS" if all(v == "PASS" for v in phrase_results.values()) else "FAIL",
            "phrases": phrase_results,
        }

    return result


def verify_case(case_id: str) -> dict:
    docs = documents(case_id)
    results = [check_document(case_id, doc) for doc in docs]
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    warned = sum(1 for r in results if r["warnings"])
    return {
        "case_id": case_id,
        "document_count": len(results),
        "passed": passed,
        "failed": failed,
        "warned": warned,
        "overall": "PASS" if failed == 0 else "FAIL",
        "documents": results,
    }


def print_report(reports: list[dict]) -> None:
    any_fail = False
    for report in reports:
        case_id = report["case_id"]
        overall = report["overall"]
        print(f"\n{'='*60}")
        print(f"  {case_id}  [{overall}]  ({report['passed']}/{report['document_count']} passed)")
        print(f"{'='*60}")
        for doc in report["documents"]:
            status = doc["status"]
            doc_id = doc["document_id"]
            wc = doc.get("word_count", "—")
            marker = "PASS" if status == "PASS" else "FAIL"
            print(f"  [{marker}] {doc_id}  ({wc} words)")
            for check_name, check in doc.get("checks", {}).items():
                cs = check.get("status", "?")
                detail = check.get("detail", "")
                if cs == "FAIL":
                    print(f"         ✗ {check_name}: {detail}")
                    if check_name == "required_phrases":
                        for phrase, ps in check.get("phrases", {}).items():
                            if ps == "FAIL":
                                print(f"             missing: {phrase!r}")
            for w in doc.get("warnings", []):
                print(f"         ⚠ {w}")
            if status == "FAIL":
                any_fail = True
    print()
    if any_fail:
        print("RESULT: FAIL — one or more documents did not pass verification.")
    else:
        print("RESULT: PASS — all documents verified.")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", default=None)
    parser.add_argument("--json", dest="output_json", action="store_true")
    parser.add_argument("--fail-fast", dest="fail_fast", action="store_true")
    args = parser.parse_args()

    ids = [c for c in case_ids(args.case_id) if c != "x-case"]
    if not ids:
        print("No cases found.", file=sys.stderr)
        return 1

    reports = []
    for cid in ids:
        report = verify_case(cid)
        reports.append(report)
        if args.fail_fast and report["overall"] == "FAIL":
            break

    if args.output_json:
        print(json.dumps({"generated_at": now_iso(), "cases": reports}, indent=2, ensure_ascii=False))
    else:
        print_report(reports)

    overall_fail = any(r["overall"] == "FAIL" for r in reports)
    return 1 if overall_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
