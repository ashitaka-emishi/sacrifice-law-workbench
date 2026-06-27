#!/usr/bin/env python3
"""Generate the publication-facing multi-model reliability results page."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from scripts.model_reliability.status import evaluate_case
except ModuleNotFoundError:
    try:
        from model_reliability.status import evaluate_case
    except ModuleNotFoundError:
        from status import evaluate_case  # type: ignore


ROOT = Path(__file__).resolve().parents[2]
TASK_LAYERS = ("identification", "cmt", "interpretation")
STATE_LABELS = {
    "absent": "absent — not designed",
    "designed": "designed — not executed",
    "partial": "partial — execution incomplete",
    "invalid": "invalid — results withheld",
    "complete": "complete",
}


def _read_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


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


def _case_ids(root: Path) -> list[str]:
    cases_root = root / "cases"
    if not cases_root.is_dir():
        return []
    return [
        path.name
        for path in sorted(cases_root.iterdir())
        if path.is_dir()
        and (path / "metadata" / "document-manifest.json").is_file()
    ]


def _summaries(
    agreement: Mapping[str, Any] | None,
    family: str,
) -> list[dict[str, Any]]:
    if agreement is None:
        return []
    families = agreement.get("comparison_families")
    if not isinstance(families, Mapping):
        return []
    section = families.get(family)
    if not isinstance(section, Mapping):
        return []
    containers = section.get("pairs" if family == "model_vs_model" else "runs")
    if not isinstance(containers, list):
        return []
    results: list[dict[str, Any]] = []
    for container in containers:
        if not isinstance(container, Mapping):
            continue
        values = container.get("summaries")
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, dict) and value.get("document_id") is None:
                results.append(value)
    return sorted(
        results,
        key=lambda item: (
            str(item.get("case_id", "")),
            str(item.get("source_language", "")),
            str(item.get("task_layer", "")),
            str(item.get("field", "")),
            str(item.get("left_id", "")),
            str(item.get("right_id", "")),
        ),
    )


def _layer_run_counts(model_root: Path) -> dict[str, int]:
    normalized = _read_object(model_root / "normalized" / "normalized-runs.json")
    if normalized is None:
        return {}
    runs = normalized.get("runs")
    if not isinstance(runs, list):
        return {}
    counts: dict[str, int] = {}
    for run in runs:
        if not isinstance(run, Mapping):
            continue
        submission = run.get("submission")
        items = submission.get("items") if isinstance(submission, Mapping) else []
        if not isinstance(items, list):
            continue
        layers = {
            item.get("task_layer")
            for item in items
            if isinstance(item, Mapping) and isinstance(item.get("task_layer"), str)
        }
        for layer in layers:
            counts[str(layer)] = counts.get(str(layer), 0) + 1
    return counts


def collect_results(root: Path) -> list[dict[str, Any]]:
    root = root.resolve()
    cases: list[dict[str, Any]] = []
    for case_id in _case_ids(root):
        model_root = root / "cases" / case_id / "quality" / "model-reliability"
        status = evaluate_case(root, case_id)
        agreement = (
            _read_object(model_root / "comparisons" / "agreement-results.json")
            if status.get("valid")
            else None
        )
        report = (
            _read_object(model_root / "comparisons" / "consensus-report.json")
            if status.get("valid")
            else None
        )
        cases.append(
            {
                "case_id": case_id,
                "status": status,
                "layer_run_counts": _layer_run_counts(model_root),
                "model_summaries": _summaries(agreement, "model_vs_model"),
                "reference_summaries": _summaries(
                    agreement, "model_vs_reference"
                ),
                "report": report,
            }
        )
    return cases


def _positive_comparable_count(summary: Mapping[str, Any]) -> bool:
    value = summary.get("comparable_count")
    return isinstance(value, int) and value > 0


def _layer_valid_runs(case: Mapping[str, Any], layer: str) -> int:
    counts = case.get("layer_run_counts")
    if isinstance(counts, Mapping):
        value = counts.get(layer, 0)
        return value if isinstance(value, int) and value >= 0 else 0
    if any(
        item.get("task_layer") == layer and _positive_comparable_count(item)
        for item in [
            *case.get("model_summaries", []),
            *case.get("reference_summaries", []),
        ]
    ):
        status_counts = case["status"].get("counts", {})
        value = status_counts.get("valid_runs", 0) if isinstance(status_counts, Mapping) else 0
        return value if isinstance(value, int) and value >= 0 else 0
    return 0


def _layer_state_and_note(
    case: Mapping[str, Any],
    layer: str,
    *,
    default_warning: str,
) -> tuple[str, str]:
    status = case["status"]
    state = status.get("state")
    if state in {"complete", "partial"} and _layer_valid_runs(case, layer) == 0:
        return "designed — not executed", (
            "No valid submissions for this layer; case completion reflects "
            "the executed layer(s)."
        )
    return str(STATE_LABELS.get(state, state)), default_warning


def _overview(cases: Sequence[Mapping[str, Any]]) -> str:
    rows: list[str] = []
    for case in cases:
        status = case["status"]
        warning_values = status.get("warnings", [])
        warning = warning_values[0] if warning_values else ""
        if status.get("state") == "invalid":
            error_count = len(status.get("errors", []))
            warning = (
                f"{error_count} validation error(s); field results withheld."
            )
        all_summaries = [
            *case.get("model_summaries", []),
            *case.get("reference_summaries", []),
        ]
        for layer in TASK_LAYERS:
            field_count = len(
                {
                    str(item.get("field"))
                    for item in all_summaries
                    if item.get("task_layer") == layer
                    and _positive_comparable_count(item)
                }
            )
            layer_state, layer_warning = _layer_state_and_note(
                case, layer, default_warning=warning
            )
            rows.append(
                "| `{}` | {} | {} | {} | {} | {} |".format(
                    _cell(case["case_id"]),
                    _cell(layer),
                    _cell(layer_state),
                    _cell(_layer_valid_runs(case, layer)),
                    field_count,
                    _cell(layer_warning),
                )
            )
    return "\n".join(rows) or "| — | — | — | 0 | 0 | No cases discovered. |"


def _metric_text(summary: Mapping[str, Any]) -> tuple[str, str]:
    metric = summary.get("metric")
    if not isinstance(metric, Mapping):
        return "—", "—"
    if metric.get("status") == "defined":
        return _cell(metric.get("name")), _number(metric.get("value"))
    reason = metric.get("undefined_reason") or "undefined"
    return _cell(metric.get("name")), f"undefined: {_cell(reason)}"


def _model_table(cases: Sequence[Mapping[str, Any]]) -> str:
    rows: list[str] = []
    for case in cases:
        for summary in case.get("model_summaries", []):
            metric, value = _metric_text(summary)
            kappa = summary.get("cohens_kappa")
            if isinstance(kappa, Mapping) and kappa.get("status") == "defined":
                kappa_value = _number(kappa.get("value"))
            elif isinstance(kappa, Mapping):
                reason = kappa.get("undefined_reason") or "undefined"
                kappa_value = f"undefined: {_cell(reason)}"
            else:
                kappa_value = "—"
            rows.append(
                "| `{}` | {} | {} | `{}` | `{}` ↔ `{}` | {} | {} | {} | {} |".format(
                    _cell(case["case_id"]),
                    _cell(summary.get("source_language")),
                    _cell(summary.get("task_layer")),
                    _cell(summary.get("field")),
                    _cell(summary.get("left_id")),
                    _cell(summary.get("right_id")),
                    _cell(summary.get("comparable_count")),
                    metric,
                    value,
                    kappa_value,
                )
            )
    if rows:
        return (
            "| Case | Language | Layer | Field | Run pair | N | Metric | Value | Cohen's kappa |\n"
            "|---|---|---|---|---|---:|---|---:|---|\n"
            + "\n".join(rows)
        )
    return (
        "No validated model-to-model field results are available. This is "
        "expected while packets are designed but not executed."
    )


def _reference_table(cases: Sequence[Mapping[str, Any]]) -> str:
    rows: list[str] = []
    for case in cases:
        for summary in case.get("reference_summaries", []):
            metric, value = _metric_text(summary)
            rows.append(
                "| `{}` | {} | {} | `{}` | `{}` vs `{}` | {} | {} | {} |".format(
                    _cell(case["case_id"]),
                    _cell(summary.get("source_language")),
                    _cell(summary.get("task_layer")),
                    _cell(summary.get("field")),
                    _cell(summary.get("left_id")),
                    _cell(summary.get("right_id")),
                    _cell(summary.get("comparable_count")),
                    metric,
                    value,
                )
            )
    if rows:
        return (
            "| Case | Language | Layer | Field | Comparison | N | Metric | Value |\n"
            "|---|---|---|---|---|---:|---|---:|\n"
            + "\n".join(rows)
        )
    return (
        "No validated model-to-reference field results are available. "
        "Reference alignment has not been measured."
    )


def _report_table(cases: Sequence[Mapping[str, Any]]) -> str:
    rows: list[str] = []
    for case in cases:
        report = case.get("report")
        if not isinstance(report, Mapping):
            continue
        summary = report.get("summary")
        if not isinstance(summary, Mapping):
            continue
        rows.append(
            "| `{}` | {} | {} | {} | {} | {} | {} |".format(
                _cell(case["case_id"]),
                _cell(summary.get("field_count")),
                _cell(summary.get("stable_field_count")),
                _cell(summary.get("unstable_field_count")),
                _cell(summary.get("insufficient_data_field_count")),
                _cell(summary.get("review_queue_count")),
                _cell(summary.get("high_priority_review_count")),
            )
        )
    if rows:
        return (
            "| Case | Fields | Stable | Unstable | Insufficient data | Review items | High priority |\n"
            "|---|---:|---:|---:|---:|---:|---:|\n"
            + "\n".join(rows)
        )
    return (
        "No consensus and instability report is available. Absence of a report "
        "is not evidence of agreement or reproducibility."
    )


def render_results_page(cases: Sequence[Mapping[str, Any]]) -> str:
    designed = [
        str(case["case_id"])
        for case in cases
        if case["status"].get("state") == "designed"
    ]
    layer_only = []
    for case in cases:
        if case["status"].get("state") not in {"complete", "partial"}:
            continue
        executed = [layer for layer in TASK_LAYERS if _layer_valid_runs(case, layer) > 0]
        missing = [layer for layer in TASK_LAYERS if _layer_valid_runs(case, layer) == 0]
        if executed and missing:
            missing_layers = ", ".join(f"`{_cell(layer)}`" for layer in missing)
            verb = "remains" if len(missing) == 1 else "remain"
            layer_only.append(
                f"`{_cell(case['case_id'])}` executed "
                f"{', '.join(f'`{_cell(layer)}`' for layer in executed)} only; "
                f"{missing_layers} {verb} designed but not executed."
            )
    if designed:
        noun = "has" if len(designed) == 1 else "have"
        execution_note = (
            "**Designed but not executed:** "
            + ", ".join(f"`{_cell(case_id)}`" for case_id in designed)
            + f" {noun} blind packets but no valid external model submissions."
        )
    elif layer_only:
        execution_note = "**Layer-only execution:** " + " ".join(layer_only)
    else:
        execution_note = (
            "No case is currently in the designed-without-submissions state."
        )
    return f'''---
title: "Multi-Model Reliability Results"
description: "Execution status and field-level diagnostics for blind multi-model annotation stress tests"
---

::: {{.callout-important}}
These are model-behavior diagnostics, not human inter-annotator reliability or
scholarly evidence. Consensus is not adjudication, and no result proves
reproducibility or changes an accepted annotation.
:::

This page is generated from validated case-local model-reliability artifacts by
`scripts/model_reliability/generate_results_page.py`.

{execution_note}

## Execution status by case and layer

| Case | Task layer | State | Valid runs | Available fields | Note |
|---|---|---|---:|---:|---|
{_overview(cases)}

Layer state is computed from validated submissions for that layer. `Complete`
means the artifact chain for the executed layer is valid; it does not mean an
interpretation has been proven.

## Model-to-model field stability

{_model_table(cases)}

Model-to-model stability asks whether separately run systems behave similarly.
Shared behavior may reflect a clear instruction, shared bias, prompt effects,
or common training data.

## Model-to-reference field divergence

{_reference_table(cases)}

Reference alignment is reported separately from model-to-model stability. A
divergence may reflect model error, reference error, or codebook ambiguity; it
is a question for human review, not an automatic correction.

## Consensus, instability, and review queue

{_report_table(cases)}

The review queue has human-only decision authority. Model agreement is not a
vote, and high-priority reference challenges remain unadjudicated suggestions.

## Interpretation limits

- Results remain stratified by case, source language, task layer, field, and
  run or run pair.
- Undefined and unavailable metrics stay visible rather than becoming zero or
  perfect agreement.
- Missing submissions and reports are execution states, not positive findings.
- Model outputs cannot corroborate historical claims or validate theoretical
  interpretations.
- Human source review, adjudication, and accepted-correction governance remain
  separate from this stress test.

See the [methodology](model-reliability-methodology.qmd) for the study design and
the [external review procedure](docs/reliability/external-model-review-procedures.md)
for packet execution and ingestion.
'''


def generate_results_page(root: Path, output: Path | None = None) -> Path:
    root = root.resolve()
    output = output or root / "model-reliability-results.qmd"
    output.write_text(render_results_page(collect_results(root)), encoding="utf-8")
    return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the public multi-model reliability results page."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    output = generate_results_page(args.root, args.output)
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
