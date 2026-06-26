#!/usr/bin/env python3
"""Generate governed codebook revision notes from human reliability results."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

try:
    from scripts.human_reliability.boundaries import protect_accepted_artifacts, safe_output_path
    from scripts.human_reliability.ingest_submission import cohort_hash
except ModuleNotFoundError:
    from boundaries import protect_accepted_artifacts, safe_output_path  # type: ignore
    from ingest_submission import cohort_hash  # type: ignore


ROOT = Path(__file__).resolve().parents[2]
GENERATOR_PATH = "scripts/human_reliability/generate_codebook_notes.py"
GENERATOR_VERSION = "1.0.0"
DISPOSITIONS = {"accepted", "rejected", "deferred"}
ACTION_PRIORITY = {
    "none": 0,
    "training_update": 1,
    "clarification": 2,
    "revision": 3,
    "unresolved": 4,
}


class HumanCodebookNotesError(ValueError):
    """Raised when human reliability evidence or governance is inconsistent."""


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HumanCodebookNotesError(
            f"{path}: unable to read JSON: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise HumanCodebookNotesError(f"{path}: expected a JSON object")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _validate(root: Path, value: Mapping[str, Any], schema_name: str) -> None:
    schema_path = root / "schemas" / "human-reliability" / schema_name
    if not schema_path.is_file():
        schema_path = ROOT / "schemas" / "human-reliability" / schema_name
    schema = read_object(schema_path)
    errors = sorted(
        Draft202012Validator(
            schema, format_checker=FormatChecker()
        ).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        location = ".".join(str(part) for part in errors[0].absolute_path)
        prefix = f"{location}: " if location else ""
        raise HumanCodebookNotesError(
            f"{schema_name} validation failed: {prefix}{errors[0].message}"
        )


def _artifact(path: Path, root: Path) -> dict[str, str]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_bytes(path.read_bytes()),
    }


def _cohorts(root: Path, case_id: str) -> dict[tuple[str, str], dict[str, Any]]:
    case_root = root / "cases" / case_id
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted(
        (case_root / "quality" / "human-reliability" / "cohorts").glob(
            "*.json"
        )
    ):
        cohort = read_object(path)
        _validate(root, cohort, "cohort-manifest-schema.json")
        if cohort.get("case_id") != case_id:
            raise HumanCodebookNotesError(
                f"{path}: cohort case does not match requested case"
            )
        if cohort["approval"]["manifest_sha256"] != cohort_hash(cohort):
            raise HumanCodebookNotesError(
                f"{path}: cohort approval hash does not match canonical content"
            )
        key = (str(cohort["cohort_id"]), str(cohort["cohort_version"]))
        if key in result:
            raise HumanCodebookNotesError(
                f"duplicate approved cohort `{key[0]}` `{key[1]}`"
            )
        result[key] = cohort
    return result


def _identity(
    value: Mapping[str, Any],
    cohort: Mapping[str, Any],
    label: str,
) -> None:
    for key in (
        "case_id",
        "cohort_id",
        "cohort_version",
        "source_language",
        "task_layer",
    ):
        if value.get(key) != cohort.get(key):
            raise HumanCodebookNotesError(
                f"{label}: `{key}` does not match the approved cohort"
            )


def _verify_disagreement_generator(
    root: Path, value: Mapping[str, Any]
) -> None:
    generator = value.get("generator")
    expected = "scripts/human_reliability/classify_disagreements.py"
    if not isinstance(generator, Mapping) or generator.get("script") != expected:
        raise HumanCodebookNotesError(
            "disagreement log has an unexpected generator"
        )
    path = root / expected
    if not path.is_file():
        path = ROOT / expected
    if generator.get("script_hash") != sha256_bytes(path.read_bytes()):
        raise HumanCodebookNotesError(
            "disagreement log generator hash is stale"
        )


def _governance(
    root: Path, case_id: str, path: Path
) -> dict[str, Mapping[str, Any]]:
    if not path.is_file():
        return {}
    value = read_object(path)
    _validate(root, value, "codebook-recommendation-decisions-schema.json")
    if value["case_id"] != case_id:
        raise HumanCodebookNotesError(
            "recommendation decision register case does not match"
        )
    result: dict[str, Mapping[str, Any]] = {}
    for decision in value["decisions"]:
        recommendation_id = str(decision["recommendation_id"])
        if recommendation_id in result:
            raise HumanCodebookNotesError(
                f"duplicate governance decision for `{recommendation_id}`"
            )
        result[recommendation_id] = decision
    return result


def _recommendation_id(
    case_id: str,
    source_language: str,
    task_layer: str,
    field: str,
) -> str:
    identity = json.dumps(
        {
            "case_id": case_id,
            "source_language": source_language,
            "task_layer": task_layer,
            "field": field,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "human-codebook-rec-" + hashlib.sha256(identity).hexdigest()[:16]


def _recommendation_hash(
    recommendation_id: str, finding: Mapping[str, Any]
) -> str:
    payload = {
        "recommendation_id": recommendation_id,
        **dict(finding),
    }
    return sha256_bytes(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _recommended_change(action: str, field: str) -> str:
    if action == "revision":
        return (
            f"Revise the decision rule for `{field}` with contrastive "
            "source-language examples and explicit edge-case criteria."
        )
    if action == "clarification":
        return (
            f"Clarify the existing rule for `{field}` with inclusion, "
            "exclusion, and uncertainty examples."
        )
    if action == "training_update":
        return (
            f"Add a calibration exercise for `{field}` using reviewed "
            "contrastive examples without exposing reliability answers."
        )
    if action == "unresolved":
        return (
            f"Hold changes to `{field}` pending additional source-language "
            "evidence and an explicit methodological decision."
        )
    return (
        f"Review the decision rule for `{field}`; repeated disagreement "
        "suggests possible ambiguity but adjudication has not requested a change."
    )


def _migration(action: str, recoding_required: bool) -> str:
    if recoding_required:
        return (
            "A separately authorized migration must identify affected cohorts, "
            "freeze the new codebook version, and explicitly schedule re-coding."
        )
    if action in {"revision", "clarification"}:
        return (
            "Apply only in a new codebook version; existing decisions remain "
            "unchanged unless a separate migration is approved."
        )
    if action == "training_update":
        return (
            "Update future training or calibration materials only; prior "
            "coding remains unchanged."
        )
    return "No migration is authorized by this note."


def _collect_evidence(
    root: Path,
    case_id: str,
    cohorts: Mapping[tuple[str, str], Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, str]], str]:
    case_root = root / "cases" / case_id
    comparison_root = case_root / "quality" / "human-reliability" / "comparisons"
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    artifacts: list[dict[str, str]] = []
    storage_policy = "repository_allowed"
    for path in sorted(comparison_root.glob("*/disagreement-log.json")):
        log = read_object(path)
        _validate(root, log, "disagreement-log-schema.json")
        _verify_disagreement_generator(root, log)
        key = (str(log["cohort_id"]), str(log["cohort_version"]))
        cohort = cohorts.get(key)
        if cohort is None:
            raise HumanCodebookNotesError(
                f"{path}: no matching approved cohort"
            )
        _identity(log, cohort, "disagreement log")
        artifacts.append(_artifact(path, root))
        if cohort["storage_policy"] == "local_only":
            storage_policy = "local_only"
        results_path = (
            case_root
            / "quality"
            / "human-reliability"
            / "adjudication"
            / "results"
            / f"{key[0]}-{key[1]}"
            / "adjudication-results.json"
        )
        adjudicated: dict[str, Mapping[str, Any]] = {}
        if results_path.is_file():
            results = read_object(results_path)
            _validate(root, results, "adjudication-results-schema.json")
            _identity(results, cohort, "adjudication results")
            artifacts.append(_artifact(results_path, root))
            for row in results["decisions"]:
                queue_entry = row["queue_entry"]
                if queue_entry.get("storage_policy") != cohort["storage_policy"]:
                    raise HumanCodebookNotesError(
                        "adjudication result storage policy does not match cohort"
                    )
                if sorted(queue_entry.get("rights_constraints", [])) != sorted(
                    cohort["rights_constraints"]
                ):
                    raise HumanCodebookNotesError(
                        "adjudication result rights constraints do not match cohort"
                    )
                decision = row["decision"]
                disagreement_id = str(decision["disagreement_id"])
                if disagreement_id in adjudicated:
                    raise HumanCodebookNotesError(
                        f"duplicate adjudication for `{disagreement_id}`"
                    )
                adjudicated[disagreement_id] = decision
        disagreement_ids = {
            str(item["disagreement_id"]) for item in log["disagreements"]
        }
        unknown_adjudications = sorted(set(adjudicated) - disagreement_ids)
        if unknown_adjudications:
            raise HumanCodebookNotesError(
                "adjudication results reference unknown disagreement(s): "
                + ", ".join(unknown_adjudications)
            )
        for disagreement in log["disagreements"]:
            decision = adjudicated.get(str(disagreement["disagreement_id"]))
            need = (
                decision.get("codebook_need")
                if isinstance(decision, Mapping)
                else None
            )
            action = (
                str(need.get("status"))
                if isinstance(need, Mapping)
                else "none"
            )
            include = bool(disagreement["possible_codebook_ambiguity"]) or (
                action != "none"
            )
            if not include:
                continue
            group_key = (
                str(log["source_language"]),
                str(log["task_layer"]),
                str(disagreement["field"]),
            )
            group = groups.setdefault(
                group_key,
                {
                    "source_language": group_key[0],
                    "task_layer": group_key[1],
                    "field": group_key[2],
                    "field_categories": set(),
                    "cases": set(),
                    "cohorts": set(),
                    "disagreement_ids": set(),
                    "adjudication_ids": set(),
                    "ambiguity_reasons": set(),
                    "affected_sections": set(),
                    "actions": [],
                    "recoding_required": False,
                    "source_language_risks": set(),
                    "claim_impacts": set(),
                },
            )
            group["field_categories"].add(str(disagreement["field_category"]))
            group["cases"].add(case_id)
            group["cohorts"].add(f"{key[0]}@{key[1]}")
            group["disagreement_ids"].add(str(disagreement["disagreement_id"]))
            group["ambiguity_reasons"].update(
                str(value)
                for value in disagreement["codebook_ambiguity_reasons"]
            )
            group["source_language_risks"].add(
                str(disagreement["source_language_risk"]["level"])
            )
            group["claim_impacts"].add(str(disagreement["claim_impact"]))
            group["actions"].append(action)
            if isinstance(decision, Mapping):
                group["adjudication_ids"].add(
                    str(decision["adjudication_id"])
                )
                group["affected_sections"].update(
                    str(value) for value in need["affected_sections"]
                )
                group["recoding_required"] = (
                    group["recoding_required"]
                    or bool(need["recoding_required"])
                )
    findings = []
    for group_key in sorted(groups):
        group = groups[group_key]
        action = max(
            group["actions"],
            key=lambda value: ACTION_PRIORITY.get(value, -1),
        )
        findings.append(
            {
                "source_language": group["source_language"],
                "task_layer": group["task_layer"],
                "field": group["field"],
                "field_categories": sorted(group["field_categories"]),
                "affected_cases": sorted(group["cases"]),
                "affected_languages": [group["source_language"]],
                "affected_layers": [group["task_layer"]],
                "affected_cohorts": sorted(group["cohorts"]),
                "disagreement_ids": sorted(group["disagreement_ids"]),
                "adjudication_ids": sorted(group["adjudication_ids"]),
                "evidence_count": len(group["disagreement_ids"]),
                "ambiguity_reasons": sorted(group["ambiguity_reasons"]),
                "source_language_risks": sorted(
                    group["source_language_risks"]
                ),
                "claim_impacts": sorted(group["claim_impacts"]),
                "recommended_action": action,
                "affected_sections": sorted(group["affected_sections"]),
                "recoding_required": bool(group["recoding_required"]),
                "recommended_change": _recommended_change(
                    action, group["field"]
                ),
                "migration_implications": _migration(
                    action, bool(group["recoding_required"])
                ),
            }
        )
    return findings, artifacts, storage_policy


def build_notes(
    case_id: str,
    findings: Sequence[Mapping[str, Any]],
    artifacts: Sequence[Mapping[str, str]],
    storage_policy: str,
    decisions: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    decisions = decisions or {}
    recommendations = []
    known_ids = set()
    for finding in findings:
        recommendation_id = _recommendation_id(
            case_id,
            str(finding["source_language"]),
            str(finding["task_layer"]),
            str(finding["field"]),
        )
        known_ids.add(recommendation_id)
        decision = decisions.get(recommendation_id)
        recommendation_hash = _recommendation_hash(
            recommendation_id, finding
        )
        if (
            decision
            and decision["recommendation_sha256"] != recommendation_hash
        ):
            raise HumanCodebookNotesError(
                f"governance decision for `{recommendation_id}` is stale "
                "relative to the current proposal"
            )
        disposition = (
            str(decision["disposition"]) if decision else "proposed"
        )
        recommendations.append(
            {
                "recommendation_id": recommendation_id,
                "recommendation_sha256": recommendation_hash,
                **dict(finding),
                "disposition": disposition,
                "decision_rationale": (
                    str(decision["rationale"])
                    if decision
                    else "Awaiting explicit human methodological review."
                ),
                "reviewer": (
                    str(decision["reviewer"])
                    if decision and decision.get("reviewer")
                    else None
                ),
                "decided_at": (
                    str(decision["decided_at"])
                    if decision and decision.get("decided_at")
                    else None
                ),
                "decision_source": (
                    "human-decision-register" if decision else "generated-proposal"
                ),
            }
        )
    unknown = sorted(set(decisions) - known_ids)
    if unknown:
        raise HumanCodebookNotesError(
            "decision register references unknown recommendation(s): "
            + ", ".join(unknown)
        )
    counts = Counter(item["disposition"] for item in recommendations)
    return {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "generator": {
            "script": GENERATOR_PATH,
            "version": GENERATOR_VERSION,
            "script_hash": sha256_bytes((ROOT / GENERATOR_PATH).read_bytes()),
        },
        "source_artifacts": list(artifacts),
        "storage_policy": storage_policy,
        "authority": {
            "decision_authority": "human-methodology-review",
            "codebook_edit_permitted": False,
            "retroactive_change_permitted": False,
            "notice": (
                "These notes are governed recommendations only. Acceptance "
                "authorizes a separate versioned codebook-edit workflow and "
                "never changes prior decisions by itself."
            ),
        },
        "summary": {
            "recommendation_count": len(recommendations),
            "proposed_count": counts["proposed"],
            "accepted_count": counts["accepted"],
            "rejected_count": counts["rejected"],
            "deferred_count": counts["deferred"],
            "recoding_required_count": sum(
                bool(item["recoding_required"]) for item in recommendations
            ),
        },
        "recommendations": recommendations,
    }


def render_notes(notes: Mapping[str, Any]) -> str:
    if notes["storage_policy"] == "local_only":
        return f"""# Human Reliability Codebook Revision Notes: {_cell(notes['case_id'])}

