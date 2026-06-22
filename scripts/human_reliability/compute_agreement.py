#!/usr/bin/env python3
"""Compute cohort-scoped layered human inter-annotator agreement metrics."""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

try:
    from scripts.human_reliability.boundaries import safe_output_path
    from scripts.human_reliability.ingest_submission import (
        _raw_digest,
        load_cohort_context,
        parse_csv_submission,
        parse_json_submission,
    )
    from scripts.human_reliability.submission_contract import validate_submission
except ModuleNotFoundError:
    from boundaries import safe_output_path  # type: ignore
    from ingest_submission import (  # type: ignore
        _raw_digest,
        load_cohort_context,
        parse_csv_submission,
        parse_json_submission,
    )
    from submission_contract import validate_submission  # type: ignore


ROOT = Path(__file__).resolve().parents[2]
GENERATOR_PATH = "scripts/human_reliability/compute_agreement.py"
GENERATOR_VERSION = "1.0.0"
POSITIVE_DECISIONS = {
    "mipvu_indirect",
    "mipvu_direct",
    "mipvu_implicit",
    "mipvu_personification",
}
NEGATIVE_DECISIONS = {"non_metaphor", "excluded_nonlexical"}
UNCERTAINTY_ORDER = {"none": 0, "low": 1, "material": 2, "unresolved": 3}
SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9._-]+$")

FIELD_SPECS = {
    "identification": [
        ("identification.decision_type", "binary_identification", "binary"),
        ("identification.boundary_response", "nominal", "category"),
        ("identification.selected_unit_boundary", "set_overlap", "set"),
        ("identification.contextual_meaning", "qualitative_only", "text"),
        ("identification.basic_meaning", "qualitative_only", "text"),
        ("identification.basic_meaning_source", "qualitative_only", "text"),
        ("identification.contrast_explanation", "qualitative_only", "text"),
        ("identification.comparison_basis", "qualitative_only", "text"),
    ],
    "cmt": [
        ("cmt.source_domain_primary", "nominal", "category"),
        ("cmt.source_domain_secondary", "set_overlap", "set"),
        ("cmt.target_domain", "nominal", "category"),
        ("cmt.conceptual_mapping", "qualitative_only", "text"),
        ("cmt.entailments", "set_overlap", "set"),
        ("cmt.cluster_id", "nominal", "category"),
        ("cmt.rival_reading", "qualitative_only", "text"),
    ],
    "interpretation": [
        ("interpretation.sacred_object", "nominal", "category"),
        ("interpretation.sacrificial_body", "nominal", "category"),
        ("interpretation.enemy_as_bringer_of_death", "nominal", "category"),
        ("interpretation.violence_logic", "nominal", "category"),
        ("interpretation.obligatory_frame", "nominal", "category"),
        ("interpretation.purification", "nominal", "category"),
        ("interpretation.agents", "set_overlap", "set"),
        ("interpretation.patients", "set_overlap", "set"),
        ("interpretation.beneficiaries", "set_overlap", "set"),
        ("interpretation.excluded_agents", "set_overlap", "set"),
        ("interpretation.absence_decision", "nominal", "category"),
        ("interpretation.absence_scope", "qualitative_only", "text"),
        ("interpretation.presence_criterion", "qualitative_only", "text"),
        ("interpretation.rival_reading", "qualitative_only", "text"),
    ],
}
COMMON_SPECS = [
    ("disposition", "nominal", "category"),
    ("confidence", "numeric_distance", "number"),
    ("uncertainty", "ordinal_distance", "ordinal"),
]


class AgreementError(ValueError):
    """Raised when normalized human runs are incomplete or not comparable."""


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgreementError(f"{path}: unable to read JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise AgreementError(f"{path}: expected a JSON object")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def code_revision(root: Path) -> str:
    for workdir in (root, ROOT):
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workdir,
            check=False,
            capture_output=True,
            text=True,
        )
        revision = result.stdout.strip()
        if result.returncode == 0 and revision:
            return revision
    raise AgreementError("unable to determine repository code revision")


