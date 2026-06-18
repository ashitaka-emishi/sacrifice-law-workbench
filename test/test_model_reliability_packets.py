from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.model_reliability.generate_packets import (
    PROHIBITED_PACKET_KEYS,
    PacketGenerationError,
    generate_packets,
)


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fixture_root(base: Path) -> Path:
    root = base / "repo"
    case = root / "cases" / "demo"
    prompt_dir = root / "config" / "model-reliability" / "prompts"
    for layer in ("identification", "cmt", "interpretation"):
        path = prompt_dir / f"{layer}-v1.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"Blind {layer} instructions.\n", encoding="utf-8")
    script = root / "scripts" / "model_reliability" / "generate_packets.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("# fixture generator identity\n", encoding="utf-8")

    write_json(
        case / "metadata" / "document-manifest.json",
        {
            "documents": [
                {
                    "document_id": "doc-001",
                    "source_language": "fr",
                    "rights_status": "public-domain",
                    "risk_flags": ["transcription-check"],
                }
            ]
        },
    )
    write_json(
        case / "corpus" / "segmented" / "doc-001.json",
        {
            "document_id": "doc-001",
            "meta": {"source_language": "fr"},
            "sections": [
                {
                    "paragraphs": [
                        {
                            "sentences": [
                                {
                                    "sentence_id": "sentence-001",
                                    "text": "Le peuple porte la patrie.",
                                    "gloss_en": "The people carry the homeland.",
                                }
                            ]
                        }
                    ]
                }
            ],
        },
    )
    units = [
        {
            "mipvu_id": "lu-001",
            "sentence_id": "sentence-001",
            "sentence_unit_ordinal": 1,
            "lexical_unit": "peuple",
            "language": "fr",
            "sentence_char_offset_start": 3,
            "sentence_char_offset_end": 9,
            "decision_type": "non_metaphor",
            "review_status": "accepted",
        },
        {
            "mipvu_id": "lu-002",
            "sentence_id": "sentence-001",
            "sentence_unit_ordinal": 2,
            "lexical_unit": "porte",
            "gloss_en": "carries",
            "language": "fr",
            "sentence_char_offset_start": 10,
            "sentence_char_offset_end": 15,
            "decision_type": "mipvu_indirect",
            "confidence": 0.72,
            "semantic_shift_risk": "high",
            "review_status": "accepted",
            "contextual_meaning": "supports",
        },
    ]
    write_json(
        case / "corpus" / "mipvu" / "doc-001_mipvu.json",
        {"case_id": "demo", "document_id": "doc-001", "lexical_units": units},
    )
    write_json(
        case / "corpus" / "annotated" / "doc-001_annotated.json",
        {
            "instances": [
                {
                    "instance_id": "ann-001",
                    "document_id": "doc-001",
                    "sentence_id": "sentence-001",
                    "mipvu_ids": ["lu-002"],
                    "cmt": {"source_domain_primary": "body", "target_domain": "nation"},
                    "koenigsberg": {"obligatory_frame": True},
                    "meta": {"confidence": 0.72, "ambiguity_flag": True},
                }
            ]
        },
    )
    write_json(case / "quality" / "reliability-sample.json", {"case_id": "demo"})
    write_json(
        case / "quality" / "model-reliability" / "sample" / "sample-manifest.json",
        {
            "schema_version": "1.0.0",
            "sample_id": "demo-sample-v1",
            "sample_version": "1.0.0",
            "packet_id": "demo-packet-v1",
            "case_id": "demo",
            "status": "approved",
            "source_language": "fr",
            "source_sample": "cases/demo/quality/reliability-sample.json",
            "sentence_ids": ["sentence-001"],
            "task_layers": ["identification", "cmt", "interpretation"],
            "selection_policy": {
                "identification": "all_lexical_units_in_selected_sentences",
                "ambiguous": "uncertain_or_confidence_below_0.8_or_high_semantic_shift_risk",
                "field_agreement": "annotated_instances_in_selected_sentences",
            },
            "rights_constraints": ["public-domain-source"],
            "prompts": {
                layer: {
                    "prompt_id": f"{layer}-v1",
                    "path": f"config/model-reliability/prompts/{layer}-v1.md",
                }
                for layer in ("identification", "cmt", "interpretation")
            },
        },
    )
    return root


class PacketGenerationTest(unittest.TestCase):
    def test_generates_deterministic_blind_multilingual_packets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = fixture_root(Path(temp_dir))
            first = generate_packets(root, "demo", revision="deadbeef")
            packet_dir = root / "cases" / "demo" / "quality" / "model-reliability" / "packets"
            first_bytes = {path.name: path.read_bytes() for path in packet_dir.iterdir() if path.is_file()}

            second = generate_packets(root, "demo", revision="deadbeef")
            second_bytes = {path.name: path.read_bytes() for path in packet_dir.iterdir() if path.is_file()}

            self.assertEqual(first, second)
            self.assertEqual(first_bytes, second_bytes)
            self.assertEqual(first["selection_summary"]["field_agreement_items"], 1)
            self.assertNotIn("negative_controls", first["selection_summary"])
            self.assertNotIn("ambiguous_items", first["selection_summary"])
            self.assertEqual(
                {entry["task_layer"] for entry in first["prompts"]},
                {"identification", "cmt", "interpretation"},
            )

            identification = json.loads(
                (packet_dir / "identification-packet.jsonl").read_text(encoding="utf-8").splitlines()[0]
            )
            serialized_keys = set(identification)
            serialized_keys.update(identification["lexical_units"][0])
            self.assertFalse(serialized_keys.intersection(PROHIBITED_PACKET_KEYS))
            self.assertEqual(identification["source_language"], "fr")
            self.assertEqual(identification["sentence_gloss_en"], "The people carry the homeland.")
            self.assertEqual(len(identification["lexical_units"]), 2)

    def test_generated_artifacts_satisfy_packet_schemas(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = fixture_root(Path(temp_dir))
            manifest = generate_packets(root, "demo", revision="deadbeef")
            source_root = Path(__file__).resolve().parents[1]
            manifest_schema = json.loads(
                (source_root / "schemas" / "model-reliability" / "packet-manifest-schema.json").read_text()
            )
            item_schema = json.loads(
                (source_root / "schemas" / "model-reliability" / "packet-item-schema.json").read_text()
            )
            Draft202012Validator.check_schema(manifest_schema)
            Draft202012Validator.check_schema(item_schema)
            self.assertEqual(list(Draft202012Validator(manifest_schema).iter_errors(manifest)), [])

            packet_dir = root / "cases" / "demo" / "quality" / "model-reliability" / "packets"
            for payload in packet_dir.glob("*-packet.jsonl"):
                for line in payload.read_text(encoding="utf-8").splitlines():
                    errors = list(Draft202012Validator(item_schema).iter_errors(json.loads(line)))
                    self.assertEqual(errors, [], payload.name)

    def test_rejects_unknown_sentence_before_writing_packets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = fixture_root(Path(temp_dir))
            sample_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "sample"
                / "sample-manifest.json"
            )
            sample = json.loads(sample_path.read_text(encoding="utf-8"))
            sample["sentence_ids"] = ["unknown-sentence"]
            write_json(sample_path, sample)

            with self.assertRaisesRegex(PacketGenerationError, "unknown sampled sentence"):
                generate_packets(root, "demo", revision="deadbeef")

            self.assertFalse(
                (root / "cases" / "demo" / "quality" / "model-reliability" / "packets").exists()
            )


if __name__ == "__main__":
    unittest.main()