> Detailed codebook recommendations are withheld because one or more source
> cohorts are local-only. Review the protected machine-readable artifact in the
> authorized local environment. No codebook edit or prior-decision change is
> authorized by this notice.
"""
    sections = []
    for disposition in ("proposed", "accepted", "rejected", "deferred"):
        entries = [
            item
            for item in notes["recommendations"]
            if item["disposition"] == disposition
        ]
        lines = [f"## {disposition.title()} recommendations", ""]
        if not entries:
            lines.append("None.")
        for item in entries:
            lines.extend(
                [
                    f"### `{_cell(item['recommendation_id'])}` — "
                    f"`{_cell(item['field'])}`",
                    "",
                    f"- Scope: `{_cell(', '.join(item['affected_cases']))}` / "
                    f"`{_cell(', '.join(item['affected_languages']))}` / "
                    f"`{_cell(', '.join(item['affected_layers']))}`",
                    f"- Cohorts: "
                    f"`{_cell(', '.join(item['affected_cohorts']))}`",
                    f"- Evidence: {item['evidence_count']} disagreement(s), "
                    f"{len(item['adjudication_ids'])} adjudicated",
                    f"- Recommended action: "
                    f"`{_cell(item['recommended_action'])}`",
                    f"- Proposed change: {_cell(item['recommended_change'])}",
                    f"- Affected sections: "
                    f"`{_cell(', '.join(item['affected_sections']) or 'not yet specified')}`",
                    f"- Re-coding required: `{item['recoding_required']}`",
                    f"- Migration implications: "
                    f"{_cell(item['migration_implications'])}",
                    f"- Governance rationale: "
                    f"{_cell(item['decision_rationale'])}",
                    f"- Reviewer: "
                    f"`{_cell(item['reviewer'] or 'not assigned')}`",
                    "",
                ]
            )
        sections.append("\n".join(lines))
    summary = notes["summary"]
    return f"""# Human Reliability Codebook Revision Notes: {_cell(notes['case_id'])}

