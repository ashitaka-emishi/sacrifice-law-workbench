#!/usr/bin/env python3
"""Generate a scoped publication report for one human-reliability cohort."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

try:
    from scripts.human_reliability.boundaries import (
        protect_accepted_artifacts,
        safe_output_path,
    )
    from scripts.human_reliability.generate_packets import sample_hash
    from scripts.human_reliability.ingest_submission import cohort_hash
except ModuleNotFoundError:
    from boundaries import protect_accepted_artifacts, safe_output_path  # type: ignore
    from generate_packets import sample_hash  # type: ignore
    from ingest_submission import cohort_hash  # type: ignore


ROOT = Path(__file__).resolve().parents[2]
GENERATOR_PATH = "scripts/human_reliability/generate_report.py"
GENERATOR_VERSION = "1.0.0"
REQUIRED_ANALYSIS = (
    ("agreement", "human-agreement.json", "agreement-results-schema.json"),
    (
        "reference_comparison",
        "reference-comparison.json",
        "reference-comparison-schema.json",
    ),
    ("disagreements", "disagreement-log.json", "disagreement-log-schema.json"),
)
SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9._-]+$")


class HumanReliabilityReportError(ValueError):
    """Raised when report inputs are invalid or cross cohort boundaries."""


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HumanReliabilityReportError(
            f"{path}: unable to read JSON: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise HumanReliabilityReportError(f"{path}: expected a JSON object")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _revision(root: Path) -> str:
    for workdir in (root, ROOT):
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workdir,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    raise HumanReliabilityReportError("unable to determine code revision")


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
        raise HumanReliabilityReportError(
            f"{schema_name} validation failed: {prefix}{errors[0].message}"
        )


def _cohort_path(
    case_root: Path, cohort_id: str, cohort_version: str
) -> Path:
    matches = []
    for path in sorted(
        (case_root / "quality" / "human-reliability" / "cohorts").glob("*.json")
    ):
        value = read_object(path)
        if (
            value.get("cohort_id") == cohort_id
            and value.get("cohort_version") == cohort_version
        ):
            matches.append(path)
    if len(matches) != 1:
        raise HumanReliabilityReportError(
            f"expected one cohort manifest for `{cohort_id}` "
            f"`{cohort_version}`, found {len(matches)}"
        )
    return matches[0]


def _find_sample(
    human_root: Path, sample_id: str, sample_version: str
) -> tuple[Path, dict[str, Any]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted((human_root / "samples").rglob("*.json")):
        value = read_object(path)
        if (
            value.get("sample_id") == sample_id
            and value.get("sample_version") == sample_version
        ):
            matches.append((path, value))
    if len(matches) != 1:
        raise HumanReliabilityReportError(
            f"expected one sample manifest for `{sample_id}` "
            f"`{sample_version}`, found {len(matches)}"
        )
    return matches[0]


def _identity(cohort: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: cohort[key]
        for key in (
            "case_id",
            "cohort_id",
            "cohort_version",
            "source_language",
            "task_layer",
            "sample_id",
            "sample_version",
            "packet_id",
        )
    }


def _check_identity(
    value: Mapping[str, Any],
    identity: Mapping[str, Any],
    source: str,
) -> None:
    for key in (
        "case_id",
        "cohort_id",
        "cohort_version",
        "source_language",
        "task_layer",
    ):
        if value.get(key) != identity[key]:
            raise HumanReliabilityReportError(
                f"{source}: `{key}` does not match the cohort manifest"
            )
    if "packet_id" in value and value.get("packet_id") != identity["packet_id"]:
        raise HumanReliabilityReportError(
            f"{source}: `packet_id` does not match the cohort manifest"
        )


def _artifact(path: Path, case_root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(case_root).as_posix(),
        "sha256": sha256_bytes(path.read_bytes()),
    }


def _case_path(case_root: Path, relative_path: str) -> Path:
    resolved_case = case_root.resolve()
    candidate = (resolved_case / relative_path).resolve()
    try:
        candidate.relative_to(resolved_case)
    except ValueError as exc:
        raise HumanReliabilityReportError(
            f"artifact path escapes the case root: `{relative_path}`"
        ) from exc
    return candidate


def _ingestion_summary(
    root: Path,
    human_root: Path,
    cohort_id: str,
    cohort_version: str,
) -> dict[str, Any]:
    path = human_root / "ingestion-status.json"
    if not path.is_file():
        return {
            "state": "absent",
            "valid_primary_coders": [],
            "valid_submission_count": 0,
            "invalid_submission_count": 0,
        }
    status = read_object(path)
    _validate(root, status, "ingestion-status-schema.json")
    for cohort in status.get("cohorts", []):
        if (
            isinstance(cohort, Mapping)
            and cohort.get("cohort_id") == cohort_id
            and cohort.get("cohort_version") == cohort_version
        ):
            return {
                key: cohort[key]
                for key in (
                    "state",
                    "valid_primary_coders",
                    "valid_submission_count",
                    "invalid_submission_count",
                )
            }
    return {
        "state": "absent",
        "valid_primary_coders": [],
        "valid_submission_count": 0,
        "invalid_submission_count": 0,
    }


STATISTIC_NAMES = (
    "observed_agreement",
    "cohens_kappa",
    "positive_agreement",
    "negative_agreement",
    "mean_jaccard",
    "mean_absolute_difference",
    "mean_ordinal_distance",
)


def _agreement_rows(agreement: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if agreement is None:
        return []
    rows = []
    for metric in agreement.get("field_metrics", []):
        if not isinstance(metric, Mapping):
            continue
        rows.append(
            {
                "field": metric.get("field"),
                "metric_family": metric.get("metric_family"),
                "comparable_count": metric.get("comparable_count"),
                "missing_count": metric.get("missing_count"),
                "sample_assessment": metric.get("sample_assessment"),
                "statistics": {
                    name: dict(metric[name])
                    for name in STATISTIC_NAMES
                    if isinstance(metric.get(name), Mapping)
                },
            }
        )
    return rows


def _reference_summary(
    comparison: Mapping[str, Any] | None,
) -> dict[str, Any]:
    totals = Counter(
        {"aligned": 0, "divergent": 0, "unavailable": 0, "not_comparable": 0}
    )
    patterns: Counter[str] = Counter()
    if comparison is not None:
        for coder in comparison.get("coder_comparisons", []):
            if isinstance(coder, Mapping):
                totals.update(
                    {
                        key: int(value)
                        for key, value in coder.get("summary", {}).items()
                        if key in totals and isinstance(value, int)
                    }
                )
        patterns.update(
            {
                str(key): int(value)
                for key, value in comparison.get("pattern_summary", {}).items()
                if isinstance(value, int)
            }
        )
    return {
        "coder_field_comparisons": dict(totals),
        "pair_patterns": dict(sorted(patterns.items())),
    }


def build_report(
    root: Path,
    case_id: str,
    cohort_id: str,
    cohort_version: str,
    *,
    revision: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    for label, value in (
        ("case ID", case_id),
        ("cohort ID", cohort_id),
        ("cohort version", cohort_version),
    ):
        if not SAFE_COMPONENT.fullmatch(value):
            raise HumanReliabilityReportError(
                f"unsafe {label} `{value}`; expected letters, digits, dot, "
                "underscore, or hyphen"
            )
    case_root = root / "cases" / case_id
    human_root = case_root / "quality" / "human-reliability"
    cohort_path = _cohort_path(case_root, cohort_id, cohort_version)
    cohort = read_object(cohort_path)
    _validate(root, cohort, "cohort-manifest-schema.json")
    if cohort["approval"]["manifest_sha256"] != cohort_hash(cohort):
        raise HumanReliabilityReportError(
            "cohort approval.manifest_sha256 does not match canonical content"
        )
    if cohort.get("case_id") != case_id:
        raise HumanReliabilityReportError(
            "cohort manifest case does not match requested case"
        )
    identity = _identity(cohort)

    sample_path, sample = _find_sample(
        human_root, identity["sample_id"], identity["sample_version"]
    )
    _validate(root, sample, "sample-manifest-schema.json")
    if sample["approval"]["manifest_sha256"] != sample_hash(sample):
        raise HumanReliabilityReportError(
            "sample approval.manifest_sha256 does not match canonical content"
        )
    packet_path = _case_path(case_root, str(cohort["packet_manifest"]))
    packet = read_object(packet_path)
    _validate(root, packet, "packet-manifest-schema.json")
    if packet.get("sample_hash") != sample_hash(sample):
        raise HumanReliabilityReportError(
            "packet manifest sample_hash does not match the approved sample"
        )
    for key in ("case_id", "source_language", "task_layer", "sample_id", "sample_version", "packet_id"):
        if packet.get(key) != identity[key]:
            raise HumanReliabilityReportError(
                f"packet manifest `{key}` does not match the cohort"
            )

    comparison_root = (
        human_root / "comparisons" / f"{cohort_id}-{cohort_version}"
    )
    artifacts: dict[str, Any] = {}
    values: dict[str, dict[str, Any] | None] = {}
    for name, filename, schema in REQUIRED_ANALYSIS:
        path = comparison_root / filename
        if path.is_file():
            value = read_object(path)
            _validate(root, value, schema)
            _check_identity(value, identity, filename)
            artifacts[name] = {"status": "available", **_artifact(path, case_root)}
            values[name] = value
        else:
            artifacts[name] = {"status": "not_available", "path": None, "sha256": None}
            values[name] = None

    ingestion = _ingestion_summary(
        root, human_root, cohort_id, cohort_version
    )
    analysis_complete = all(
        artifacts[name]["status"] == "available"
        for name, _, _ in REQUIRED_ANALYSIS
    )
    if ingestion["state"] == "absent":
        report_state = "designed"
    elif ingestion["state"] != "complete" or not analysis_complete:
        report_state = "partial"
    else:
        report_state = "complete"

    adjudication_path = (
        human_root
        / "adjudication"
        / "results"
        / f"{cohort_id}-{cohort_version}"
        / "adjudication-results.json"
    )
    adjudication: dict[str, Any]
    if adjudication_path.is_file():
        adjudication_value = read_object(adjudication_path)
        _validate(root, adjudication_value, "adjudication-results-schema.json")
        _check_identity(adjudication_value, identity, adjudication_path.name)
        adjudication = {
            "status": adjudication_value["summary"]["state"],
            **adjudication_value["summary"],
            "artifact": _artifact(adjudication_path, case_root),
        }
    else:
        adjudication = {
            "status": "not_started",
            "decision_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
            "deferred_count": 0,
            "unresolved_count": 0,
            "correction_candidate_count": 0,
            "artifact": None,
        }

    disagreement_value = values["disagreements"]
    disagreement_summary = (
        dict(disagreement_value["summary"])
        if disagreement_value is not None
        else {
            "total_disagreements": None,
            "by_category": {},
            "by_claim_impact": {},
            "by_priority": {},
            "by_source_language_risk": {},
            "possible_codebook_ambiguity_count": None,
            "major_claim_impact_count": None,
        }
    )
    limitations = [
        "Results apply only to this case, source language, task layer, sample, and cohort version.",
        "Human-human agreement and coder-to-reference alignment are separate analyses.",
        "Sparse, undefined, unavailable, and qualitative-only fields must not be interpreted as zero or perfect agreement.",
        "Reference divergence does not by itself establish coder error or reference error.",
        "Adjudication and correction-candidate promotion remain separate from pre-adjudication reliability.",
    ]
    if report_state != "complete":
        limitations.append(
            "Execution is incomplete; no empirical reliability claim may be made for this cohort."
        )

    generator_path = root / GENERATOR_PATH
    if not generator_path.is_file():
        generator_path = ROOT / GENERATOR_PATH
    report = {
        "schema_version": "1.0.0",
        "report_state": report_state,
        **identity,
        "design": {
            "codebook_version": cohort["codebook_version"],
            "training_version": cohort["training_version"],
            "calibration_id": cohort["calibration_id"],
            "required_primary_coders": cohort["required_primary_coders"],
            "primary_coder_ids": cohort["primary_coder_ids"],
            "blind_independent_coding": True,
            "ai_assistance_allowed": cohort["ai_assistance_allowed"],
            "storage_policy": cohort["storage_policy"],
            "rights_constraints": cohort["rights_constraints"],
            "sample_status": sample["status"],
            "sample_item_count": len(sample["items"]),
            "sample_exclusion_count": len(sample["exclusions"]),
            "sample_execution_status": sample["execution"]["status"],
        },
        "execution": ingestion,
        "input_artifacts": {
            "cohort_manifest": _artifact(cohort_path, case_root),
            "sample_manifest": _artifact(sample_path, case_root),
            "packet_manifest": _artifact(packet_path, case_root),
            **artifacts,
        },
        "agreement_metrics": _agreement_rows(values["agreement"]),
        "reference_comparison": _reference_summary(
            values["reference_comparison"]
        ),
        "disagreements": disagreement_summary,
        "adjudication": adjudication,
        "scope_claim": (
            f"This report describes only `{case_id}` / "
            f"`{identity['source_language']}` / `{identity['task_layer']}` / "
            f"`{cohort_id}` `{cohort_version}`."
        ),
        "limitations": limitations,
        "generator": {
            "script": GENERATOR_PATH,
            "version": GENERATOR_VERSION,
            "script_hash": sha256_bytes(generator_path.read_bytes()),
            "code_revision": revision or _revision(root),
        },
    }
    _validate(root, report, "human-reliability-report-schema.json")
    return report


def _cell(value: Any) -> str:
    if value is None:
        return "—"
    return (
        html.escape(str(value), quote=False)
        .replace("`", "&#96;")
        .replace("|", "\\|")
        .replace("\n", " ")
    )


def _number(value: Any) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "—"
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _statistics_text(statistics: Mapping[str, Any]) -> str:
    values = []
    for name in STATISTIC_NAMES:
        statistic = statistics.get(name)
        if not isinstance(statistic, Mapping):
            continue
        status = statistic.get("status")
        if status == "defined":
            values.append(f"`{name}`={_number(statistic.get('value'))}")
        elif status == "undefined":
            reason = _cell(statistic.get("undefined_reason") or "undefined")
            values.append(f"`{name}`=undefined ({reason})")
    return "; ".join(values) or "qualitative only"


def render_markdown(report: Mapping[str, Any]) -> str:
    design = report["design"]
    execution = report["execution"]
    metric_rows = []
    for metric in report["agreement_metrics"]:
        metric_rows.append(
            "| `{}` | {} | {} | {} | {} |".format(
                _cell(metric["field"]),
                _cell(metric["metric_family"]),
                _cell(metric["comparable_count"]),
                _cell(metric["sample_assessment"]),
                _statistics_text(metric["statistics"]),
            )
        )
    metrics = "\n".join(metric_rows) or (
        "No agreement metrics are available. This is an execution state, not "
        "evidence of agreement."
    )
    if metric_rows:
        metrics = (
            "| Field | Family | N | Sample | Statistics |\n"
            "|---|---|---:|---|---|\n" + metrics
        )

    comparison_rows = "\n".join(
        f"| `{_cell(name)}` | {_cell(count)} |"
        for name, count in sorted(
            report["reference_comparison"]["coder_field_comparisons"].items()
        )
    )
    pattern_rows = "\n".join(
        f"| `{_cell(name)}` | {_cell(count)} |"
        for name, count in sorted(
            report["reference_comparison"]["pair_patterns"].items()
        )
    )
    if not pattern_rows:
        pattern_rows = "| — | — |"

    disagreements = report["disagreements"]
    adjudication = report["adjudication"]
    return f"""# Human Reliability Report

