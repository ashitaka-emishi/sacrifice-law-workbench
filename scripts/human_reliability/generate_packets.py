#!/usr/bin/env python3
"""Generate deterministic blind human coding packets from an approved sample."""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator

try:
    from scripts.human_reliability.boundaries import safe_output_path
except ModuleNotFoundError:
    from boundaries import safe_output_path  # type: ignore


ROOT = Path(__file__).resolve().parents[2]
GENERATOR_VERSION = "1.0.0"
GENERATOR_PATH = "scripts/human_reliability/generate_packets.py"
TASK_LAYERS = {"identification", "cmt", "interpretation"}
PROHIBITED_PACKET_KEYS = frozenset(
    {
        "accepted_decision",
        "adjudicated_decision",
        "ambiguity_flag",
        "claim_impact",
        "confidence",
        "decision_type",
        "design_roles",
        "ideological_functions",
        "interpretation",
        "justification",
        "koenigsberg",
        "mapping_status",
        "meta",
        "review_notes",
        "review_status",
        "rhetorical_functions",
        "rival_reading",
        "support_score",
        "target_domain",
    }
)
PROHIBITED_TEMPLATE_KEYS = frozenset(
    {
        "accepted_decision", "adjudicated_decision", "claim_impact",
        "design_roles", "ideological_functions", "koenigsberg", "meta",
        "model_output", "review_status", "rhetorical_functions", "support_score",
    }
)
ANSWER_TEMPLATE_KEYS = frozenset(
    {
        "decision_type", "confidence", "target_domain", "rival_reading",
        "interpretation", "justification", "uncertainty", "disposition",
    }
)

SUBMISSION_COLUMNS = [
    "schema_version", "submission_id", "cohort_id", "cohort_version",
    "case_id", "sample_id", "sample_version", "packet_id", "packet_hash",
    "source_language", "task_layer", "codebook_version", "coder_id",
    "coder_role", "qualification_attested", "source_language_qualified",
    "training_version", "training_completed_at", "calibration_id",
    "calibration_completed_at", "conflict_status", "conflict_details",
    "independence_attested", "ai_assistance_used", "completed_at",
]
COMMON_COLUMNS = SUBMISSION_COLUMNS + [
    "item_id", "document_id", "sentence_id", "source_span_id",
    "disposition", "confidence", "uncertainty", "uncertainty_note",
    "out_of_scope_reason", "notes", "case_fields",
]
LAYER_COLUMNS = {
    "identification": [
        "lexical_unit_id", "boundary_response", "decision_type",
        "contextual_meaning", "basic_meaning", "basic_meaning_source",
        "contrast_explanation", "comparison_basis",
    ],
    "cmt": [
        "lexical_unit_ids", "source_domain_primary", "source_domain_secondary", "target_domain",
        "conceptual_mapping", "entailments", "cluster_id", "rival_reading",
    ],
    "interpretation": [
        "lexical_unit_ids", "sacred_object", "sacrificial_body", "enemy_as_bringer_of_death",
        "violence_logic", "obligatory_frame", "purification", "agents",
        "patients", "beneficiaries", "excluded_agents", "absence_decision",
        "absence_scope", "presence_criterion", "rival_reading",
    ],
}


