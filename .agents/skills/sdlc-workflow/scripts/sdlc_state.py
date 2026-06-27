#!/usr/bin/env python3
"""Deterministic state helpers for the SDLC workflow skill."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def run(cmd: list[str], cwd: str | None = None) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            cmd,
            cwd=cwd,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        return {"ok": False, "returncode": 127, "stdout": "", "stderr": f"{cmd[0]} not found"}

    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def load_json(cmd: list[str], cwd: str | None = None) -> tuple[Any | None, dict[str, Any]]:
    result = run(cmd, cwd)
    if not result["ok"]:
        return None, result
    try:
        return json.loads(result["stdout"] or "null"), result
    except json.JSONDecodeError as exc:
        result["ok"] = False
        result["stderr"] = f"failed to parse JSON: {exc}"
        return None, result


def issue_pattern(issue: int) -> re.Pattern[str]:
    return re.compile(rf"(^|[^0-9]){re.escape(str(issue))}([^0-9]|$)")


def git_snapshot(issue: int, cwd: str | None) -> dict[str, Any]:
    status = run(["git", "status", "--short", "--branch"], cwd)
    if not status["ok"]:
        return {"available": False, "error": status["stderr"] or status["stdout"]}

    branch_result = run(["git", "branch", "--all", "--format=%(refname:short)"], cwd)
    branches: list[dict[str, str]] = []
    if branch_result["ok"]:
        pattern = issue_pattern(issue)
        for raw_name in branch_result["stdout"].splitlines():
            name = raw_name.strip()
            if not name or not pattern.search(name):
                continue
            kind = "remote" if name.startswith("remotes/") or name.startswith("origin/") else "local"
            branches.append({"name": name, "kind": kind})

    return {
        "available": True,
        "status": status["stdout"].splitlines(),
        "branches_for_issue": branches,
    }


def gh_issue(issue: int, repo: str | None, cwd: str | None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    cmd = [
        "gh",
        "issue",
        "view",
        str(issue),
        "--json",
        "number,title,state,url,milestone,labels,assignees,projectItems,body",
    ]
    if repo:
        cmd.extend(["--repo", repo])
    return load_json(cmd, cwd)


def gh_prs(issue: int, repo: str | None, cwd: str | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cmd = [
        "gh",
        "pr",
        "list",
        "--state",
        "open",
        "--search",
        str(issue),
        "--json",
        "number,title,body,headRefName,baseRefName,state,url,isDraft,reviewDecision,statusCheckRollup",
        "--limit",
        "50",
    ]
    if repo:
        cmd.extend(["--repo", repo])
    data, result = load_json(cmd, cwd)
    pattern = issue_pattern(issue)
    filtered = []
    for pr in data or []:
        haystack = "\n".join(str(pr.get(field) or "") for field in ("title", "body", "headRefName"))
        if f"#{issue}" in haystack or pattern.search(haystack):
            pr.pop("body", None)
            filtered.append(pr)
    return filtered, result


def gh_tracking_issues(milestone: dict[str, Any] | None, repo: str | None, cwd: str | None) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    if not milestone or not milestone.get("title"):
        return [], None

    cmd = [
        "gh",
        "issue",
        "list",
        "--state",
        "open",
        "--label",
        "tracking",
        "--milestone",
        milestone["title"],
        "--json",
        "number,title,url,state,milestone",
        "--limit",
        "20",
    ]
    if repo:
        cmd.extend(["--repo", repo])
    data, result = load_json(cmd, cwd)
    return data or [], result


def continuation(issue_data: dict[str, Any] | None, git_data: dict[str, Any], prs: list[dict[str, Any]]) -> str:
    if not issue_data:
        return "blocked: issue state unavailable"
    if issue_data.get("state") == "CLOSED":
        return "stop: issue is closed"
    if prs:
        return "inspect open PR before changing code"
    if not git_data.get("available"):
        return "blocked: local git state unavailable for branch decision"
    branches = git_data.get("branches_for_issue") or []
    if branches:
        return "inspect existing issue branch before creating new branch"
    return "start issue work from intended base branch"


def compact_checks(checks: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    compacted = []
    for check in checks or []:
        compacted.append(
            {
                "name": check.get("name") or check.get("context"),
                "status": check.get("status"),
                "conclusion": check.get("conclusion"),
            }
        )
    return compacted


def inspect_issue(args: argparse.Namespace) -> int:
    cwd = str(Path(args.cwd).resolve()) if args.cwd else None
    issue_data, issue_result = gh_issue(args.issue, args.repo, cwd)
    git_data = git_snapshot(args.issue, cwd)
    prs, pr_result = gh_prs(args.issue, args.repo, cwd)
    tracking, tracking_result = gh_tracking_issues((issue_data or {}).get("milestone"), args.repo, cwd)

    for pr in prs:
        pr["statusCheckRollup"] = compact_checks(pr.get("statusCheckRollup"))

    report = {
        "issue": issue_data,
        "git": git_data,
        "open_prs": prs,
        "tracking_issues": tracking,
        "recommended_continuation": continuation(issue_data, git_data, prs),
        "command_status": {
            "issue": command_summary(issue_result),
            "prs": command_summary(pr_result),
            "tracking": command_summary(tracking_result),
        },
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text_report(report)

    return 0 if issue_data else 1


def command_summary(result: dict[str, Any] | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "ok": result["ok"],
        "returncode": result["returncode"],
        "stderr": result["stderr"],
    }


def print_text_report(report: dict[str, Any]) -> None:
    issue = report["issue"] or {}
    milestone = issue.get("milestone") or {}
    labels = ", ".join(label.get("name", "") for label in issue.get("labels", [])) or "none"

    print(f"Issue: #{issue.get('number', '?')} {issue.get('title', '(unavailable)')}")
    print(f"State: {issue.get('state', 'unknown')}")
    print(f"URL: {issue.get('url', 'unknown')}")
    print(f"Milestone: {milestone.get('title') or 'none'}")
    print(f"Labels: {labels}")
    print(f"Recommended continuation: {report['recommended_continuation']}")

    git_data = report["git"]
    print("\nGit:")
    if git_data.get("available"):
        print("  Status:")
        for line in git_data.get("status", []):
            print(f"    {line}")
        print("  Branches for issue:")
        branches = git_data.get("branches_for_issue") or []
        if branches:
            for branch in branches:
                print(f"    {branch['kind']}: {branch['name']}")
        else:
            print("    none")
    else:
        print(f"  unavailable: {git_data.get('error')}")

    print("\nOpen PRs matching issue:")
    if report["open_prs"]:
        for pr in report["open_prs"]:
            print(
                f"  #{pr['number']} {pr['title']} "
                f"({pr['headRefName']} -> {pr['baseRefName']}, draft={pr['isDraft']})"
            )
            print(f"    reviewDecision={pr.get('reviewDecision')} url={pr['url']}")
            for check in pr.get("statusCheckRollup", []):
                print(f"    check {check['name']}: {check['status']} / {check['conclusion']}")
    else:
        print("  none")

    print("\nOpen same-milestone tracking issues:")
    if report["tracking_issues"]:
        for item in report["tracking_issues"]:
            print(f"  #{item['number']} {item['title']} {item['url']}")
    else:
        print("  none")


def tracker_entry(args: argparse.Namespace) -> int:
    checked = "x" if args.state.lower() == "closed" else " "
    title = args.title.strip()
    prefix = f"#{args.issue}"
    entry = f"- [{checked}] {prefix}"
    if title:
        entry += f" {title}"
    if args.url:
        entry += f" ({args.url})"
    if args.note:
        entry += f" - {args.note.strip()}"
    print(entry)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect deterministic SDLC workflow state from git and GitHub.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect = subparsers.add_parser(
        "inspect-issue",
        help="Report issue, branch, PR, and same-milestone tracking state.",
    )
    inspect.add_argument("issue", type=int, help="GitHub issue number")
    inspect.add_argument("--repo", help="GitHub repository in OWNER/REPO form")
    inspect.add_argument("--cwd", help="Git checkout to inspect; defaults to current directory")
    inspect.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    inspect.set_defaults(func=inspect_issue)

    tracker = subparsers.add_parser(
        "tracker-entry",
        help="Format a deterministic tracking checklist entry for an issue.",
    )
    tracker.add_argument("issue", type=int, help="GitHub issue number")
    tracker.add_argument("--title", default="", help="Issue title")
    tracker.add_argument("--state", choices=("open", "closed"), default="open", help="Issue state")
    tracker.add_argument("--url", help="Issue URL")
    tracker.add_argument("--note", help="Short tracker note to append")
    tracker.set_defaults(func=tracker_entry)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