def _vocabularies(root: Path) -> dict[str, set[str]]:
    data = read_json_object(root / "config" / "controlled-vocabularies.json")
    return {
        name: {
            str(entry["id"])
            for entry in entries
            if isinstance(entry, Mapping) and entry.get("id")
        }
        for name, entries in data.items()
        if isinstance(entries, list)
    }


def _cohort_manifest_path(
    case_root: Path,
    cohort_id: str,
    cohort_version: str,
) -> Path:
    cohort_root = (
        case_root / "quality" / "human-reliability" / "cohorts"
    )
    matches: list[Path] = []
    for path in sorted(cohort_root.glob("*.json")):
        value = read_json_object(path)
        if (
            value.get("cohort_id") == cohort_id
            and value.get("cohort_version") == cohort_version
        ):
            matches.append(path)
    if len(matches) != 1:
        raise AgreementError(
            f"expected one approved cohort manifest for `{cohort_id}` "
            f"`{cohort_version}`, found {len(matches)}"
        )
    return matches[0]


def _verify_raw_registrations(
    root: Path,
    case_root: Path,
    runs: Sequence[Mapping[str, Any]],
) -> None:
    register = read_json_object(
        case_root
        / "quality"
        / "human-reliability"
        / "submissions"
        / "submission-register.json"
    )
    entries = register.get("submissions")
    if register.get("case_id") != case_root.name or not isinstance(entries, list):
        raise AgreementError("submission register has invalid case identity or entries")
    by_registration = {
        str(entry.get("registration_id") or ""): entry
        for entry in entries
        if isinstance(entry, Mapping)
    }
    csv_contract = read_json_object(
        root / "schemas" / "human-reliability" / "submission-csv-contract.json"
    )
    for run in runs:
        registration_id = str(run.get("registration_id") or "")
        entry = by_registration.get(registration_id)
        if not isinstance(entry, Mapping) or entry.get("status") != "valid":
            raise AgreementError(
                f"normalized run `{registration_id}` has no valid registration"
            )
        if entry.get("raw_hash") != run.get("raw_hash"):
            raise AgreementError(
                f"normalized run `{registration_id}` raw hash differs from registration"
            )
        raw_dir = (
            case_root
            / "quality"
            / "human-reliability"
            / "submissions"
            / "raw"
            / registration_id
        )
        if entry.get("source_format") == "json":
            parsed = parse_json_submission(raw_dir / "submission.json")
        elif entry.get("source_format") == "csv":
            parsed = parse_csv_submission(raw_dir / "submission.csv", csv_contract)
        else:
            raise AgreementError(
                f"registration `{registration_id}` has unknown source format"
            )
        if parsed.errors:
            raise AgreementError(
                f"registered raw submission `{registration_id}` no longer parses cleanly"
            )
        if _raw_digest(parsed.raw_files) != run.get("raw_hash"):
            raise AgreementError(
                f"registered raw submission `{registration_id}` hash mismatch"
            )
        if parsed.envelope != _submission(run):
            raise AgreementError(
                f"normalized run `{registration_id}` differs from immutable raw submission"
            )