> Governed methodological recommendations only. These notes do not edit a
> codebook, overwrite accepted annotations, alter adjudication, or retroactively
> change prior coder decisions.

## Summary

| Recommendations | Proposed | Accepted | Rejected | Deferred | Re-coding required |
|---:|---:|---:|---:|---:|---:|
| {summary['recommendation_count']} | {summary['proposed_count']} | {summary['accepted_count']} | {summary['rejected_count']} | {summary['deferred_count']} | {summary['recoding_required_count']} |

Generated findings default to **proposed**. Accepted, rejected, and deferred
states require the separate human decision register. Even an accepted
recommendation requires a later versioned codebook edit and, when applicable,
an explicitly authorized migration and re-coding plan.

{chr(10).join(sections)}
"""


def _cell(value: Any) -> str:
    return (
        html.escape(str(value), quote=False)
        .replace("`", "&#96;")
        .replace("|", "\\|")
        .replace("\n", " ")
    )


@protect_accepted_artifacts
def generate_case_codebook_notes(root: Path, case_id: str) -> dict[str, Any]:
    root = root.resolve()
    case_root = root / "cases" / case_id
    if not case_root.is_dir():
        raise HumanCodebookNotesError(f"unknown case `{case_id}`")
    cohorts = _cohorts(root, case_id)
    findings, artifacts, storage_policy = _collect_evidence(
        root, case_id, cohorts
    )
    codebook_root = safe_output_path(
        case_root, "quality/human-reliability/codebook"
    )
    if storage_policy == "local_only" and (root / ".git").exists():
        ignored = subprocess.run(
            ["git", "check-ignore", "--quiet", codebook_root],
            cwd=root,
            check=False,
        )
        if ignored.returncode != 0:
            raise HumanCodebookNotesError(
                "local-only codebook notes output is not gitignored"
            )
    decision_path = codebook_root / "recommendation-decisions.json"
    decisions = _governance(root, case_id, decision_path)
    notes = build_notes(
        case_id, findings, artifacts, storage_policy, decisions
    )
    _validate(root, notes, "codebook-revision-notes-schema.json")
    write_json(codebook_root / "codebook-revision-notes.json", notes)
    (codebook_root / "codebook-revision-notes.md").write_text(
        render_notes(notes), encoding="utf-8"
    )
    return notes


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    notes = generate_case_codebook_notes(args.root, args.case)
    print(
        f"Generated {notes['summary']['recommendation_count']} human "
        "codebook recommendation(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
