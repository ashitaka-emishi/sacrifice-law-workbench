#!/usr/bin/env python3
"""Compute layered model-vs-model and model-vs-reference diagnostics."""
from __future__ import annotations

import argparse
import csv
import itertools
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:
    from scripts.model_reliability.boundaries import safe_output_path
except ModuleNotFoundError:
    from boundaries import safe_output_path  # type: ignore

GENERATOR_PATH = "scripts/model_reliability/compare_runs.py"
NOMINAL_FIELDS = {
    "identification.decision",
    "identification.boundary_decision",
    "cmt.source_domain_primary",
    "cmt.target_domain",
    "cmt.conceptual_metaphor",
    "cmt.cluster_id",
    "interpretation.functions.sacred_object",
    "interpretation.functions.sacrificial_body",
    "interpretation.functions.enemy_as_bringer_of_death",
    "interpretation.functions.violence_logic",
    "interpretation.functions.obligatory_frame",
    "interpretation.functions.purification",
    "interpretation.absence.status",
    "uncertainty.status",
}
KAPPA_FIELDS = {
    "identification.decision",
    "identification.boundary_decision",
    "interpretation.functions.sacred_object",
    "interpretation.functions.sacrificial_body",
    "interpretation.functions.enemy_as_bringer_of_death",
    "interpretation.functions.violence_logic",
    "interpretation.functions.obligatory_frame",
    "interpretation.functions.purification",
    "interpretation.absence.status",
    "uncertainty.status",
}
SET_FIELDS = {
    "identification.boundary_span",
    "cmt.source_domain_secondary",
    "cmt.entailments",
    "interpretation.agency.agents",
    "interpretation.agency.patients",
    "interpretation.agency.beneficiaries",
    "interpretation.agency.sacrificial_subjects",
    "interpretation.agency.excluded_agents",
}
TEXT_FIELDS = {
    "identification.contextual_meaning",
    "identification.basic_meaning",
    "identification.contrast_explanation",
    "identification.comparison_basis",
    "interpretation.absence.expected_presence",
    "interpretation.absence.possible_absence",
    "interpretation.absence.displacement_mechanism",
}
NUMERIC_FIELDS = {"confidence"}
REQUESTED_FIELDS = tuple(sorted(NOMINAL_FIELDS | SET_FIELDS | TEXT_FIELDS | NUMERIC_FIELDS))


class ComparisonError(ValueError):
    """Raised when comparison inputs are unsafe or not comparable."""


@dataclass(frozen=True)
class Observation:
    key: tuple[str, str]
    item_id: str
    unit_id: str
    case_id: str
    source_language: str
    document_id: str
    sentence_id: str
    task_layer: str
    field: str
    value: Any


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ComparisonError(f"{path}: unable to read JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ComparisonError(f"{path}: expected a JSON object")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _submission(run: Mapping[str, Any]) -> Mapping[str, Any]:
    submission = run.get("submission")
    return submission if isinstance(submission, Mapping) else run


def _run_metadata(
    run: Mapping[str, Any], default_case_id: str | None = None
) -> tuple[str, str, str, Sequence[Mapping[str, Any]]]:
    submission = _submission(run)
    metadata = submission.get("run")
    if isinstance(metadata, Mapping):
        run_id = metadata.get("run_id")
    else:
        run_id = submission.get("run_id")
    language = submission.get("source_language")
    items = submission.get("items")
    case_id = submission.get("case_id", default_case_id)
    if not isinstance(run_id, str) or not run_id:
        raise ComparisonError("every normalized run must have a non-empty run_id")
    if not isinstance(case_id, str) or not case_id:
        raise ComparisonError(f"run `{run_id}` has no case_id")
    if not isinstance(language, str) or not language:
        raise ComparisonError(f"run `{run_id}` has no source_language")
    if not isinstance(items, list):
        raise ComparisonError(f"run `{run_id}` has no items array")
    return run_id, case_id, language, [item for item in items if isinstance(item, Mapping)]


def _add(
    observations: list[Observation],
    *,
    item: Mapping[str, Any],
    unit_id: str,
    field: str,
    value: Any,
) -> None:
    if value is None:
        return
    item_id = item.get("item_id")
    if not isinstance(item_id, str):
        return
    observations.append(
        Observation(
            key=(unit_id, field),
            item_id=item_id,
            unit_id=unit_id,
            case_id=str(item.get("case_id", "")),
            source_language=str(item.get("source_language", "")),
            document_id=str(item.get("document_id", "")),
            sentence_id=str(item.get("sentence_id", "")),
            task_layer=str(item.get("task_layer", "")),
            field=field,
            value=value,
        )
    )


def _nested(mapping: Mapping[str, Any], *keys: str) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, Mapping) or key not in value:
            return None
        value = value[key]
    return value


