from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.model_reliability.generate_packets import (
    PROHIBITED_PACKET_KEYS,
    PacketGenerationError,
    generate_packets,
)

SOURCE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = SOURCE_ROOT / "test" / "fixtures" / "model-reliability"
FIXTURE_REPOSITORY = FIXTURE_ROOT / "repository"


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fixture_root(base: Path) -> Path:
    root = base / "repo"
    shutil.copytree(FIXTURE_REPOSITORY, root)
    packets = root / "cases" / "demo" / "quality" / "model-reliability" / "packets"
    shutil.rmtree(packets)
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
            self.assertEqual(identification["sentence_gloss_en"], "The city carries hope.")
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

    def test_packet_hash_ignores_generated_at_source_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = fixture_root(Path(temp_dir))
            manifest_before = generate_packets(root, "demo", revision="deadbeef")
            segmented_path = (
                root
                / "cases"
                / "demo"
                / "corpus"
                / "segmented"
                / "demo-doc-001.json"
            )
            segmented = json.loads(segmented_path.read_text(encoding="utf-8"))
            segmented.setdefault("meta", {})["generated_at"] = "2099-01-01T00:00:00"
            write_json(segmented_path, segmented)

            manifest_after = generate_packets(root, "demo", revision="deadbeef")

            self.assertEqual(manifest_before["packet_hash"], manifest_after["packet_hash"])
            before_sources = {
                entry["path"]: entry["hash"] for entry in manifest_before["source_inputs"]
            }
            after_sources = {
                entry["path"]: entry["hash"] for entry in manifest_after["source_inputs"]
            }
            self.assertEqual(before_sources, after_sources)

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