class PacketGenerationError(ValueError):
    """Raised when a sample cannot produce a valid blind packet."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def hash_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PacketGenerationError(f"required input not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PacketGenerationError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PacketGenerationError(f"expected an object in {path}")
    return value


def validate_sample_schema(root: Path, sample: Mapping[str, Any]) -> None:
    schema_path = root / "schemas" / "human-reliability" / "sample-manifest-schema.json"
    if not schema_path.is_file():
        schema_path = ROOT / "schemas" / "human-reliability" / "sample-manifest-schema.json"
    schema = read_json(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(sample), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        location = ".".join(str(value) for value in first.path) or "<root>"
        raise PacketGenerationError(f"sample schema error at `{location}`: {first.message}")


def sample_hash(sample: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(sample))
    approval = payload.get("approval")
    if isinstance(approval, dict):
        approval["manifest_sha256"] = None
    return sha256_bytes(canonical_json_bytes(payload))


def code_revision(root: Path) -> str:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", GENERATOR_PATH],
        cwd=root, check=True, capture_output=True, text=True,
    )
    revision = result.stdout.strip()
    if not revision:
        raise PacketGenerationError(f"generator has no committed revision: {GENERATOR_PATH}")
    return revision


def relative_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise PacketGenerationError(f"path escapes repository root: {path}") from exc


def iter_sentences(document: Mapping[str, Any]) -> Iterable[dict[str, Any]]:
    for section in document.get("sections", []) or []:
        for paragraph in section.get("paragraphs", []) or []:
            for sentence in paragraph.get("sentences", []) or []:
                if isinstance(sentence, dict):
                    yield sentence


def walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key)
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def assert_blind(items: Iterable[Mapping[str, Any]]) -> None:
    for item in items:
        leaked = sorted(PROHIBITED_PACKET_KEYS.intersection(walk_keys(item)))
        if leaked:
            raise PacketGenerationError(
                f"packet item `{item.get('item_id', '<unknown>')}` leaks prohibited key(s): "
                + ", ".join(leaked)
            )


def assert_blank_templates(value: Any, item_id: str = "<template>") -> None:
    if isinstance(value, Mapping):
        forbidden = sorted(PROHIBITED_TEMPLATE_KEYS.intersection(str(key) for key in value))
        if forbidden:
            raise PacketGenerationError(
                f"response template `{item_id}` contains prohibited key(s): " + ", ".join(forbidden)
            )
        for key, child in value.items():
            if str(key) in ANSWER_TEMPLATE_KEYS and child not in (None, "", [], {}):
                raise PacketGenerationError(
                    f"response template `{item_id}` pre-populates answer field `{key}`"
                )
            assert_blank_templates(child, item_id)
    elif isinstance(value, list):
        for child in value:
            assert_blank_templates(child, item_id)


def lexical_payload(unit: Mapping[str, Any]) -> dict[str, Any]:
    unit_id = str(unit.get("mipvu_id") or "")
    source_text = str(unit.get("lexical_unit") or "")
    start = unit.get("sentence_char_offset_start", unit.get("char_offset_start"))
    end = unit.get("sentence_char_offset_end", unit.get("char_offset_end"))
    if not unit_id or not source_text or not isinstance(start, int) or not isinstance(end, int) or end <= start:
        raise PacketGenerationError(f"invalid lexical source fields for `{unit_id or '<unknown>'}`")
    payload: dict[str, Any] = {
        "lexical_unit_id": unit_id,
        "source_text": source_text,
        "char_offset_start": start,
        "char_offset_end": end,
    }
    if isinstance(unit.get("gloss_en"), str) and unit["gloss_en"]:
        payload["gloss_en"] = unit["gloss_en"]
    return payload


def csv_bytes(rows: list[dict[str, Any]], columns: list[str]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def jsonl_bytes(items: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(item) + b"\n" for item in items)


def write_if_changed(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def generate_packets(
    root: Path,
    case_id: str,
    *,
    sample_path: Path | None = None,
    revision: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    case_root = root / "cases" / case_id
    if not case_root.is_dir():
        raise PacketGenerationError(f"unknown case `{case_id}`")
    sample_path = (sample_path or case_root / "quality" / "human-reliability" / "samples" / "sample-manifest.json").resolve()
    sample = read_json(sample_path)
    validate_sample_schema(root, sample)
    if sample.get("status") != "approved" or sample.get("case_id") != case_id:
        raise PacketGenerationError("sample must be approved and match the requested case")
    execution = sample.get("execution", {})
    if not isinstance(execution, dict) or execution.get("status") != "approved_to_execute":
        raise PacketGenerationError("sample execution must be `approved_to_execute`")
    approval = sample.get("approval", {})
    expected_sample_hash = approval.get("manifest_sha256") if isinstance(approval, dict) else None
    actual_sample_hash = sample_hash(sample)
    if expected_sample_hash != actual_sample_hash:
        raise PacketGenerationError("sample approval.manifest_sha256 does not match canonical sample content")

    layer = str(sample.get("task_layer") or "")
    source_language = str(sample.get("source_language") or "")
    sample_id = str(sample.get("sample_id") or "")
    sample_version = str(sample.get("sample_version") or "")
    frame = sample.get("frame", {})
    rights_constraints = sorted({str(v) for v in frame.get("rights_constraints", []) if v}) if isinstance(frame, dict) else []
    if layer not in TASK_LAYERS or not source_language or not sample_id or not sample_version or not rights_constraints:
        raise PacketGenerationError("sample layer, identity, language, and rights constraints are required")
    items = sample.get("items")
    if not isinstance(items, list) or not items:
        raise PacketGenerationError("sample items must be a non-empty array")

    manifest_path = case_root / "metadata" / "document-manifest.json"
    manifest = read_json(manifest_path)
    documents = {
        str(doc.get("document_id") or doc.get("id") or ""): doc
        for doc in manifest.get("documents", []) if isinstance(doc, dict)
    }
    sentence_lookup: dict[str, tuple[str, dict[str, Any]]] = {}
    unit_lookup: dict[str, dict[str, Any]] = {}
    annotation_lookup: dict[str, dict[str, Any]] = {}
    source_paths: set[Path] = {sample_path, manifest_path}
    selected_docs = sorted({str(item.get("document_id") or "") for item in items if isinstance(item, dict)})
    for document_id in selected_docs:
        document = documents.get(document_id)
        if not document:
            raise PacketGenerationError(f"unknown sampled document `{document_id}`")
        segmented_path = case_root / "corpus" / "segmented" / f"{document_id}.json"
        mipvu_path = case_root / "corpus" / "mipvu" / f"{document_id}_mipvu.json"
        annotated_path = case_root / "corpus" / "annotated" / f"{document_id}_annotated.json"
        segmented = read_json(segmented_path)
        mipvu = read_json(mipvu_path)
        source_paths.update({segmented_path, mipvu_path})
        for sentence in iter_sentences(segmented):
            sentence_id = str(sentence.get("sentence_id") or "")
            if sentence_id:
                sentence_lookup[sentence_id] = (document_id, sentence)
        for unit in mipvu.get("lexical_units", []) or []:
            if isinstance(unit, dict) and unit.get("mipvu_id"):
                unit_lookup[str(unit["mipvu_id"])] = unit
        if annotated_path.exists():
            annotated = read_json(annotated_path)
            source_paths.add(annotated_path)
            for annotation in annotated.get("instances", []) or []:
                if isinstance(annotation, dict) and annotation.get("instance_id"):
                    annotation_lookup[str(annotation["instance_id"])] = annotation

    packet_id = f"{sample_id}-{sample_version}-{layer}"
    template_metadata = {
        "schema_version": "1.0.0",
        "submission_id": "",
        "cohort_id": "",
        "cohort_version": "",
        "case_id": case_id,
        "sample_id": sample_id,
        "sample_version": sample_version,
        "packet_id": packet_id,
        "packet_hash": "",
        "source_language": source_language,
        "task_layer": layer,
        "codebook_version": str(frame.get("codebook_version") or ""),
        "coder_id": "",
        "coder_role": "primary",
        "qualification_attested": "",
        "source_language_qualified": "",
        "training_version": "",
        "training_completed_at": "",
        "calibration_id": "",
        "calibration_completed_at": "",
        "conflict_status": "",
        "conflict_details": "",
        "independence_attested": "",
        "ai_assistance_used": "",
        "completed_at": "",
    }
    packet_items: list[dict[str, Any]] = []
    response_rows: list[dict[str, Any]] = []
    response_json_items: list[dict[str, Any]] = []
    seen_item_ids: set[str] = set()
    seen_source_keys: set[tuple[str, str | None]] = set()
    for sample_item in items:
        if not isinstance(sample_item, dict):
            raise PacketGenerationError("sample item must be an object")
        item_id = str(sample_item.get("item_id") or "")
        document_id = str(sample_item.get("document_id") or "")
        sentence_id = str(sample_item.get("sentence_id") or "")
        source_span_id = sample_item.get("source_span_id")
        source_span_id = str(source_span_id) if source_span_id else None
        if not item_id or item_id in seen_item_ids:
            raise PacketGenerationError(f"missing or duplicate sample item_id `{item_id}`")
        seen_item_ids.add(item_id)
        source_key = (sentence_id, source_span_id)
        if source_key in seen_source_keys:
            raise PacketGenerationError(f"duplicate sampled source `{sentence_id}` / `{source_span_id}`")
        seen_source_keys.add(source_key)
        sentence_record = sentence_lookup.get(sentence_id)
        if not sentence_record or sentence_record[0] != document_id:
            raise PacketGenerationError(f"item `{item_id}` has unknown or mismatched sentence `{sentence_id}`")
        sentence = sentence_record[1]
        sentence_units = sorted(
            (u for u in unit_lookup.values() if str(u.get("sentence_id") or "") == sentence_id),
            key=lambda u: (int(u.get("sentence_unit_ordinal") or 0), str(u.get("mipvu_id") or "")),
        )
        if not sentence_units:
            raise PacketGenerationError(f"item `{item_id}` sentence has no lexical units")
        wrong_languages = {str(u.get("language") or "") for u in sentence_units if str(u.get("language") or "") != source_language}
        if wrong_languages:
            raise PacketGenerationError(f"item `{item_id}` contains language(s) outside `{source_language}`")
        if layer == "identification":
            focal_units = sentence_units
        elif source_span_id in unit_lookup:
            focal_units = [unit_lookup[source_span_id]]
        elif source_span_id in annotation_lookup:
            annotation = annotation_lookup[source_span_id]
            focal_ids = [str(v) for v in annotation.get("mipvu_ids", []) if v]
            focal_units = [unit_lookup[v] for v in focal_ids if v in unit_lookup]
            if len(focal_units) != len(focal_ids):
                raise PacketGenerationError(f"item `{item_id}` annotation references unknown lexical units")
        elif source_span_id is None:
            focal_units = sentence_units
        else:
            raise PacketGenerationError(f"item `{item_id}` has unknown source_span_id `{source_span_id}`")
        mismatched_units = [
            str(unit.get("mipvu_id") or "")
            for unit in focal_units
            if str(unit.get("document_id") or "") != document_id
            or str(unit.get("sentence_id") or "") != sentence_id
        ]
        if mismatched_units:
            raise PacketGenerationError(
                f"item `{item_id}` source span belongs to another document or sentence: "
                + ", ".join(mismatched_units)
            )
        packet_item = {
            "schema_version": "1.0.0",
            "packet_id": packet_id,
            "item_id": item_id,
            "task_layer": layer,
            "case_id": case_id,
            "document_id": document_id,
            "sentence_id": sentence_id,
            "source_span_id": source_span_id,
            "source_language": source_language,
            "sentence_source_text": str(sentence.get("text") or ""),
            "lexical_units": [lexical_payload(unit) for unit in focal_units],
            "context_scope": str(sample_item.get("context_scope") or ""),
            "rights_constraints": rights_constraints,
        }
        if not packet_item["sentence_source_text"] or not packet_item["context_scope"]:
            raise PacketGenerationError(f"item `{item_id}` lacks source text or context scope")
        packet_items.append(packet_item)
        common = {
            **template_metadata,
            "packet_id": packet_id,
            "item_id": item_id,
            "document_id": document_id,
            "sentence_id": sentence_id,
            "source_span_id": source_span_id or "",
        }
        if layer == "identification":
            for unit in focal_units:
                response_rows.append({**common, "lexical_unit_id": unit["mipvu_id"]})
        else:
            response_rows.append({
                **common,
                "lexical_unit_ids": json.dumps(
                    [str(unit["mipvu_id"]) for unit in focal_units],
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            })
        response_item = {
            **common,
            "task_layer": layer,
            "source_span_id": source_span_id,
            "lexical_unit_ids": [str(unit["mipvu_id"]) for unit in focal_units],
            "disposition": None,
            "confidence": None,
            "uncertainty": None,
            "uncertainty_note": None,
            "out_of_scope_reason": None,
            "notes": None,
            "case_fields": {},
        }
        for metadata_key in SUBMISSION_COLUMNS:
            response_item.pop(metadata_key, None)
        response_item["task_layer"] = layer
        if layer == "identification":
            response_item["lexical_unit_responses"] = [
                {
                    "lexical_unit_id": str(unit["mipvu_id"]),
                    **{
                        column: None
                        for column in LAYER_COLUMNS[layer]
                        if column != "lexical_unit_id"
                    },
                }
                for unit in focal_units
            ]
        else:
            response_item[f"{layer}_response"] = {
                column: None
                for column in LAYER_COLUMNS[layer]
                if column != "lexical_unit_ids"
            }
        response_json_items.append(response_item)

    seed = str(sample.get("selection", {}).get("seed") or "")
    if not seed:
        raise PacketGenerationError("sample selection seed is required")
    packet_items.sort(key=lambda item: hashlib.sha256(f"{seed}:{item['item_id']}".encode()).hexdigest())
    response_rows.sort(key=lambda row: (str(row["item_id"]), str(row.get("lexical_unit_id") or "")))
    response_json_items.sort(key=lambda row: str(row["item_id"]))
    assert_blind(packet_items)
    assert_blank_templates(response_rows)
    assert_blank_templates(response_json_items)

    packet_bytes = jsonl_bytes(packet_items)
    csv_columns = COMMON_COLUMNS + LAYER_COLUMNS[layer]
    response_csv_bytes = csv_bytes(response_rows, csv_columns)
    response_template = {
        **{
            key: (value if value != "" else None)
            for key, value in template_metadata.items()
        },
        "packet_hash": None,
        "responses": response_json_items,
    }

    output_dir = safe_output_path(case_root, f"quality/human-reliability/packets/{sample_id}-{sample_version}-{layer}")
    packet_path = output_dir / f"{layer}-packet.jsonl"
    csv_path = output_dir / f"{layer}-response-template.csv"
    json_path = output_dir / f"{layer}-response-template.json"
    required_contracts = {
        root / "schemas" / "human-reliability" / "sample-manifest-schema.json",
        root / "schemas" / "human-reliability" / "packet-item-schema.json",
        root / "schemas" / "human-reliability" / "packet-manifest-schema.json",
        root / "schemas" / "human-reliability" / "submission-schema.json",
        root / "schemas" / "human-reliability" / "submission-csv-contract.json",
        root / "docs" / "reliability" / "human-coder-training-guide.md",
        root / "docs" / "reliability" / "human-reliability-packets.md",
    }
    source_paths.update(path for path in required_contracts if path.is_file())

    def logical_source(path: Path) -> str:
        if path == sample_path:
            return "coordinator://sample-manifest"
        relative = relative_path(root, path)
        if "/corpus/annotated/" in f"/{relative}":
            return f"coordinator://accepted-annotation/{path.stem}"
        if "/corpus/mipvu/" in f"/{relative}":
            return f"source://mipvu/{path.stem}"
        if "/corpus/segmented/" in f"/{relative}":
            return f"source://segmented/{path.stem}"
        return f"contract://{relative}"

    source_entries = [
        {"id": path.stem, "path": logical_source(path), "hash": hash_file(path)}
        for path in sorted(source_paths, key=lambda p: logical_source(p))
    ]
    generator_path = root / GENERATOR_PATH
    if not generator_path.is_file():
        generator_path = Path(__file__)
    manifest_without_hash = {
        "schema_version": "1.0.0",
        "packet_id": packet_id,
        "case_id": case_id,
        "sample_id": sample_id,
        "sample_version": sample_version,
        "sample_hash": actual_sample_hash,
        "source_language": source_language,
        "task_layer": layer,
        "codebook_version": str(frame.get("codebook_version") or ""),
        "rights_constraints": rights_constraints,
        "generator": {
            "script": GENERATOR_PATH,
            "version": GENERATOR_VERSION,
            "script_hash": hash_file(generator_path),
            "code_revision": revision or code_revision(root),
        },
        "selection_summary": {
            "item_count": len(packet_items),
            "sentence_count": len({item["sentence_id"] for item in packet_items}),
            "lexical_unit_count": sum(len(item["lexical_units"]) for item in packet_items),
        },
        "source_inputs": source_entries,
        "payloads": [
            {"id": f"{packet_id}-packet", "path": relative_path(case_root, packet_path), "hash": sha256_bytes(packet_bytes), "media_type": "application/x-ndjson"},
            {"id": f"{packet_id}-csv-template", "path": relative_path(case_root, csv_path), "hash": sha256_bytes(response_csv_bytes), "media_type": "text/csv"},
        ],
    }
    response_json_bytes = json.dumps(response_template, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    manifest_without_hash["payloads"].append(
        {"id": f"{packet_id}-json-template", "path": relative_path(case_root, json_path), "hash": sha256_bytes(response_json_bytes), "media_type": "application/json"}
    )
    packet_hash = sha256_bytes(canonical_json_bytes(manifest_without_hash))
    packet_manifest = {**manifest_without_hash, "packet_hash": packet_hash}
    manifest_bytes = json.dumps(packet_manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"

    output_dir.mkdir(parents=True, exist_ok=True)
    for path, data in ((packet_path, packet_bytes), (csv_path, response_csv_bytes), (json_path, response_json_bytes), (output_dir / "packet-manifest.json", manifest_bytes)):
        write_if_changed(path, data)
    return packet_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument("--sample", type=Path)
    parser.add_argument("--code-revision")
    args = parser.parse_args()
    try:
        manifest = generate_packets(ROOT, args.case_id, sample_path=args.sample, revision=args.code_revision)
    except (PacketGenerationError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
    print(f"{args.case_id}: wrote human packet `{manifest['packet_id']}` ({manifest['packet_hash']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