def _reference_unit_id(item: Mapping[str, Any], layer: str, item_id: str) -> str:
    span_ids = item.get("span_ids")
    if isinstance(span_ids, list) and len(span_ids) == 1 and isinstance(span_ids[0], str):
        return span_ids[0]
    marker = f":{layer}:"
    return item_id.split(marker, 1)[1] if marker in item_id else item_id


def flatten_run(
    run: Mapping[str, Any], default_case_id: str | None = None
) -> tuple[str, list[Observation]]:
    run_id, case_id, language, items = _run_metadata(run, default_case_id)
    observations: list[Observation] = []
    for item in items:
        enriched = dict(item)
        enriched.setdefault("case_id", case_id)
        enriched.setdefault("source_language", language)
        item_id = item.get("item_id")
        if not isinstance(item_id, str):
            continue
        layer = item.get("task_layer")
        common_unit_id = item_id
        if layer == "identification":
            lexical_units = item.get("lexical_units")
            if not isinstance(lexical_units, list):
                lexical_units = [item]
            identification = item.get("identification")
            if isinstance(identification, Mapping):
                for name in (
                    "contextual_meaning",
                    "basic_meaning",
                    "contrast_explanation",
                    "comparison_basis",
                ):
                    _add(
                        observations,
                        item=enriched,
                        unit_id=item_id,
                        field=f"identification.{name}",
                        value=identification.get(name),
                    )
            for lexical_unit in lexical_units:
                if not isinstance(lexical_unit, Mapping):
                    continue
                unit_id = lexical_unit.get("lexical_unit_id") or item_id
                _add(
                    observations,
                    item=enriched,
                    unit_id=str(unit_id),
                    field="identification.decision",
                    value=lexical_unit.get("decision", item.get("decision")),
                )
                _add(
                    observations,
                    item=enriched,
                    unit_id=str(unit_id),
                    field="identification.boundary_decision",
                    value=lexical_unit.get(
                        "boundary_decision", item.get("boundary_decision")
                    ),
                )
                start = lexical_unit.get("proposed_char_offset_start")
                end = lexical_unit.get("proposed_char_offset_end")
                if not isinstance(start, int) or not isinstance(end, int):
                    start = lexical_unit.get("char_offset_start")
                    end = lexical_unit.get("char_offset_end")
                if isinstance(start, int) and isinstance(end, int) and end > start:
                    _add(
                        observations,
                        item=enriched,
                        unit_id=str(unit_id),
                        field="identification.boundary_span",
                        value=list(range(start, end)),
                    )
        if layer == "cmt":
            cmt = item.get("cmt") if isinstance(item.get("cmt"), Mapping) else item
            unit_id = _reference_unit_id(item, "cmt", item_id)
            common_unit_id = unit_id
            for name in (
                "source_domain_primary",
                "source_domain_secondary",
                "target_domain",
                "conceptual_metaphor",
                "entailments",
                "cluster_id",
            ):
                _add(
                    observations,
                    item=enriched,
                    unit_id=unit_id,
                    field=f"cmt.{name}",
                    value=cmt.get(name),
                )
        if layer == "interpretation":
            interpretation = (
                item.get("interpretation")
                if isinstance(item.get("interpretation"), Mapping)
                else item
            )
            unit_id = _reference_unit_id(item, "interpretation", item_id)
            common_unit_id = unit_id
            functions = interpretation.get("functions")
            if isinstance(functions, Mapping):
                for name, value in functions.items():
                    _add(
                        observations,
                        item=enriched,
                        unit_id=unit_id,
                        field=f"interpretation.functions.{name}",
                        value=value,
                    )
            agency = interpretation.get("agency")
            if isinstance(agency, Mapping):
                for name, value in agency.items():
                    _add(
                        observations,
                        item=enriched,
                        unit_id=unit_id,
                        field=f"interpretation.agency.{name}",
                        value=value,
                    )
            absence = interpretation.get("absence")
            if isinstance(absence, Mapping):
                for name, value in absence.items():
                    _add(
                        observations,
                        item=enriched,
                        unit_id=unit_id,
                        field=f"interpretation.absence.{name}",
                        value=value,
                    )
        _add(
            observations,
            item=enriched,
            unit_id=common_unit_id,
            field="confidence",
            value=item.get("confidence"),
        )
        _add(
            observations,
            item=enriched,
            unit_id=common_unit_id,
            field="uncertainty.status",
            value=_nested(item, "uncertainty", "status"),
        )
    return run_id, observations


