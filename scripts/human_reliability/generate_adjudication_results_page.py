#!/usr/bin/env python3
"""Generate the publication-facing human adjudication results page."""
from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

try:
    from scripts.human_reliability.ingest_submission import cohort_hash
except ModuleNotFoundError:
    from ingest_submission import cohort_hash  # type: ignore


ROOT = Path(__file__).resolve().parents[2]


class AdjudicationResultsPageError(ValueError):
    """Raised when machine-readable adjudication outputs are not publishable."""


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdjudicationResultsPageError(
            f"{path}: unable to read JSON: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise AdjudicationResultsPageError(f"{path}: expected a JSON object")
    return value


def _validate(
    root: Path, value: Mapping[str, Any], schema_name: str
) -> None:
    schema_path = root / "schemas" / "human-reliability" / schema_name
    if not schema_path.is_file():
        schema_path = ROOT / "schemas" / "human-reliability" / schema_name
    schema = _read_object(schema_path)
    errors = sorted(
        Draft202012Validator(
            schema, format_checker=FormatChecker()
        ).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        location = ".".join(str(part) for part in errors[0].absolute_path)
        prefix = f"{location}: " if location else ""
        raise AdjudicationResultsPageError(
            f"{schema_name} validation failed: {prefix}{errors[0].message}"
        )


def _identity_matches(
    value: Mapping[str, Any],
    cohort: Mapping[str, Any],
    label: str,
) -> None:
    for key in ("case_id", "cohort_id", "cohort_version"):
        if value.get(key) != cohort.get(key):
            raise AdjudicationResultsPageError(
                f"{label}: `{key}` does not match the approved cohort"
            )
    for key in ("source_language", "task_layer"):
        if key in value and value.get(key) != cohort.get(key):
            raise AdjudicationResultsPageError(
                f"{label}: `{key}` does not match the approved cohort"
            )


def _cohort_manifests(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    values: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(
        (root / "cases").glob(
            "*/quality/human-reliability/cohorts/*.json"
        )
    ):
        cohort = _read_object(path)
        _validate(root, cohort, "cohort-manifest-schema.json")
        if cohort["approval"]["manifest_sha256"] != cohort_hash(cohort):
            raise AdjudicationResultsPageError(
                f"{path}: approval hash does not match canonical cohort content"
            )
        values.append((path, cohort))
    return values


def _decision_summary(
    results: Mapping[str, Any],
    *,
    publish_details: bool,
) -> tuple[
    dict[str, int],
    list[dict[str, Any]],
    dict[str, int],
    dict[str, int],
    set[tuple[str, str]],
]:
    statuses: Counter[str] = Counter()
    details: list[dict[str, Any]] = []
    codebook: Counter[str] = Counter()
    claims: Counter[str] = Counter()
    candidates: set[tuple[str, str]] = set()
    for row in results.get("decisions", []):
        if not isinstance(row, Mapping):
            continue
        queue = row.get("queue_entry")
        decision = row.get("decision")
        if not isinstance(queue, Mapping) or not isinstance(decision, Mapping):
            continue
        status = str(decision.get("status") or "")
        statuses[status] += 1
        need = decision.get("codebook_need")
        if isinstance(need, Mapping):
            codebook[str(need.get("status") or "unknown")] += 1
        for claim in decision.get("affected_claims", []):
            if isinstance(claim, Mapping):
                claims[str(claim.get("disposition") or "unknown")] += 1
        if publish_details:
            candidate = decision.get("correction_candidate")
            candidate_status = (
                str(candidate.get("status") or "not_candidate")
                if isinstance(candidate, Mapping)
                else "not_candidate"
            )
            follow_up = decision.get("follow_up")
            details.append(
                {
                    "adjudication_id": decision.get("adjudication_id"),
                    "field": decision.get("field"),
                    "status": status,
                    "selected_basis": decision.get("selected_basis"),
                    "claim_impact": queue.get("claim_impact"),
                    "source_language_risk": (
                        queue.get("source_language_risk", {}).get("level")
                        if isinstance(
                            queue.get("source_language_risk"), Mapping
                        )
                        else None
                    ),
                    "codebook_need": (
                        need.get("status")
                        if isinstance(need, Mapping)
                        else None
                    ),
                    "recoding_required": (
                        need.get("recoding_required")
                        if isinstance(need, Mapping)
                        else None
                    ),
                    "correction_candidate": candidate_status,
                    "follow_up_required": (
                        follow_up.get("required")
                        if isinstance(follow_up, Mapping)
                        else None
                    ),
                }
            )
        candidate = decision.get("correction_candidate")
        if (
            isinstance(candidate, Mapping)
            and candidate.get("status") == "candidate"
        ):
            candidates.add(
                (
                    str(candidate.get("candidate_id")),
                    str(decision.get("adjudication_id")),
                )
            )
    return (
        dict(statuses),
        details,
        dict(codebook),
        dict(claims),
        candidates,
    )


def collect_results(root: Path) -> list[dict[str, Any]]:
    root = root.resolve()
    cohorts: list[dict[str, Any]] = []
    for _, cohort in _cohort_manifests(root):
        case_id = str(cohort["case_id"])
        cohort_id = str(cohort["cohort_id"])
        version = str(cohort["cohort_version"])
        human_root = (
            root / "cases" / case_id / "quality" / "human-reliability"
        )
        results_path = (
            human_root
            / "adjudication"
            / "results"
            / f"{cohort_id}-{version}"
            / "adjudication-results.json"
        )
        candidate_path = (
            human_root
            / "correction-candidates"
            / f"{cohort_id}-{version}"
            / "correction-candidates.json"
        )
        base = {
            "case_id": case_id,
            "cohort_id": cohort_id,
            "cohort_version": version,
            "source_language": cohort["source_language"],
            "task_layer": cohort["task_layer"],
            "storage_policy": cohort["storage_policy"],
            "rights_constraints": cohort["rights_constraints"],
        }
        if not results_path.is_file():
            cohorts.append(
                {
                    **base,
                    "state": "not_started",
                    "summary": {
                        "decision_count": 0,
                        "accepted_count": 0,
                        "rejected_count": 0,
                        "deferred_count": 0,
                        "unresolved_count": 0,
                        "correction_candidate_count": 0,
                    },
                    "decision_statuses": {},
                    "decision_details": [],
                    "codebook_implications": {},
                    "claim_impacts": {},
                    "candidate_count": 0,
                }
            )
            continue

        results = _read_object(results_path)
        _validate(root, results, "adjudication-results-schema.json")
        _identity_matches(results, cohort, "adjudication results")
        for row in results["decisions"]:
            queue = row["queue_entry"]
            if queue.get("storage_policy") != cohort["storage_policy"]:
                raise AdjudicationResultsPageError(
                    "adjudication result storage policy does not match the cohort"
                )
            if sorted(queue.get("rights_constraints", [])) != sorted(
                cohort["rights_constraints"]
            ):
                raise AdjudicationResultsPageError(
                    "adjudication result rights constraints do not match the cohort"
                )
        publish_details = cohort["storage_policy"] == "repository_allowed"
        statuses, details, codebook, claims, decision_candidates = _decision_summary(
            results, publish_details=publish_details
        )
        summary = results["summary"]
        expected_counts = {
            "decision_count": sum(statuses.values()),
            "accepted_count": statuses.get("accepted", 0),
            "rejected_count": statuses.get("rejected", 0),
            "deferred_count": statuses.get("deferred", 0),
            "unresolved_count": statuses.get("unresolved", 0),
        }
        for key, expected in expected_counts.items():
            if summary[key] != expected:
                raise AdjudicationResultsPageError(
                    f"adjudication summary `{key}` does not match decisions"
                )
        expected_state = (
            "unresolved"
            if statuses.get("deferred", 0) or statuses.get("unresolved", 0)
            else "complete"
        )
        if summary["state"] != expected_state:
            raise AdjudicationResultsPageError(
                "adjudication summary `state` does not match decisions"
            )
        if summary["correction_candidate_count"] != len(decision_candidates):
            raise AdjudicationResultsPageError(
                "adjudication summary correction candidate count does not "
                "match decisions"
            )
        candidate_count = 0
        candidate_pairs: set[tuple[str, str]] = set()
        if candidate_path.is_file():
            candidates = _read_object(candidate_path)
            _validate(root, candidates, "correction-candidates-schema.json")
            _identity_matches(candidates, cohort, "correction candidates")
            if (
                candidates.get("source_registration_id")
                != results.get("registration_id")
            ):
                raise AdjudicationResultsPageError(
                    "correction candidates do not match the adjudication registration"
                )
            authority = candidates["authority"]
            if (
                authority["promotion_permitted"]
                or authority["layer"] != "dedicated_review_only"
            ):
                raise AdjudicationResultsPageError(
                    "correction candidate authority permits promotion"
                )
            candidate_count = len(candidates["candidates"])
            candidate_pairs = {
                (
                    str(candidate["candidate_id"]),
                    str(candidate["adjudication_id"]),
                )
                for candidate in candidates["candidates"]
            }
        if candidate_pairs != decision_candidates:
            raise AdjudicationResultsPageError(
                "correction candidate IDs do not match adjudication decisions"
            )
        if candidate_count != summary["correction_candidate_count"]:
            raise AdjudicationResultsPageError(
                "correction candidate count does not match adjudication results"
            )
        cohorts.append(
            {
                **base,
                "state": summary["state"],
                "summary": summary,
                "decision_statuses": statuses,
                "decision_details": details,
                "codebook_implications": codebook,
                "claim_impacts": claims,
                "candidate_count": candidate_count,
            }
        )
    return cohorts


def _cell(value: Any) -> str:
    if value is None:
        return "—"
    return (
        html.escape(str(value), quote=False)
        .replace("`", "&#96;")
        .replace("|", "\\|")
        .replace("\n", " ")
    )


def _overview(cohorts: Sequence[Mapping[str, Any]]) -> str:
    rows = []
    for cohort in cohorts:
        summary = cohort["summary"]
        rows.append(
            "| `{}` | `{}` | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                _cell(cohort["case_id"]),
                _cell(cohort["cohort_id"]),
                _cell(cohort["source_language"]),
                _cell(cohort["task_layer"]),
                _cell(cohort["state"]),
                _cell(summary["decision_count"]),
                _cell(summary["accepted_count"]),
                _cell(summary["rejected_count"]),
                _cell(summary["deferred_count"]),
                _cell(summary["unresolved_count"]),
                _cell(cohort["candidate_count"]),
            )
        )
    return (
        "\n".join(rows)
        or "| — | — | — | — | not started | 0 | 0 | 0 | 0 | 0 | 0 |"
    )


def _rights(cohorts: Sequence[Mapping[str, Any]]) -> str:
    rows = []
    for cohort in cohorts:
        detail = (
            "item-level metadata shown"
            if cohort["storage_policy"] == "repository_allowed"
            else "item-level metadata withheld"
        )
        rows.append(
            "| `{}` | {} | `{}` | {} | {} |".format(
                _cell(cohort["cohort_id"]),
                _cell(cohort["source_language"]),
                _cell(cohort["storage_policy"]),
                _cell(", ".join(cohort["rights_constraints"])),
                detail,
            )
        )
    return "\n".join(rows) or "| — | — | — | — | No cohorts discovered. |"


def _details(cohorts: Sequence[Mapping[str, Any]]) -> str:
    rows = []
    for cohort in cohorts:
        for decision in cohort["decision_details"]:
            rows.append(
                "| `{}` | `{}` | `{}` | `{}` | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                    _cell(cohort["case_id"]),
                    _cell(cohort["cohort_id"]),
                    _cell(decision["adjudication_id"]),
                    _cell(decision["field"]),
                    _cell(decision["status"]),
                    _cell(decision["selected_basis"]),
                    _cell(decision["claim_impact"]),
                    _cell(decision["source_language_risk"]),
                    _cell(decision["codebook_need"]),
                    _cell(decision["recoding_required"]),
                    _cell(decision["correction_candidate"]),
                    _cell(decision["follow_up_required"]),
                )
            )
    if not rows:
        return (
            "No repository-safe adjudication decision metadata is available. "
            "This may mean adjudication has not started or the cohort is local-only."
        )
    return (
        "| Case | Cohort | Decision | Field | Status | Basis | Claim impact | "
        "Source risk | Codebook | Recoding | Candidate | Follow-up |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
        + "\n".join(rows)
    )


def _consequences(
    cohorts: Sequence[Mapping[str, Any]], key: str, label: str
) -> str:
    rows = []
    for cohort in cohorts:
        for status, count in sorted(cohort[key].items()):
            rows.append(
                f"| `{_cell(cohort['cohort_id'])}` | `{_cell(status)}` | "
                f"{_cell(count)} |"
            )
    if not rows:
        return f"No {key.replace('_', ' ')} are available."
    return (
        f"| Cohort | {label} | Count |\n"
        "|---|---|---:|\n" + "\n".join(rows)
    )


def render_results_page(cohorts: Sequence[Mapping[str, Any]]) -> str:
    return f'''---
title: "Human Adjudication Results"
description: "Scoped outcomes, unresolved work, correction candidates, and publication consequences from validated human adjudication"
---

::: {{.callout-important}}
Adjudication resolves study disagreements; it does not silently rewrite
accepted annotations. Correction candidates remain review-only proposals until
a separate authorized promotion records and applies a canonical change.
:::

This page is generated from validated machine-readable adjudication results and
correction-candidate artifacts by
`scripts/human_reliability/generate_adjudication_results_page.py`.

## Cohort status

| Case | Cohort | Language | Layer | State | Decisions | Accepted | Rejected | Deferred | Unresolved | Candidates |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|
{_overview(cohorts)}

`Not started` means no validated normalized adjudication result exists.
`Unresolved` preserves deferred or unresolved decisions rather than inferring an
answer. Results are never pooled across cases, languages, layers, or cohorts.

## Rights and source-language scope

| Cohort | Language | Storage | Rights constraints | Publication detail |
|---|---|---|---|---|
{_rights(cohorts)}

Local-only cohorts expose aggregate state and counts only. Source text,
adjudicated values, rationales, evidence, coder values, and reference values
are not reproduced on this page.

## Decision outcomes

{_details(cohorts)}

The table reports decision metadata only. It intentionally omits source text,
adjudicated values, rationales, evidence, coder values, and reference values.

## Codebook implications

{_consequences(cohorts, "codebook_implications", "Disposition")}

Codebook clarification, revision, training updates, or recoding needs remain
recommendations for the separately governed codebook workflow.

## Claim impacts

{_consequences(cohorts, "claim_impacts", "Disposition")}

`review_required` and `hold_pending_resolution` keep affected claims under
review; they do not automatically revise publication claims.

## Correction candidates and promotion boundary

Candidate counts come from the dedicated correction-candidate layer. Every
candidate remains `pending_separate_authorization`, has no promotion ID, and
forbids direct writes. This page reports proposals, not promoted corrections.

## Interpretation limits

- Adjudication outcomes do not replace pre-adjudication human-human agreement.
- A selected coder or reference basis is a human decision, not a vote.
- Missing adjudication is an execution state, not evidence of agreement.
- Source-language qualification and rights restrictions remain cohort-specific.
- Canonical corpus, analysis, metadata, claim, and publication edits require a
  separate authorized promotion and regeneration workflow.
'''


def generate_results_page(root: Path, output: Path | None = None) -> Path:
    root = root.resolve()
    output = output or root / "human-adjudication-results.qmd"
    output.write_text(
        render_results_page(collect_results(root)), encoding="utf-8"
    )
    return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the public human adjudication results page."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    output = generate_results_page(args.root, args.output)
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
