#!/usr/bin/env python3
"""Generate deterministic blind packets from an approved reliability sample."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from scripts.model_reliability.boundaries import safe_output_path
except ModuleNotFoundError:
    try:
        from model_reliability.boundaries import safe_output_path
    except ModuleNotFoundError:
        from boundaries import safe_output_path  # type: ignore

ROOT = Path(__file__).resolve().parents[2]
GENERATOR_VERSION = "1.0.0"
GENERATOR_PATH = "scripts/model_reliability/generate_packets.py"
TASK_LAYERS = ("identification", "cmt", "interpretation")
PAYLOAD_FILENAMES = {
    "identification": "identification-packet.jsonl",
    "cmt": "cmt-packet.jsonl",
    "interpretation": "interpretive-packet.jsonl",
}
PROMPT_FILENAMES = {
    "identification": "identification-prompt.md",
    "cmt": "cmt-prompt.md",
    "interpretation": "interpretation-prompt.md",
}
PROHIBITED_PACKET_KEYS = frozenset(
    {
        "accepted_decision",
        "adjudicated_decision",
        "ambiguity_flag",
        "cmt",
        "confidence",
        "decision_type",
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


class PacketGenerationError(ValueError):
    """Raised when an approved sample cannot produce a valid blind packet."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PacketGenerationError(f"required input not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PacketGenerationError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PacketGenerationError(f"expected an object in {path}")
    return data


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def hash_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json_bytes(data: Any) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def jsonl_bytes(items: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(item) + b"\n" for item in items)


def relative_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise PacketGenerationError(f"input path escapes repository root: {path}") from exc


def code_revision(root: Path) -> str:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", GENERATOR_PATH],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    revision = result.stdout.strip()
    if not revision:
        raise PacketGenerationError(f"generator has no committed revision: {GENERATOR_PATH}")
    return revision


def _iter_sentences(segmented: Mapping[str, Any]) -> Iterable[dict[str, Any]]:
    for section in segmented.get("sections", []) or []:
        for paragraph in section.get("paragraphs", []) or []:
            for sentence in paragraph.get("sentences", []) or []:
                if isinstance(sentence, dict):
                    yield sentence


def _iter_annotations(annotated: Mapping[str, Any]) -> Iterable[dict[str, Any]]:
    for item in annotated.get("instances", []) or []:
        if isinstance(item, dict):
            yield item


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def assert_blind(items: Iterable[Mapping[str, Any]]) -> None:
    for item in items:
        leaked = sorted(PROHIBITED_PACKET_KEYS.intersection(_walk_keys(item)))
        if leaked:
            raise PacketGenerationError(
                f"packet item {item.get('item_id', '<unknown>')} contains prohibited key(s): "
                + ", ".join(leaked)
            )


def _lexical_unit(unit: Mapping[str, Any], span_id: str) -> dict[str, Any]:
    unit_id = str(unit.get("mipvu_id") or "")
    source_text = str(unit.get("lexical_unit") or "")
    start = unit.get("sentence_char_offset_start", unit.get("char_offset_start"))
    end = unit.get("sentence_char_offset_end", unit.get("char_offset_end"))
    if not unit_id or not source_text or not isinstance(start, int) or not isinstance(end, int) or end <= start:
        raise PacketGenerationError(f"invalid lexical-unit source fields for `{unit_id or '<unknown>'}`")
    result: dict[str, Any] = {
        "lexical_unit_id": unit_id,
        "span_id": span_id,
        "source_text": source_text,
        "char_offset_start": start,
        "char_offset_end": end,
    }
    gloss = unit.get("gloss_en")
    if isinstance(gloss, str) and gloss:
        result["gloss_en"] = gloss
    return result


def _source_risk_flags(document: Mapping[str, Any]) -> list[str]:
    flags = document.get("risk_flags", [])
    return sorted({str(flag) for flag in flags if str(flag)}) if isinstance(flags, list) else []