def _canonical_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {json.dumps(item, ensure_ascii=False, sort_keys=True) for item in value}


def _jaccard(left: Any, right: Any) -> float:
    left_set = _canonical_set(left)
    right_set = _canonical_set(right)
    union = left_set | right_set
    return 1.0 if not union else len(left_set & right_set) / len(union)


def _cohens_kappa(pairs: Sequence[tuple[Any, Any]]) -> tuple[float | None, str | None]:
    if len(pairs) < 2:
        return None, "fewer than two comparable observations"
    labels = {json.dumps(value, sort_keys=True) for pair in pairs for value in pair}
    total = len(pairs)
    observed = sum(left == right for left, right in pairs) / total
    expected = 0.0
    for label in labels:
        left_share = sum(json.dumps(left, sort_keys=True) == label for left, _ in pairs) / total
        right_share = sum(json.dumps(right, sort_keys=True) == label for _, right in pairs) / total
        expected += left_share * right_share
    if expected == 1.0:
        return None, "expected agreement is 1.0 because both sides are constant"
    return (observed - expected) / (1.0 - expected), None


def _metric_name(field: str) -> str:
    if field in SET_FIELDS:
        return "jaccard_overlap"
    if field in NUMERIC_FIELDS:
        return "mean_absolute_difference"
    return "observed_agreement"


def _exact_match(field: str, left: Any, right: Any) -> bool:
    if field in SET_FIELDS:
        return _canonical_set(left) == _canonical_set(right)
    return left == right


def _group_summary(
    family: str,
    left_id: str,
    right_id: str,
    field: str,
    pairs: Sequence[tuple[Observation, Observation]],
    *,
    case_id: str,
    source_language: str,
    document_id: str | None,
    task_layer: str,
) -> dict[str, Any]:
    values = [(left.value, right.value) for left, right in pairs]
    metric_name = _metric_name(field)
    metric_value: float | None = None
    reason: str | None = None
    if not values:
        status = "undefined"
        reason = "no comparable observations"
    elif field in SET_FIELDS:
        status = "defined"
        metric_value = sum(_jaccard(left, right) for left, right in values) / len(values)
    elif field in NUMERIC_FIELDS:
        numeric = [
            (float(left), float(right))
            for left, right in values
            if isinstance(left, (int, float)) and isinstance(right, (int, float))
        ]
        if not numeric:
            status = "undefined"
            reason = "no paired numeric values"
        else:
            status = "defined"
            metric_value = sum(abs(left - right) for left, right in numeric) / len(numeric)
    else:
        status = "defined"
        metric_value = (
            sum(_exact_match(field, left, right) for left, right in values)
            / len(values)
        )
    kappa: float | None = None
    kappa_reason: str | None = "not applicable to this field type"
    if field in KAPPA_FIELDS:
        kappa, kappa_reason = _cohens_kappa(values)
    return {
        "comparison_family": family,
        "left_id": left_id,
        "right_id": right_id,
        "case_id": case_id,
        "source_language": source_language,
        "document_id": document_id,
        "task_layer": task_layer,
        "field": field,
        "comparable_count": len(values),
        "exact_match_count": sum(
            _exact_match(field, left, right) for left, right in values
        ),
        "metric": {
            "name": metric_name,
            "status": status,
            "value": metric_value,
            "undefined_reason": reason,
        },
        "cohens_kappa": {
            "status": "defined" if kappa is not None else "undefined",
            "value": kappa,
            "undefined_reason": kappa_reason,
        },
    }


def _pair_observations(
    left: Sequence[Observation], right: Sequence[Observation]
) -> list[tuple[Observation, Observation]]:
    right_index = {observation.key: observation for observation in right}
    return [
        (observation, right_index[observation.key])
        for observation in left
        if observation.key in right_index
    ]