def _stat(
    value: float | None = None,
    *,
    status: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    resolved = status or ("defined" if value is not None else "undefined")
    return {
        "status": resolved,
        "value": value,
        "undefined_reason": reason,
    }


def _canonical_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {json.dumps(item, ensure_ascii=False, sort_keys=True) for item in value}


def _jaccard(left: Any, right: Any) -> float:
    left_set = _canonical_set(left)
    right_set = _canonical_set(right)
    union = left_set | right_set
    return 1.0 if not union else len(left_set & right_set) / len(union)


def _cohens_kappa(values: Sequence[tuple[Any, Any]]) -> tuple[float | None, str | None]:
    if len(values) < 2:
        return None, "fewer than two comparable observations"
    total = len(values)
    observed = sum(left == right for left, right in values) / total
    left_counts = Counter(json.dumps(left, ensure_ascii=False, sort_keys=True) for left, _ in values)
    right_counts = Counter(json.dumps(right, ensure_ascii=False, sort_keys=True) for _, right in values)
    expected = sum(
        (left_counts[label] / total) * (right_counts[label] / total)
        for label in set(left_counts) | set(right_counts)
    )
    if expected == 1.0:
        return None, "expected agreement is 1.0 because both coders are constant"
    return (observed - expected) / (1.0 - expected), None


def _binary_agreement(
    values: Sequence[tuple[Any, Any]],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    usable: list[tuple[bool, bool]] = []
    excluded = 0
    for left, right in values:
        if left in POSITIVE_DECISIONS:
            left_binary = True
        elif left in NEGATIVE_DECISIONS:
            left_binary = False
        else:
            excluded += 1
            continue
        if right in POSITIVE_DECISIONS:
            right_binary = True
        elif right in NEGATIVE_DECISIONS:
            right_binary = False
        else:
            excluded += 1
            continue
        usable.append((left_binary, right_binary))
    if not usable:
        reason = "no paired positive/negative decisions; uncertain values are excluded"
        return _stat(reason=reason), _stat(reason=reason), [
            f"{excluded} uncertain or non-binary pair(s) excluded"
        ]
    both_positive = sum(left and right for left, right in usable)
    both_negative = sum(not left and not right for left, right in usable)
    discordant = sum(left != right for left, right in usable)
    positive_denominator = 2 * both_positive + discordant
    negative_denominator = 2 * both_negative + discordant
    positive = (
        2 * both_positive / positive_denominator
        if positive_denominator
        else None
    )
    negative = (
        2 * both_negative / negative_denominator
        if negative_denominator
        else None
    )
    notes = [f"{excluded} uncertain or non-binary pair(s) excluded"] if excluded else []
    return (
        _stat(
            positive,
            reason="no positive decisions by either coder" if positive is None else None,
        ),
        _stat(
            negative,
            reason="no negative decisions by either coder" if negative is None else None,
        ),
        notes,
    )


def _submission(run: Mapping[str, Any]) -> Mapping[str, Any]:
    submission = run.get("submission")
    if not isinstance(submission, Mapping):
        raise AgreementError("every normalized run must contain a submission object")
    return submission


def _comparable_metadata(runs: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    required = (
        "case_id",
        "cohort_id",
        "cohort_version",
        "sample_id",
        "sample_version",
        "packet_id",
        "packet_hash",
        "source_language",
        "task_layer",
        "codebook_version",
        "training_version",
        "calibration_id",
    )
    submissions = [_submission(run) for run in runs]
    metadata: dict[str, str] = {}
    for field in required:
        values = {str(submission.get(field) or "") for submission in submissions}
        if len(values) != 1 or "" in values:
            raise AgreementError(
                f"normalized runs differ on `{field}` and cannot be pooled or compared"
            )
        metadata[field] = next(iter(values))
    coder_ids = [str(submission.get("coder_id") or "") for submission in submissions]
    if "" in coder_ids or len(coder_ids) != len(set(coder_ids)):
        raise AgreementError("agreement requires distinct non-empty primary coder IDs")
    if any(submission.get("coder_role") != "primary" for submission in submissions):
        raise AgreementError("agreement uses primary coder submissions only")
    return metadata


def _response_index(submission: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    responses = submission.get("responses")
    if not isinstance(responses, list):
        raise AgreementError("submission responses must be an array")
    index: dict[str, Mapping[str, Any]] = {}
    for response in responses:
        if not isinstance(response, Mapping):
            continue
        item_id = str(response.get("item_id") or "")
        if not item_id or item_id in index:
            raise AgreementError(f"missing or duplicate response item ID `{item_id}`")
        index[item_id] = response
    return index


def _extract(response: Mapping[str, Any], field: str) -> Any:
    if field in {"disposition", "confidence", "uncertainty"}:
        return response.get(field)
    prefix, name = field.split(".", 1)
    if prefix == "identification":
        raise AgreementError("identification lexical fields require unit-level extraction")
    payload = response.get(f"{prefix}_response")
    return payload.get(name) if isinstance(payload, Mapping) else None


def _identification_units(response: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    values = response.get("lexical_unit_responses")
    if not isinstance(values, list):
        return {}
    result: dict[str, Mapping[str, Any]] = {}
    for value in values:
        if not isinstance(value, Mapping):
            continue
        unit_id = str(value.get("lexical_unit_id") or "")
        if unit_id:
            result[unit_id] = value
    return result


def _pairs_for_field(
    left: Mapping[str, Mapping[str, Any]],
    right: Mapping[str, Mapping[str, Any]],
    field: str,
) -> tuple[list[tuple[Any, Any]], int]:
    values: list[tuple[Any, Any]] = []
    missing = 0
    for item_id in sorted(set(left) | set(right)):
        left_response = left.get(item_id)
        right_response = right.get(item_id)
        if left_response is None or right_response is None:
            missing += 1
            continue
        if field != "disposition" and (
            left_response.get("disposition") != "coded"
            or right_response.get("disposition") != "coded"
        ):
            missing += 1
            continue
        if field.startswith("identification.") and field != "identification.selected_unit_boundary":
            name = field.split(".", 1)[1]
            left_units = _identification_units(left_response)
            right_units = _identification_units(right_response)
            for unit_id in sorted(set(left_units) | set(right_units)):
                left_unit = left_units.get(unit_id)
                right_unit = right_units.get(unit_id)
                if left_unit is None or right_unit is None:
                    missing += 1
                    continue
                left_value = left_unit.get(name)
                right_value = right_unit.get(name)
                if left_value is None or right_value is None:
                    missing += 1
                else:
                    values.append((left_value, right_value))
            continue
        if field == "identification.selected_unit_boundary":
            left_positive = [
                unit_id
                for unit_id, unit in _identification_units(left_response).items()
                if unit.get("decision_type") in POSITIVE_DECISIONS
            ]
            right_positive = [
                unit_id
                for unit_id, unit in _identification_units(right_response).items()
                if unit.get("decision_type") in POSITIVE_DECISIONS
            ]
            values.append((left_positive, right_positive))
            continue
        left_value = _extract(left_response, field)
        right_value = _extract(right_response, field)
        if left_value is None or right_value is None:
            missing += 1
        else:
            values.append((left_value, right_value))
    return values, missing


def _sample_assessment(count: int) -> str:
    if count == 0:
        return "unavailable"
    return "sparse" if count < 20 else "adequate"


def _field_metric(
    task_layer: str,
    field: str,
    family: str,
    value_type: str,
    values: Sequence[tuple[Any, Any]],
    missing: int,
) -> dict[str, Any]:
    exact = sum(
        _canonical_set(left) == _canonical_set(right)
        if family == "set_overlap"
        else left == right
        for left, right in values
    )
    count = len(values)
    notes: list[str] = []
    observed_not_applicable = {
        "qualitative_only": "free-text fields require qualitative disagreement review",
        "numeric_distance": "confidence is reported as numeric distance, not nominal agreement",
        "ordinal_distance": "uncertainty is reported as ordinal distance, not nominal agreement",
    }
    if family in observed_not_applicable:
        observed = _stat(
            status="not_applicable",
            reason=observed_not_applicable[family],
        )
    elif count:
        observed = _stat(exact / count)
    else:
        observed = _stat(reason="no comparable observations")
    kappa = _stat(status="not_applicable", reason="not applicable to this field type")
    positive = _stat(status="not_applicable", reason="not a binary identification field")
    negative = _stat(status="not_applicable", reason="not a binary identification field")
    jaccard = _stat(status="not_applicable", reason="not a set-valued field")
    absolute = _stat(status="not_applicable", reason="not a numeric field")
    ordinal = _stat(status="not_applicable", reason="not an ordinal field")
    if family in {"nominal", "binary_identification"}:
        kappa_value, kappa_reason = _cohens_kappa(values)
        kappa = _stat(kappa_value, reason=kappa_reason)
    if family == "binary_identification":
        positive, negative, binary_notes = _binary_agreement(values)
        notes.extend(binary_notes)
    if family == "set_overlap":
        jaccard = (
            _stat(sum(_jaccard(left, right) for left, right in values) / count)
            if count
            else _stat(reason="no comparable set-valued observations")
        )
    if family == "numeric_distance":
        numeric = [
            (float(left), float(right))
            for left, right in values
            if isinstance(left, (int, float)) and isinstance(right, (int, float))
        ]
        absolute = (
            _stat(sum(abs(left - right) for left, right in numeric) / len(numeric))
            if numeric
            else _stat(reason="no paired numeric confidence values")
        )
    if family == "ordinal_distance":
        ordered = [
            (UNCERTAINTY_ORDER[left], UNCERTAINTY_ORDER[right])
            for left, right in values
            if left in UNCERTAINTY_ORDER and right in UNCERTAINTY_ORDER
        ]
        ordinal = (
            _stat(
                sum(abs(left - right) / 3 for left, right in ordered) / len(ordered)
            )
            if ordered
            else _stat(reason="no paired controlled uncertainty values")
        )
    if count and count < 20:
        notes.append("sparse sample: fewer than 20 comparable observations")
    if missing:
        notes.append(f"{missing} missing or out-of-scope observation(s)")
    return {
        "task_layer": task_layer,
        "field": field,
        "metric_family": family,
        "value_type": value_type,
        "comparable_count": count,
        "missing_count": missing,
        "exact_match_count": exact,
        "sample_assessment": _sample_assessment(count),
        "observed_agreement": observed,
        "cohens_kappa": kappa,
        "positive_agreement": positive,
        "negative_agreement": negative,
        "mean_jaccard": jaccard,
        "mean_absolute_difference": absolute,
        "mean_ordinal_distance": ordinal,
        "notes": notes,
    }


def compare_cohort(
    case_id: str,
    normalized: Mapping[str, Any],
    cohort_id: str,
    cohort_version: str,
    *,
    revision: str = "in-memory-comparison",
) -> dict[str, Any]:
    if normalized.get("case_id") != case_id:
        raise AgreementError("normalized coder runs do not match requested case")
    raw_runs = normalized.get("runs")
    if not isinstance(raw_runs, list):
        raise AgreementError("normalized coder runs must contain a runs array")
    runs = [
        run
        for run in raw_runs
        if isinstance(run, Mapping)
        and run.get("cohort_id") == cohort_id
        and run.get("cohort_version") == cohort_version
    ]
    if len(runs) < 2:
        raise AgreementError("at least two validated primary coder runs are required")
    metadata = _comparable_metadata(runs)
    if metadata["case_id"] != case_id:
        raise AgreementError("cohort submissions do not match requested case")
    indexes = [
        (str(_submission(run)["coder_id"]), _response_index(_submission(run)))
        for run in runs
    ]
    item_ids = set().union(*(set(index) for _, index in indexes))
    if any(set(index) != item_ids for _, index in indexes):
        raise AgreementError("all coder runs must contain identical packet item IDs")
    field_pairs: dict[str, list[tuple[Any, Any]]] = defaultdict(list)
    missing_counts: Counter[str] = Counter()
    coder_pairs: list[dict[str, Any]] = []
    pair_count = 0
    for (left_id, left), (right_id, right) in itertools.combinations(indexes, 2):
        pair_count += 1
        pair_values: dict[str, list[tuple[Any, Any]]] = {}
        pair_missing: dict[str, int] = {}
        for field, _, _ in FIELD_SPECS[metadata["task_layer"]] + COMMON_SPECS:
            values, missing = _pairs_for_field(left, right, field)
            pair_values[field] = values
            pair_missing[field] = missing
            field_pairs[field].extend(values)
            missing_counts[field] += missing
        coder_pairs.append(
            {
                "left_coder_id": left_id,
                "right_coder_id": right_id,
                "field_metrics": [
                    _field_metric(
                        metadata["task_layer"],
                        field,
                        family,
                        value_type,
                        pair_values[field],
                        pair_missing[field],
                    )
                    for field, family, value_type in (
                        FIELD_SPECS[metadata["task_layer"]] + COMMON_SPECS
                    )
                ],
            }
        )
    metrics = [
        _field_metric(
            metadata["task_layer"],
            field,
            family,
            value_type,
            field_pairs[field],
            missing_counts[field],
        )
        for field, family, value_type in FIELD_SPECS[metadata["task_layer"]] + COMMON_SPECS
    ]
    out_of_scope: Counter[str] = Counter()
    lexical_units: set[str] = set()
    for _, index in indexes:
        for response in index.values():
            if response.get("disposition") == "out_of_scope":
                out_of_scope[str(response.get("out_of_scope_reason") or "unspecified")] += 1
            lexical_units.update(str(value) for value in response.get("lexical_unit_ids", []))
    return {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "cohort_id": cohort_id,
        "cohort_version": cohort_version,
        "source_language": metadata["source_language"],
        "task_layer": metadata["task_layer"],
        "packet_id": metadata["packet_id"],
        "coder_ids": sorted(coder_id for coder_id, _ in indexes),
        "input_runs": sorted(
            [
                {
                    "registration_id": str(run.get("registration_id") or ""),
                    "raw_hash": str(run.get("raw_hash") or ""),
                    "submission_id": str(_submission(run).get("submission_id") or ""),
                    "coder_id": str(_submission(run).get("coder_id") or ""),
                }
                for run in runs
            ],
            key=lambda value: value["coder_id"],
        ),
        "generator": {
            "script": GENERATOR_PATH,
            "version": GENERATOR_VERSION,
            "script_hash": sha256_bytes(Path(__file__).read_bytes()),
            "code_revision": revision,
        },
        "scope": {
            "pooled": False,
            "pair_count": pair_count,
            "item_count": len(item_ids),
            "lexical_unit_count": len(lexical_units),
            "out_of_scope_counts": dict(sorted(out_of_scope.items())),
        },
        "coder_pairs": coder_pairs,
        "field_metrics": metrics,
    }


def write_summary_csv(path: Path, result: Mapping[str, Any]) -> None:
    fields = [
        "scope", "left_coder_id", "right_coder_id",
        "case_id", "cohort_id", "cohort_version", "source_language",
        "task_layer", "field", "metric_family", "value_type",
        "comparable_count", "missing_count", "exact_match_count",
        "sample_assessment", "observed_agreement", "cohens_kappa",
        "positive_agreement", "negative_agreement", "mean_jaccard",
        "mean_absolute_difference", "mean_ordinal_distance", "notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        rows = [
            ("cohort", "", "", metric)
            for metric in result["field_metrics"]
        ]
        rows.extend(
            (
                "coder_pair",
                pair["left_coder_id"],
                pair["right_coder_id"],
                metric,
            )
            for pair in result["coder_pairs"]
            for metric in pair["field_metrics"]
        )
        for scope, left_coder_id, right_coder_id, metric in rows:
            writer.writerow(
                {
                    "scope": scope,
                    "left_coder_id": left_coder_id,
                    "right_coder_id": right_coder_id,
                    "case_id": result["case_id"],
                    "cohort_id": result["cohort_id"],
                    "cohort_version": result["cohort_version"],
                    "source_language": result["source_language"],
                    **{
                        key: metric[key]
                        for key in (
                            "task_layer", "field", "metric_family", "value_type",
                            "comparable_count", "missing_count", "exact_match_count",
                            "sample_assessment",
                        )
                    },
                    "observed_agreement": metric["observed_agreement"]["value"],
                    "cohens_kappa": metric["cohens_kappa"]["value"],
                    "positive_agreement": metric["positive_agreement"]["value"],
                    "negative_agreement": metric["negative_agreement"]["value"],
                    "mean_jaccard": metric["mean_jaccard"]["value"],
                    "mean_absolute_difference": metric["mean_absolute_difference"]["value"],
                    "mean_ordinal_distance": metric["mean_ordinal_distance"]["value"],
                    "notes": " | ".join(metric["notes"]),
                }
            )


def compute_case_agreement(
    root: Path,
    case_id: str,
    cohort_id: str,
    cohort_version: str,
) -> dict[str, Any]:
    root = root.resolve()
    for label, value in (
        ("case_id", case_id),
        ("cohort_id", cohort_id),
        ("cohort_version", cohort_version),
    ):
        if not SAFE_COMPONENT.fullmatch(value):
            raise AgreementError(f"unsafe {label} `{value}`")
    case_root = root / "cases" / case_id
    normalized = read_json_object(
        case_root
        / "quality"
        / "human-reliability"
        / "normalized"
        / "normalized-coder-runs.json"
    )
    normalized_schema = read_json_object(
        root / "schemas" / "human-reliability" / "normalized-coder-runs-schema.json"
    )
    normalized_errors = sorted(
        Draft202012Validator(
            normalized_schema, format_checker=FormatChecker()
        ).iter_errors(normalized),
        key=lambda error: list(error.absolute_path),
    )
    if normalized_errors:
        raise AgreementError(
            "normalized coder runs fail schema validation: "
            + "; ".join(error.message for error in normalized_errors)
        )
    cohort_path = _cohort_manifest_path(case_root, cohort_id, cohort_version)
    cohort = load_cohort_context(root, case_id, cohort_path)
    submission_schema = read_json_object(
        root / "schemas" / "human-reliability" / "submission-schema.json"
    )
    relevant_runs = [
        run
        for run in normalized.get("runs", [])
        if isinstance(run, Mapping)
        and run.get("cohort_id") == cohort_id
        and run.get("cohort_version") == cohort_version
    ]
    _verify_raw_registrations(root, case_root, relevant_runs)
    contextual_errors: list[str] = []
    for run in relevant_runs:
        submission = _submission(run)
        contextual_errors.extend(
            validate_submission(
                submission,
                cohort.validation_context,
                schema=submission_schema,
                vocabularies=_vocabularies(root),
            )
        )
    if contextual_errors:
        raise AgreementError(
            "normalized submissions fail cohort validation: "
            + "; ".join(dict.fromkeys(contextual_errors))
        )
    status = read_json_object(
        case_root / "quality" / "human-reliability" / "ingestion-status.json"
    )
    status_schema = read_json_object(
        root / "schemas" / "human-reliability" / "ingestion-status-schema.json"
    )
    status_errors = sorted(
        Draft202012Validator(status_schema).iter_errors(status),
        key=lambda error: list(error.absolute_path),
    )
    if status_errors:
        raise AgreementError(
            "ingestion status fails schema validation: "
            + "; ".join(error.message for error in status_errors)
        )
    cohort_status = next(
        (
            value
            for value in status.get("cohorts", [])
            if isinstance(value, Mapping)
            and value.get("cohort_id") == cohort_id
            and value.get("cohort_version") == cohort_version
        ),
        None,
    )
    if not isinstance(cohort_status, Mapping) or cohort_status.get("state") != "complete":
        raise AgreementError(
            "cohort ingestion must be `complete` before agreement computation"
        )
    result = compare_cohort(
        case_id,
        normalized,
        cohort_id,
        cohort_version,
        revision=code_revision(root),
    )
    if set(result["coder_ids"]) != set(cohort_status.get("valid_primary_coders", [])):
        raise AgreementError(
            "normalized coder IDs do not match completed ingestion status"
        )
    if len(result["input_runs"]) != cohort_status.get("valid_submission_count"):
        raise AgreementError(
            "normalized run count does not match completed ingestion status"
        )
    result_schema = read_json_object(
        root / "schemas" / "human-reliability" / "agreement-results-schema.json"
    )
    result_errors = sorted(
        Draft202012Validator(result_schema).iter_errors(result),
        key=lambda error: list(error.absolute_path),
    )
    if result_errors:
        raise AgreementError(
            "agreement result fails schema validation: "
            + "; ".join(error.message for error in result_errors)
        )
    output_root = (
        f"quality/human-reliability/comparisons/"
        f"{cohort_id}-{cohort_version}"
    )
    json_path = safe_output_path(case_root, f"{output_root}/human-agreement.json")
    csv_path = safe_output_path(case_root, f"{output_root}/human-agreement.csv")
    write_json(json_path, result)
    write_summary_csv(csv_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument("--cohort", dest="cohort_id", required=True)
    parser.add_argument("--cohort-version", required=True)
    args = parser.parse_args()
    try:
        result = compute_case_agreement(
            ROOT, args.case_id, args.cohort_id, args.cohort_version
        )
    except AgreementError as exc:
        parser.error(str(exc))
    print(
        f"{args.case_id}: compared {len(result['coder_ids'])} coders in "
        f"{result['cohort_id']} {result['cohort_version']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