**State:** `{_cell(report['report_state'])}`

::: {{.callout-important}}
This report is cohort-scoped. It does not provide a project-wide reliability
score, treat reference alignment as human-human agreement, or authorize edits
to accepted annotations.
:::

{_cell(report['scope_claim'])}

## Study design

| Case | Language | Layer | Cohort | Sample items | Required coders |
|---|---|---|---|---:|---:|
| `{_cell(report['case_id'])}` | {_cell(report['source_language'])} | {_cell(report['task_layer'])} | `{_cell(report['cohort_id'])}` `{_cell(report['cohort_version'])}` | {_cell(design['sample_item_count'])} | {_cell(design['required_primary_coders'])} |

- Training version: `{_cell(design['training_version'])}`
- Calibration: `{_cell(design['calibration_id'])}`
- Codebook: `{_cell(design['codebook_version'])}`
- Blind independent coding: `{_cell(design['blind_independent_coding'])}`
- AI assistance allowed: `{_cell(design['ai_assistance_allowed'])}`
- Sample execution state: `{_cell(design['sample_execution_status'])}`

## Execution

| Ingestion state | Valid coders | Valid submissions | Invalid submissions |
|---|---:|---:|---:|
| `{_cell(execution['state'])}` | {_cell(len(execution['valid_primary_coders']))} | {_cell(execution['valid_submission_count'])} | {_cell(execution['invalid_submission_count'])} |