def _summaries(
    family: str,
    left_id: str,
    right_id: str,
    pairs: Sequence[tuple[Observation, Observation]],
    *,
    case_id: str,
    source_language: str,
    documents: Iterable[str],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str | None, str, str], list[tuple[Observation, Observation]]] = (
        defaultdict(list)
    )
    for pair in pairs:
        left = pair[0]
        grouped[(left.document_id, left.task_layer, left.field)].append(pair)
        grouped[(None, left.task_layer, left.field)].append(pair)
    fields_by_layer = {
        "identification": [field for field in REQUESTED_FIELDS if field.startswith("identification.")],
        "cmt": [field for field in REQUESTED_FIELDS if field.startswith("cmt.")],
        "interpretation": [
            field
            for field in REQUESTED_FIELDS
            if field.startswith("interpretation.")
        ],
    }
    for layer in fields_by_layer:
        fields_by_layer[layer].extend(["confidence", "uncertainty.status"])
    document_ids = sorted(set(documents))
    for layer, fields in fields_by_layer.items():
        for field in fields:
            grouped.setdefault((None, layer, field), [])
            for document in document_ids:
                grouped.setdefault((document, layer, field), [])
    return [
        _group_summary(
            family,
            left_id,
            right_id,
            field,
            grouped[(document_id, layer, field)],
            case_id=case_id,
            source_language=source_language,
            document_id=document_id,
            task_layer=layer,
        )
        for document_id, layer, field in sorted(
            grouped, key=lambda key: (key[0] or "", key[1], key[2])
        )
    ]


def load_references(root: Path, case_id: str) -> list[Observation]:
    case_root = root / "cases" / case_id
    observations: list[Observation] = []
    mipvu_root = case_root / "corpus" / "mipvu"
    for path in sorted(mipvu_root.glob("*_mipvu.json")):
        data = read_json_object(path)
        for unit in data.get("lexical_units", []):
            if not isinstance(unit, Mapping):
                continue
            unit_id = unit.get("mipvu_id")
            if not isinstance(unit_id, str):
                continue
            item = {
                "item_id": unit_id,
                "case_id": case_id,
                "source_language": unit.get("language", data.get("source_language", "")),
                "document_id": unit.get("document_id", data.get("document_id", "")),
                "sentence_id": unit.get("sentence_id", ""),
                "task_layer": "identification",
            }
            _add(
                observations,
                item=item,
                unit_id=unit_id,
                field="identification.decision",
                value=unit.get("decision_type"),
            )
            _add(
                observations,
                item=item,
                unit_id=unit_id,
                field="identification.boundary_decision",
                value="exact",
            )
            start = unit.get("sentence_char_offset_start")
            end = unit.get("sentence_char_offset_end")
            if isinstance(start, int) and isinstance(end, int) and end > start:
                _add(
                    observations,
                    item=item,
                    unit_id=unit_id,
                    field="identification.boundary_span",
                    value=list(range(start, end)),
                )
    annotated_root = case_root / "corpus" / "annotated"
    for path in sorted(annotated_root.glob("*_annotated.json")):
        data = read_json_object(path)
        for instance in data.get("instances", []):
            if not isinstance(instance, Mapping):
                continue
            instance_id = instance.get("instance_id")
            if not isinstance(instance_id, str):
                continue
            item = {
                "item_id": instance_id,
                "case_id": case_id,
                "source_language": "",
                "document_id": instance.get("document_id", data.get("document_id", "")),
                "sentence_id": instance.get("sentence_id", ""),
                "task_layer": "cmt",
            }
            cmt = instance.get("cmt")
            if isinstance(cmt, Mapping):
                for name in (
                    "source_domain_primary",
                    "source_domain_secondary",
                    "target_domain",
                    "conceptual_metaphor",
                    "entailments",
                    "cluster_id",
                ):
                    _add(
                        observations,
                        item=item,
                        unit_id=instance_id,
                        field=f"cmt.{name}",
                        value=cmt.get(name),
                    )
            confidence = _nested(instance, "meta", "confidence")
            _add(
                observations,
                item=item,
                unit_id=instance_id,
                field="confidence",
                value=confidence,
            )
    return observations