def _base_item(
    *,
    packet_id: str,
    layer: str,
    source_id: str,
    case_id: str,
    document_id: str,
    sentence: Mapping[str, Any],
    span_ids: list[str],
    source_language: str,
    lexical_units: list[dict[str, Any]],
    risk_flags: list[str],
) -> dict[str, Any]:
    sentence_id = str(sentence.get("sentence_id") or "")
    sentence_text = str(sentence.get("text") or "")
    if not sentence_id or not sentence_text:
        raise PacketGenerationError(f"missing source text for sentence `{sentence_id or '<unknown>'}`")
    item: dict[str, Any] = {
        "item_id": f"{packet_id}:{layer}:{source_id}",
        "task_layer": layer,
        "case_id": case_id,
        "document_id": document_id,
        "sentence_id": sentence_id,
        "span_ids": span_ids,
        "source_language": source_language,
        "sentence_source_text": sentence_text,
        "lexical_units": lexical_units,
        "source_risk_flags": risk_flags,
    }
    sentence_gloss = sentence.get("gloss_en")
    if isinstance(sentence_gloss, str) and sentence_gloss:
        item["sentence_gloss_en"] = sentence_gloss
    return item


def _write_bytes_if_changed(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == data:
        return
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
    sample_path = sample_path or (
        case_root / "quality" / "model-reliability" / "sample" / "sample-manifest.json"
    )
    sample_path = sample_path.resolve()
    sample = read_json(sample_path)
    if sample.get("status") != "approved":
        raise PacketGenerationError("sample status must be `approved`")
    if sample.get("case_id") != case_id:
        raise PacketGenerationError(f"sample case_id must be `{case_id}`")
    if set(sample.get("task_layers", [])) != set(TASK_LAYERS):
        raise PacketGenerationError("sample must enable identification, cmt, and interpretation layers")

    packet_id = str(sample.get("packet_id") or "")
    sample_id = str(sample.get("sample_id") or "")
    sample_version = str(sample.get("sample_version") or "")
    source_language = str(sample.get("source_language") or "")
    sentence_ids = {str(value) for value in sample.get("sentence_ids", []) if value}
    if not packet_id or not sample_id or not sample_version or not source_language or not sentence_ids:
        raise PacketGenerationError("sample identity, language, and sentence_ids are required")

    manifest_path = case_root / "metadata" / "document-manifest.json"
    document_manifest = read_json(manifest_path)
    documents = {
        str(document.get("document_id") or document.get("id") or ""): document
        for document in document_manifest.get("documents", [])
        if isinstance(document, dict)
    }
    selected_sentences: dict[str, tuple[str, dict[str, Any]]] = {}
    units_by_sentence: dict[str, list[dict[str, Any]]] = {}
    annotations_by_sentence: dict[str, list[dict[str, Any]]] = {}
    source_paths: set[Path] = {sample_path, manifest_path}

    for document_id, document in sorted(documents.items()):
        if not document_id:
            continue
        segmented_path = case_root / "corpus" / "segmented" / f"{document_id}.json"
        segmented = read_json(segmented_path)
        selected_in_document = [
            sentence
            for sentence in _iter_sentences(segmented)
            if str(sentence.get("sentence_id") or "") in sentence_ids
        ]
        if not selected_in_document:
            continue

        mipvu_path = case_root / "corpus" / "mipvu" / f"{document_id}_mipvu.json"
        annotated_path = case_root / "corpus" / "annotated" / f"{document_id}_annotated.json"
        mipvu = read_json(mipvu_path)
        annotated = read_json(annotated_path) if annotated_path.exists() else {"instances": []}
        source_paths.update({segmented_path, mipvu_path})
        if annotated_path.exists():
            source_paths.add(annotated_path)

        document_language = str(
            document.get("source_language") or segmented.get("meta", {}).get("source_language") or ""
        )
        if document_language != source_language:
            raise PacketGenerationError(
                f"document `{document_id}` language `{document_language}` does not match sample `{source_language}`"
            )
        for sentence in selected_in_document:
            sentence_id = str(sentence.get("sentence_id") or "")
            selected_sentences[sentence_id] = (document_id, sentence)
        for unit in mipvu.get("lexical_units", []) or []:
            if isinstance(unit, dict) and str(unit.get("sentence_id") or "") in sentence_ids:
                units_by_sentence.setdefault(str(unit["sentence_id"]), []).append(unit)
        for annotation in _iter_annotations(annotated):
            sentence_id = str(annotation.get("sentence_id") or "")
            if sentence_id in sentence_ids:
                annotations_by_sentence.setdefault(sentence_id, []).append(annotation)

    unknown_sentences = sorted(sentence_ids - set(selected_sentences))
    if unknown_sentences:
        raise PacketGenerationError("unknown sampled sentence ID(s): " + ", ".join(unknown_sentences))

    identification_items: list[dict[str, Any]] = []
    cmt_items: list[dict[str, Any]] = []
    interpretation_items: list[dict[str, Any]] = []
    all_selected_units: list[dict[str, Any]] = []
    claim_relevant_ids: set[str] = set()

    for sentence_id in sorted(sentence_ids):
        document_id, sentence = selected_sentences[sentence_id]
        document = documents[document_id]
        units = sorted(
            units_by_sentence.get(sentence_id, []),
            key=lambda unit: (int(unit.get("sentence_unit_ordinal") or 0), str(unit.get("mipvu_id") or "")),
        )
        if not units:
            raise PacketGenerationError(f"sampled sentence `{sentence_id}` has no lexical units")
        unit_ids_in_order = [str(unit.get("mipvu_id") or "") for unit in units]
        if len(set(unit_ids_in_order)) != len(unit_ids_in_order):
            raise PacketGenerationError(f"sampled sentence `{sentence_id}` contains duplicate lexical-unit IDs")
        wrong_languages = sorted(
            {
                str(unit.get("language") or "")
                for unit in units
                if str(unit.get("language") or "") != source_language
            }
        )
        if wrong_languages:
            raise PacketGenerationError(
                f"sampled sentence `{sentence_id}` contains lexical-unit language(s) outside `{source_language}`: "
                + ", ".join(wrong_languages)
            )
        all_selected_units.extend(units)
        unit_lookup = {str(unit.get("mipvu_id") or ""): unit for unit in units}
        unit_ids = list(unit_lookup)
        identification_items.append(
            _base_item(
                packet_id=packet_id,
                layer="identification",
                source_id=sentence_id,
                case_id=case_id,
                document_id=document_id,
                sentence=sentence,
                span_ids=unit_ids,
                source_language=source_language,
                lexical_units=[_lexical_unit(unit, str(unit["mipvu_id"])) for unit in units],
                risk_flags=_source_risk_flags(document),
            )
        )

        for annotation in sorted(
            annotations_by_sentence.get(sentence_id, []), key=lambda item: str(item.get("instance_id") or "")
        ):
            annotation_id = str(annotation.get("instance_id") or "")
            mipvu_ids = [str(value) for value in annotation.get("mipvu_ids", []) if value]
            if not annotation_id or not mipvu_ids:
                raise PacketGenerationError(f"field item in `{sentence_id}` lacks stable annotation/MIPVU IDs")
            if annotation_id in claim_relevant_ids:
                raise PacketGenerationError(f"duplicate annotation ID `{annotation_id}`")
            missing_units = sorted(set(mipvu_ids) - set(unit_lookup))
            if missing_units:
                raise PacketGenerationError(
                    f"annotation `{annotation_id}` references lexical units outside its sampled sentence: "
                    + ", ".join(missing_units)
                )
            claim_relevant_ids.add(annotation_id)
            lexical_units = [_lexical_unit(unit_lookup[unit_id], annotation_id) for unit_id in mipvu_ids]
            common = {
                "packet_id": packet_id,
                "source_id": annotation_id,
                "case_id": case_id,
                "document_id": document_id,
                "sentence": sentence,
                "span_ids": [annotation_id],
                "source_language": source_language,
                "lexical_units": lexical_units,
                "risk_flags": _source_risk_flags(document),
            }
            cmt_items.append(_base_item(layer="cmt", **common))
            interpretation_items.append(_base_item(layer="interpretation", **common))

    payload_items = {
        "identification": identification_items,
        "cmt": cmt_items,
        "interpretation": interpretation_items,
    }
    if any(not items for items in payload_items.values()):
        missing = [layer for layer, items in payload_items.items() if not items]
        raise PacketGenerationError("sample produced no packet items for layer(s): " + ", ".join(missing))
    for items in payload_items.values():
        assert_blind(items)

    negative_controls = sum(
        1 for unit in all_selected_units if unit.get("decision_type") == "non_metaphor"
    )
    ambiguous_items = sum(
        1
        for unit in all_selected_units
        if unit.get("decision_type") == "uncertain"
        or (isinstance(unit.get("confidence"), (int, float)) and unit["confidence"] < 0.8)
        or unit.get("semantic_shift_risk") == "high"
    )
    if not negative_controls or not ambiguous_items or not claim_relevant_ids:
        raise PacketGenerationError(
            "approved sample must contain negative controls, ambiguous items, and claim-relevant items"
        )

    output_dir = safe_output_path(case_root, "quality/model-reliability/packets")
    payload_entries: list[dict[str, Any]] = []
    output_bytes: dict[Path, bytes] = {}
    for layer in TASK_LAYERS:
        filename = PAYLOAD_FILENAMES[layer]
        payload_path = safe_output_path(case_root, f"quality/model-reliability/packets/{filename}")
        data = jsonl_bytes(payload_items[layer])
        output_bytes[payload_path] = data
        payload_entries.append(
            {
                "id": f"{packet_id}-{layer}",
                "path": relative_path(case_root, payload_path),
                "hash": sha256_bytes(data),
                "task_layer": layer,
                "item_count": len(payload_items[layer]),
            }
        )

    prompt_entries: list[dict[str, Any]] = []
    prompts = sample.get("prompts", {})
    for layer in TASK_LAYERS:
        prompt = prompts.get(layer, {}) if isinstance(prompts, dict) else {}
        prompt_id = str(prompt.get("prompt_id") or "") if isinstance(prompt, dict) else ""
        prompt_source = root / str(prompt.get("path") or "") if isinstance(prompt, dict) else root
        if not prompt_id or not prompt_source.is_file():
            raise PacketGenerationError(f"missing configured prompt for `{layer}`")
        source_paths.add(prompt_source)
        prompt_data = prompt_source.read_bytes()
        prompt_output = safe_output_path(
            case_root, f"quality/model-reliability/packets/{PROMPT_FILENAMES[layer]}"
        )
        output_bytes[prompt_output] = prompt_data
        prompt_entries.append(
            {
                "id": prompt_id,
                "path": relative_path(case_root, prompt_output),
                "hash": sha256_bytes(prompt_data),
                "task_layer": layer,
            }
        )

    configured_source_sample = root / str(sample.get("source_sample") or "")
    if not configured_source_sample.is_file():
        raise PacketGenerationError(f"configured source sample not found: {configured_source_sample}")
    source_paths.add(configured_source_sample)
    source_entries = [
        {
            "id": path.stem,
            "path": relative_path(root, path),
            "hash": hash_file(path),
        }
        for path in sorted(source_paths, key=lambda item: relative_path(root, item))
    ]

    script_path = root / GENERATOR_PATH
    manifest_without_hash = {
        "schema_version": "1.0.0",
        "packet_id": packet_id,
        "case_id": case_id,
        "sample_id": sample_id,
        "sample_version": sample_version,
        "source_language": source_language,
        "rights_constraints": sorted({str(value) for value in sample.get("rights_constraints", [])}),
        "code_revision": revision or code_revision(root),
        "generator": {
            "script": GENERATOR_PATH,
            "version": GENERATOR_VERSION,
            "script_hash": hash_file(script_path),
        },
        "selection_summary": {
            "sentences": len(sentence_ids),
            "lexical_units": len(all_selected_units),
            "field_agreement_items": len(claim_relevant_ids),
        },
        "prompts": prompt_entries,
        "source_inputs": source_entries,
        "payloads": payload_entries,
    }
    manifest = {
        **manifest_without_hash,
        "packet_hash": sha256_bytes(canonical_json_bytes(manifest_without_hash)),
    }
    manifest_path_out = safe_output_path(
        case_root, "quality/model-reliability/packets/packet-manifest.json"
    )
    output_bytes[manifest_path_out] = json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, indent=2
    ).encode("utf-8") + b"\n"

    output_dir.mkdir(parents=True, exist_ok=True)
    for path, data in output_bytes.items():
        _write_bytes_if_changed(path, data)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument("--sample", type=Path)
    parser.add_argument("--code-revision")
    args = parser.parse_args()
    try:
        manifest = generate_packets(
            ROOT,
            args.case_id,
            sample_path=args.sample,
            revision=args.code_revision,
        )
    except (PacketGenerationError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
    print(
        f"{args.case_id}: wrote deterministic packet `{manifest['packet_id']}` "
        f"({manifest['packet_hash']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
