from __future__ import annotations

import csv
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.human_reliability.generate_packets import (
    PROHIBITED_PACKET_KEYS,
    PacketGenerationError,
    canonical_json_bytes,
    generate_packets,
    sample_hash,
    sha256_bytes,
)


SOURCE_ROOT = Path(__file__).resolve().parents[1]
MODEL_FIXTURE = SOURCE_ROOT / "test" / "fixtures" / "model-reliability" / "repository"
SENTENCE_ID = "demo-doc-001_s01_p01_s01"
UNIT_ID = f"{SENTENCE_ID}_lu001"
ANNOTATION_ID = "demo-ann-001"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sample_manifest(layer: str, source_span_id: str | None) -> dict:
    sample = {
        "schema_version": "1.0.0",
        "strategy_version": "1.0.0",
        "sample_id": f"demo-human-{layer}",
        "sample_version": "1.0.0",
        "status": "approved",
        "case_id": "demo",
        "source_language": "fr",
        "task_layer": layer,
        "frame": {
            "frame_id": "demo-frame-v1",
            "frame_sha256": "0" * 64,
            "codebook_version": "demo-codebook-v1",
            "source_artifact_versions": ["demo-v1"],
            "eligible_item_count": 1,
            "eligible_document_count": 1,
            "phases": ["invented-phase"],
            "genres_or_registers": ["invented-address"],
            "rights_constraints": ["synthetic-test-only"],
            "frozen_at": "2026-06-21T00:00:00Z",
        },
        "selection": {
            "method": "two_stage_stratified_seeded",
            "seed": "demo-seed",
            "primary_unit": "complete_segmented_sentence" if layer == "identification" else "source_span",
            "target_item_count": 1,
            "target_cluster_count": 1,
            "quotas": {
                "reference_positive_or_uncertain_minimum": 0,
                "ordinary_negative_minimum": 1,
                "ambiguous_target_fraction": [0, 1],
                "provenance_risk_target_fraction": [0, 1],
                "high_impact_maximum_fraction": 1,
                "document_maximum_fraction": 1,
            },
            "small_frame_policy": "census_and_scope_claim",
            "adaptive_expansion_policy": "predeclared_new_version_only",
        },
        "items": [
            {
                "item_id": f"demo-item-{layer}",
                "document_id": "demo-doc-001",
                "sentence_id": SENTENCE_ID,
                "source_span_id": source_span_id,
                "phase": "invented-phase",
                "genre_or_register": "invented-address",
                "design_roles": ["negative_control"],
                "provenance_risks": [],
                "claim_impact": "ordinary",
                "context_scope": "complete_sentence",
                "legacy_continuity": False,
            }
        ],
        "exclusions": [],
        "execution": {
            "status": "approved_to_execute",
            "qualified_primary_coders_required": 2,
            "coder_access_constraints": [],
            "non_execution_reason": None,
        },
        "approval": {
            "approved_by": "coordinator-demo",
            "approved_at": "2026-06-21T00:00:00Z",
            "manifest_sha256": None,
        },
    }
    sample["approval"]["manifest_sha256"] = sample_hash(sample)
    return sample


def fixture_root(base: Path, layer: str, source_span_id: str | None) -> tuple[Path, Path]:
    root = base / "repo"
    shutil.copytree(MODEL_FIXTURE, root)
    human_root = root / "cases" / "demo" / "quality" / "human-reliability"
    sample_path = human_root / "samples" / "sample-manifest.json"
    write_json(sample_path, sample_manifest(layer, source_span_id))
    return root, sample_path


def packet_dir(root: Path, layer: str) -> Path:
    return (
        root / "cases" / "demo" / "quality" / "human-reliability" / "packets"
        / f"demo-human-{layer}-1.0.0-{layer}"
    )