def compare_runs(
    root: Path,
    case_id: str,
    normalized: Mapping[str, Any],
) -> dict[str, Any]:
    if normalized.get("case_id") != case_id:
        raise ComparisonError(
            f"normalized case_id `{normalized.get('case_id')}` does not match `{case_id}`"
        )
    raw_runs = normalized.get("runs")
    if not isinstance(raw_runs, list) or len(raw_runs) < 2:
        raise ComparisonError("at least two validated normalized runs are required")
    flattened = [
        flatten_run(run, case_id) for run in raw_runs if isinstance(run, Mapping)
    ]
    run_ids = [run_id for run_id, _ in flattened]
    if len(run_ids) != len(set(run_ids)):
        raise ComparisonError("normalized runs contain duplicate run_id values")
    languages = {
        _run_metadata(run, case_id)[2] for run in raw_runs if isinstance(run, Mapping)
    }
    if len(languages) != 1:
        raise ComparisonError(
            "runs with different source_language values must be compared in separate cohorts"
        )
    language = next(iter(languages))
    model_pairs: list[dict[str, Any]] = []
    for (left_id, left), (right_id, right) in itertools.combinations(flattened, 2):
        pairs = _pair_observations(left, right)
        model_pairs.append(
            {
                "left_run_id": left_id,
                "right_run_id": right_id,
                "summaries": _summaries(
                    "model_vs_model",
                    left_id,
                    right_id,
                    pairs,
                    case_id=case_id,
                    source_language=language,
                    documents=(
                        observation.document_id
                        for observation in itertools.chain(left, right)
                    ),
                ),
            }
        )
    references = load_references(root, case_id)
    reference_runs = []
    for run_id, observations in flattened:
        pairs = _pair_observations(observations, references)
        reference_runs.append(
            {
                "run_id": run_id,
                "reference_id": f"{case_id}:accepted-reference",
                "summaries": _summaries(
                    "model_vs_reference",
                    run_id,
                    f"{case_id}:accepted-reference",
                    pairs,
                    case_id=case_id,
                    source_language=language,
                    documents=(
                        observation.document_id for observation in observations
                    ),
                ),
            }
        )
    return {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "generator": GENERATOR_PATH,
        "run_ids": sorted(run_ids),
        "comparison_families": {
            "model_vs_model": {"pairs": model_pairs},
            "model_vs_reference": {"runs": reference_runs},
        },
    }


def iter_summaries(result: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    families = result["comparison_families"]
    for pair in families["model_vs_model"]["pairs"]:
        yield from pair["summaries"]
    for run in families["model_vs_reference"]["runs"]:
        yield from run["summaries"]


def write_summary_csv(path: Path, result: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "comparison_family",
        "left_id",
        "right_id",
        "case_id",
        "source_language",
        "document_id",
        "task_layer",
        "field",
        "comparable_count",
        "exact_match_count",
        "metric_name",
        "metric_status",
        "metric_value",
        "metric_undefined_reason",
        "cohens_kappa_status",
        "cohens_kappa_value",
        "cohens_kappa_undefined_reason",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for summary in iter_summaries(result):
            metric = summary["metric"]
            kappa = summary["cohens_kappa"]
            writer.writerow(
                {
                    **{field: summary.get(field) for field in fields[:10]},
                    "metric_name": metric["name"],
                    "metric_status": metric["status"],
                    "metric_value": metric["value"],
                    "metric_undefined_reason": metric["undefined_reason"],
                    "cohens_kappa_status": kappa["status"],
                    "cohens_kappa_value": kappa["value"],
                    "cohens_kappa_undefined_reason": kappa["undefined_reason"],
                }
            )


def compute_case_agreement(root: Path, case_id: str) -> dict[str, Any]:
    root = root.resolve()
    case_root = root / "cases" / case_id
    if not case_root.is_dir():
        raise ComparisonError(f"unknown case `{case_id}`")
    normalized_path = (
        case_root / "quality" / "model-reliability" / "normalized" / "normalized-runs.json"
    )
    normalized = read_json_object(normalized_path)
    result = compare_runs(root, case_id, normalized)
    output_json = safe_output_path(
        case_root, "quality/model-reliability/comparisons/agreement-results.json"
    )
    output_csv = safe_output_path(
        case_root, "quality/model-reliability/comparisons/agreement-summary.csv"
    )
    write_json(output_json, result)
    write_summary_csv(output_csv, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    result = compute_case_agreement(args.root, args.case_id)
    print(
        f"Compared {len(result['run_ids'])} runs for {args.case_id}; "
        "wrote agreement-results.json and agreement-summary.csv"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
