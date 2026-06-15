#!/usr/bin/env python3
"""Report acquisition status for all sources in a case source registry.

Reads cases/<case>/metadata/source-registry.json and checks each source
against its expected_local_path to produce an acquisition status report.
Does not download or modify any files — acquisition is user-assisted per
the rights policy and interactive-acquisition-prompt.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline_common import ROOT, CASES_ROOT, case_ids, now_iso, read_json, write_json

REGISTRY_PATH = "metadata/source-registry.json"

RIGHTS_GATE = {
    "committed": "ready-to-ingest",
    "gitignored-local": "acquire-and-store-locally",
    "metadata-only": "resolve-rights-before-ingestion",
    "unavailable": "source-unavailable",
}


def load_registry(case_id: str) -> dict:
    path = CASES_ROOT / case_id / REGISTRY_PATH
    data = read_json(path, {}) or {}
    return data


def check_source(case_id: str, source: dict) -> dict:
    source_id = source.get("source_id", "unknown")
    git_tracking = source.get("git_tracking", "")
    expected = source.get("expected_local_path", "")
    rights_status = source.get("rights_status", "unknown")
    analytical_priority = source.get("analytical_priority", "unknown")

    # Resolve expected path relative to repo root
    local_path: Path | None = None
    path_exists = False
    if expected:
        candidate = Path(expected)
        if not candidate.is_absolute():
            candidate = ROOT / candidate
        local_path = candidate
        path_exists = candidate.exists() and (
            candidate.is_file() or (candidate.is_dir() and any(candidate.iterdir()))
        )

    acquisition_action = RIGHTS_GATE.get(git_tracking, "check-rights-policy")

    if path_exists:
        local_status = "present"
    elif git_tracking in ("metadata-only", "unavailable"):
        local_status = "not-applicable"
    else:
        local_status = "missing"

    blockers = []
    if rights_status in ("rights-unclear", "restricted"):
        blockers.append(f"rights-status={rights_status}")
    if rights_status == "translation-risk":
        blockers.append("translation-copyright-must-be-verified")
    for flag in source.get("risk_flags", []) or []:
        if "copyright" in flag or "unresolved" in flag:
            blockers.append(flag)

    return {
        "source_id": source_id,
        "title": source.get("short_title") or source.get("title", ""),
        "phase": source.get("phase", ""),
        "register": source.get("register", ""),
        "analytical_priority": analytical_priority,
        "rights_status": rights_status,
        "git_tracking": git_tracking,
        "acquisition_action": acquisition_action,
        "local_status": local_status,
        "expected_local_path": expected,
        "blockers": blockers,
        "source_url": source.get("source_url", ""),
    }


def report_case(case_id: str) -> dict:
    registry = load_registry(case_id)
    sources = registry.get("sources", []) or []

    if not sources:
        return {
            "case_id": case_id,
            "registry_status": registry.get("status", "missing"),
            "source_count": 0,
            "sources": [],
            "summary": {"ready": 0, "needs-acquisition": 0, "blocked": 0, "not-applicable": 0},
        }

    checked = [check_source(case_id, s) for s in sources]

    summary = {"ready": 0, "needs-acquisition": 0, "blocked": 0, "not-applicable": 0}
    for s in checked:
        if s["local_status"] == "present":
            summary["ready"] += 1
        elif s["local_status"] == "not-applicable":
            summary["not-applicable"] += 1
        elif s["blockers"]:
            summary["blocked"] += 1
        else:
            summary["needs-acquisition"] += 1

    return {
        "case_id": case_id,
        "registry_status": registry.get("status", "draft"),
        "source_count": len(checked),
        "sources": checked,
        "summary": summary,
    }


def print_report(reports: list[dict]) -> None:
    for report in reports:
        case_id = report["case_id"]
        s = report["summary"]
        print(f"\n=== {case_id} ({report['source_count']} sources) ===")
        print(f"  ready={s['ready']}  needs-acquisition={s['needs-acquisition']}  blocked={s['blocked']}  not-applicable={s['not-applicable']}")
        for src in report["sources"]:
            status_tag = (
                "READY"
                if src["local_status"] == "present"
                else "N/A"
                if src["local_status"] == "not-applicable"
                else "BLOCKED"
                if src["blockers"]
                else "MISSING"
            )
            print(f"  [{status_tag:7s}] {src['source_id']}")
            print(f"           rights={src['rights_status']}  tracking={src['git_tracking']}  priority={src['analytical_priority']}")
            print(f"           action: {src['acquisition_action']}")
            if src["blockers"]:
                print(f"           blockers: {', '.join(src['blockers'])}")
            if src["local_status"] not in ("present", "not-applicable"):
                print(f"           url: {src['source_url']}")
                print(f"           path: {src['expected_local_path']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", default=None, help="Limit to one case id")
    parser.add_argument("--json", dest="output_json", action="store_true", help="Output JSON instead of text report")
    args = parser.parse_args()

    ids = case_ids(args.case_id)
    if not ids:
        print("No cases found.", file=sys.stderr)
        return 1

    reports = [report_case(c) for c in ids if c != "x-case"]

    if args.output_json:
        print(json.dumps({"generated_at": now_iso(), "cases": reports}, indent=2, ensure_ascii=False))
    else:
        print_report(reports)
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