class HumanReliabilityPacketTest(unittest.TestCase):
    def test_generates_deterministic_identification_packet_and_templates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, sample_path = fixture_root(Path(temp_dir), "identification", None)
            first = generate_packets(root, "demo", sample_path=sample_path, revision="deadbeef")
            output = packet_dir(root, "identification")
            first_bytes = {path.name: path.read_bytes() for path in output.iterdir()}
            second = generate_packets(root, "demo", sample_path=sample_path, revision="deadbeef")
            second_bytes = {path.name: path.read_bytes() for path in output.iterdir()}
            self.assertEqual(first, second)
            self.assertEqual(first_bytes, second_bytes)

            packet_item = json.loads(
                (output / "identification-packet.jsonl").read_text(encoding="utf-8").splitlines()[0]
            )
            self.assertEqual("fr", packet_item["source_language"])
            self.assertEqual(2, len(packet_item["lexical_units"]))
            self.assertFalse(set(packet_item).intersection(PROHIBITED_PACKET_KEYS))
            serialized = json.dumps(packet_item)
            self.assertNotIn("negative_control", serialized)
            self.assertNotIn("mipvu_indirect", serialized)

            rows = list(csv.DictReader(io.StringIO(
                (output / "identification-response-template.csv").read_text(encoding="utf-8")
            )))
            self.assertEqual(2, len(rows))
            self.assertEqual("", rows[0]["decision_type"])
            self.assertEqual("", rows[0]["confidence"])
            json_template = json.loads(
                (output / "identification-response-template.json").read_text(encoding="utf-8")
            )
            self.assertIsNone(json_template["packet_hash"])
            self.assertIsNone(json_template["responses"][0]["response"]["decision_type"])

    def test_generates_field_packet_from_annotation_and_negative_span(self) -> None:
        for layer, span_id, expected_unit in (
            ("cmt", ANNOTATION_ID, f"{SENTENCE_ID}_lu002"),
            ("interpretation", UNIT_ID, UNIT_ID),
        ):
            with self.subTest(layer=layer), tempfile.TemporaryDirectory() as temp_dir:
                root, sample_path = fixture_root(Path(temp_dir), layer, span_id)
                generate_packets(root, "demo", sample_path=sample_path, revision="deadbeef")
                item = json.loads(
                    (packet_dir(root, layer) / f"{layer}-packet.jsonl")
                    .read_text(encoding="utf-8").splitlines()[0]
                )
                self.assertEqual(span_id, item["source_span_id"])
                self.assertEqual([expected_unit], [unit["lexical_unit_id"] for unit in item["lexical_units"]])
                self.assertNotIn("cmt", item)
                self.assertNotIn("koenigsberg", item)

    def test_generated_packet_and_manifest_satisfy_schemas(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, sample_path = fixture_root(Path(temp_dir), "cmt", ANNOTATION_ID)
            manifest = generate_packets(root, "demo", sample_path=sample_path, revision="deadbeef")
            manifest_schema = json.loads(
                (SOURCE_ROOT / "schemas" / "human-reliability" / "packet-manifest-schema.json").read_text()
            )
            item_schema = json.loads(
                (SOURCE_ROOT / "schemas" / "human-reliability" / "packet-item-schema.json").read_text()
            )
            Draft202012Validator.check_schema(manifest_schema)
            Draft202012Validator.check_schema(item_schema)
            self.assertEqual([], list(Draft202012Validator(manifest_schema).iter_errors(manifest)))
            item = json.loads(
                (packet_dir(root, "cmt") / "cmt-packet.jsonl").read_text().splitlines()[0]
            )
            self.assertEqual([], list(Draft202012Validator(item_schema).iter_errors(item)))

    def test_manifest_uses_logical_sources_and_hashes_all_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, sample_path = fixture_root(Path(temp_dir), "cmt", ANNOTATION_ID)
            manifest = generate_packets(root, "demo", sample_path=sample_path, revision="deadbeef")
            paths = {entry["path"] for entry in manifest["source_inputs"]}
            self.assertIn("coordinator://sample-manifest", paths)
            self.assertTrue(any(path.startswith("coordinator://accepted-annotation/") for path in paths))
            self.assertFalse(any("quality/human-reliability/samples" in path for path in paths))
            self.assertEqual(3, len(manifest["payloads"]))
            for payload in manifest["payloads"]:
                path = root / "cases" / "demo" / payload["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(payload["hash"], sha256_bytes(path.read_bytes()))
            unsigned_manifest = {key: value for key, value in manifest.items() if key != "packet_hash"}
            self.assertEqual(
                manifest["packet_hash"],
                sha256_bytes(canonical_json_bytes(unsigned_manifest)),
            )

    def test_rejects_tampered_approval_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, sample_path = fixture_root(Path(temp_dir), "identification", None)
            sample = json.loads(sample_path.read_text())
            sample["selection"]["seed"] = "changed-after-approval"
            write_json(sample_path, sample)
            with self.assertRaisesRegex(PacketGenerationError, "manifest_sha256"):
                generate_packets(root, "demo", sample_path=sample_path, revision="deadbeef")
            self.assertFalse((root / "cases" / "demo" / "quality" / "human-reliability" / "packets").exists())

    def test_rejects_span_bound_to_another_sentence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, sample_path = fixture_root(Path(temp_dir), "cmt", UNIT_ID)
            mipvu_path = root / "cases" / "demo" / "corpus" / "mipvu" / "demo-doc-001_mipvu.json"
            mipvu = json.loads(mipvu_path.read_text())
            mipvu["lexical_units"][0]["sentence_id"] = "different-sentence"
            write_json(mipvu_path, mipvu)
            with self.assertRaisesRegex(PacketGenerationError, "belongs to another document or sentence"):
                generate_packets(root, "demo", sample_path=sample_path, revision="deadbeef")


if __name__ == "__main__":
    unittest.main()
