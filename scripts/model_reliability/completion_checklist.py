#!/usr/bin/env python3
"""Evaluate and optionally write the final model-reliability completion gate."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from scripts.model_reliability.boundaries import safe_output_path
    from scripts.model_reliability.status import evaluate_case
except ModuleNotFoundError:
    from boundaries import safe_output_path  # type: ignore
    from status import evaluate_case  # type: ignore


ROOT = Path(__file__).resolve().parents[2]
GENERATOR = "scripts/model_reliability/completion_checklist.py"
REPOSITORY_COMMANDS = (
    "npm run status",
    "npm run validate",
    "npm run pipeline",
    "quarto render",
)
REQUIRED_ARTIFACTS = (
    "comparisons/agreement-results.json",
    "comparisons/agreement-summary.csv",
    "comparisons/disagreement-log.json",
    "comparisons/disagreement-log.csv",
    "comparisons/instability-report.md",
    "review-queue/model-review-queue.json",
    "review-queue/model-review-queue.csv",
    "comparisons/consensus-report.json",
    "comparisons/consensus-report.md",
    "codebook/codebook-revision-notes.json",
    "codebook/codebook-revision-notes.md",
)
REQUIRED_DOCUMENTATION = (
    "model-reliability-methodology.qmd",
    "model-reliability-results.qmd",
    "publication/model-reliability.md",
    "docs/reliability/external-model-review-procedures.md",
    "docs/reliability/model-reliability-governance.md",
    "docs/reliability/model-reliability-completion-checklist.md",
)


def _read_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _check(
    check_id: str,
    category: str,
    passed: bool,
    detail: str,
    evidence: Sequence[str],
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "category": category,
        "status": "pass" if passed else "fail",
        "detail": detail,
        "evidence": list(evidence),
    }


def _task_layers(agreement: Mapping[str, Any] | None) -> set[str]:
    layers: set[str] = set()
    if agreement is None:
        return layers
    families = agreement.get("comparison_families")
    if not isinstance(families, Mapping):
        return layers
    for family, container_key in (
        ("model_vs_model", "pairs"),
        ("model_vs_reference", "runs"),
    ):
        section = families.get(family)
        containers = section.get(container_key) if isinstance(section, Mapping) else []
        if not isinstance(containers, list):
            continue
        for container in containers:
            summaries = container.get("summaries") if isinstance(container, Mapping) else []
            if not isinstance(summaries, list):
                continue
            for summary in summaries:
                layer = summary.get("task_layer") if isinstance(summary, Mapping) else None
                if isinstance(layer, str) and layer:
                    layers.add(layer)
    return layers


def run_repository_validation(root: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for command in REPOSITORY_COMMANDS:
        completed = subprocess.run(
            command,
            cwd=root,
            shell=True,
            text=True,
            capture_output=True,
            check=False,
        )
        results.append(
            {
                "command": command,
                "status": "pass" if completed.returncode == 0 else "fail",
                "exit_code": completed.returncode,
            }
        )
        if completed.returncode != 0:
            break
    return results


def evaluate_completion(
    root: Path,
    case_id: str,
    *,
    repository_results: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    case_root = root / "cases" / case_id
    model_root = case_root / "quality" / "model-reliability"
    status = evaluate_case(root, case_id)
    checks: list[dict[str, Any]] = []

    run_count = status.get("counts", {}).get("valid_runs", 0)
    checks.append(
        _check(
            "validated-runs",
            "artifacts",
            status.get("valid") is True and isinstance(run_count, int) and run_count >= 2,
            f"{run_count} validated run(s); at least two are required.",
            ["quality/model-reliability/status.json"],
        )
    )

    missing_artifacts = [
        relative for relative in REQUIRED_ARTIFACTS if not (model_root / relative).is_file()
    ]
    checks.append(
        _check(
            "required-artifacts",
            "artifacts",
            not missing_artifacts,
            (
                "All required comparison, disagreement, queue, and report artifacts exist."
                if not missing_artifacts
                else "Missing: " + ", ".join(missing_artifacts)
            ),
            [f"quality/model-reliability/{item}" for item in REQUIRED_ARTIFACTS],
        )
    )

    agreement_path = model_root / "comparisons" / "agreement-results.json"
    layers = _task_layers(_read_object(agreement_path))
    checks.append(
        _check(
            "layered-metrics",
            "artifacts",
            bool(layers),
            (
                "Layered diagnostics present for: " + ", ".join(sorted(layers))
                if layers
                else "No layered agreement diagnostics are available."
            ),
            ["quality/model-reliability/comparisons/agreement-results.json"],
        )
    )

    report_path = model_root / "comparisons" / "consensus-report.json"
    report = _read_object(report_path)
    authority = report.get("authority") if isinstance(report, Mapping) else None
    authority_passed = (
        isinstance(authority, Mapping)
        and authority.get("consensus_is_evidence") is False
        and authority.get("decision_authority") == "human-only"
    )
    checks.append(
        _check(
            "consensus-authority",
            "protected-paths",
            authority_passed,
            (
                "Consensus is diagnostic and decision authority is human-only."
                if authority_passed
                else "Consensus authority fields are missing or unsafe."
            ),
            ["quality/model-reliability/comparisons/consensus-report.json"],
        )
    )

    queue_path = model_root / "review-queue" / "model-review-queue.json"
    queue = _read_object(queue_path)
    entries = queue.get("entries", []) if isinstance(queue, Mapping) else []
    queue_passed = isinstance(entries, list) and all(
        isinstance(entry, Mapping)
        and entry.get("decision_authority") == "human-only"
        and entry.get("review_status") == "pending-human-review"
        and not any(
            prohibited in entry
            for prohibited in ("accepted_value", "adjudication_decision", "majority_decision")
        )
        for entry in entries
    )
    checks.append(
        _check(
            "review-queue-authority",
            "protected-paths",
            queue_passed,
            (
                "Review candidates remain pending with human-only authority."
                if queue_passed
                else "The review queue contains an automatic or accepted decision."
            ),
            ["quality/model-reliability/review-queue/model-review-queue.json"],
        )
    )

    guard_files = (
        "scripts/model_reliability/boundaries.py",
        "test/test_model_reliability_boundaries.py",
    )
    guard_passed = all((root / relative).is_file() for relative in guard_files)
    checks.append(
        _check(
            "protected-write-guard",
            "protected-paths",
            guard_passed,
            (
                "Protected-write enforcement and regression tests are present."
                if guard_passed
                else "Protected-write enforcement or its regression test is missing."
            ),
            list(guard_files),
        )
    )

    missing_docs = [
        relative for relative in REQUIRED_DOCUMENTATION if not (root / relative).is_file()
    ]
    checks.append(
        _check(
            "required-documentation",
            "documentation",
            not missing_docs,
            (
                "Method, results, governance, procedures, publication, and gate documentation exist."
                if not missing_docs
                else "Missing: " + ", ".join(missing_docs)
            ),
            list(REQUIRED_DOCUMENTATION),
        )
    )

    command_by_name = {
        str(result.get("command")): result
        for result in (repository_results or [])
        if isinstance(result, Mapping)
    }
    repository_checks: list[dict[str, Any]] = []
    for command in REPOSITORY_COMMANDS:
        result = command_by_name.get(command)
        passed = (
            isinstance(result, Mapping)
            and result.get("status") == "pass"
            and result.get("exit_code") == 0
        )
        repository_checks.append(
            {
                "command": command,
                "status": "pass" if passed else "not-passed",
                "exit_code": result.get("exit_code") if isinstance(result, Mapping) else None,
            }
        )
    repository_passed = all(item["status"] == "pass" for item in repository_checks)
    checks.append(
        _check(
            "repository-validation",
            "repository",
            repository_passed,
            (
                "All required repository validation commands passed."
                if repository_passed
                else "Run the completion command with --run-repository-validation."
            ),
            list(REPOSITORY_COMMANDS),
        )
    )

    failed = [item["check_id"] for item in checks if item["status"] != "pass"]
    run_ids = report.get("run_ids", []) if isinstance(report, Mapping) else []
    return {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "generator": GENERATOR,
        "status": "complete" if not failed else "blocked",
        "run_ids": sorted(run_ids) if isinstance(run_ids, list) else [],
        "authority": {
            "consensus_changes_accepted_annotations": False,
            "decision_authority": "human-only",
        },
        "required_commands": repository_checks,
        "checks": checks,
        "summary": {
            "check_count": len(checks),
            "passed_count": len(checks) - len(failed),
            "failed_count": len(failed),
            "failed_check_ids": failed,
        },
    }


def render_completion(report: Mapping[str, Any]) -> str:
    lines = [
        "# Model Reliability Completion Checklist",
        "",
        f"Status: **{report['status']}**.",
        "",
        "This is a milestone-readiness gate, not evidence that model consensus is",
        "correct. Accepted annotations can change only through separate human",
        "review and authorization.",
        "",
        "## Gate checks",
        "",
    ]
    for check in report["checks"]:
        marker = "x" if check["status"] == "pass" else " "
        lines.append(f"- [{marker}] **{check['check_id']}** — {check['detail']}")
    lines.extend(["", "## Required repository commands", ""])
    for command in report["required_commands"]:
        marker = "x" if command["status"] == "pass" else " "
        lines.append(f"- [{marker}] `{command['command']}`")
    lines.extend(
        [
            "",
            "A complete report requires every artifact, authority, documentation,",
            "protected-path, and repository-validation check to pass.",
            "",
        ]
    )
    return "\n".join(lines)


def write_completion(
    root: Path,
    case_id: str,
    report: Mapping[str, Any],
) -> tuple[Path, Path]:
    case_root = root.resolve() / "cases" / case_id
    json_path = safe_output_path(
        case_root,
        "quality/model-reliability/completion/completion-checklist.json",
    )
    markdown_path = safe_output_path(
        case_root,
        "quality/model-reliability/completion/completion-checklist.md",
    )
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_completion(report), encoding="utf-8")
    return json_path, markdown_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run-repository-validation", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    repository_results = (
        run_repository_validation(args.root.resolve())
        if args.run_repository_validation
        else None
    )
    report = evaluate_completion(
        args.root,
        args.case_id,
        repository_results=repository_results,
    )
    if args.write:
        write_completion(args.root, args.case_id, report)
    print(
        f"{args.case_id}: completion gate is `{report['status']}`; "
        f"{report['summary']['failed_count']} check(s) failed"
    )
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