## Human-human agreement by field

{metrics}

Agreement is pre-adjudication and field-specific. Undefined and sparse values
remain visible; no overall agreement statistic is computed.

## Coder-to-reference comparison

| Alignment | Count |
|---|---:|
{comparison_rows}

### Pair patterns

| Pattern | Count |
|---|---:|
{pattern_rows}

Reference alignment is descriptive. Divergence can indicate coder error,
reference error, or codebook ambiguity and requires human review.

## Disagreements

| Total | Major claim impact | Possible codebook ambiguity |
|---:|---:|---:|
| {_cell(disagreements['total_disagreements'])} | {_cell(disagreements['major_claim_impact_count'])} | {_cell(disagreements['possible_codebook_ambiguity_count'])} |

## Adjudication

| State | Decisions | Unresolved | Correction candidates |
|---|---:|---:|---:|
| `{_cell(adjudication['status'])}` | {_cell(adjudication['decision_count'])} | {_cell(adjudication['unresolved_count'])} | {_cell(adjudication['correction_candidate_count'])} |

Adjudication does not replace the pre-adjudication agreement results.
Correction candidates require separate authorization before any canonical edit.

## Scope and limitations

""" + "\n".join(f"- {_cell(value)}" for value in report["limitations"]) + "\n"


@protect_accepted_artifacts
def generate_case_report(
    root: Path,
    case_id: str,
    cohort_id: str,
    cohort_version: str,
    *,
    revision: str | None = None,
) -> dict[str, Any]:
    report = build_report(
        root, case_id, cohort_id, cohort_version, revision=revision
    )
    case_root = root.resolve() / "cases" / case_id
    output_root = safe_output_path(
        case_root,
        (
            "quality/human-reliability/comparisons/"
            f"{cohort_id}-{cohort_version}"
        ),
    )
    write_json(output_root / "human-reliability-report.json", report)
    (output_root / "human-reliability-report.md").write_text(
        render_markdown(report), encoding="utf-8"
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a scoped human reliability report."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--case", required=True)
    parser.add_argument("--cohort", required=True)
    parser.add_argument("--cohort-version", required=True)
    args = parser.parse_args(argv)
    report = generate_case_report(
        args.root,
        args.case,
        args.cohort,
        args.cohort_version,
    )
    print(
        "Wrote human reliability report "
        f"({report['report_state']}) for {args.cohort} {args.cohort_version}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
