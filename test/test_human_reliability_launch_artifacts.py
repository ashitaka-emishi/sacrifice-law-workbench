from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.human_reliability.generate_packets import (
    PROHIBITED_PACKET_KEYS,
    canonical_json_bytes,
    sample_hash,
    sha256_bytes,
)
from scripts.human_reliability.ingest_submission import cohort_hash
from scripts.human_reliability.status import evaluate_case


ROOT = Path(__file__).resolve().parents[1]
HUMAN_ROOT = ROOT / "cases" / "lincoln" / "quality" / "human-reliability"
SAMPLE_PATH = HUMAN_ROOT / "samples" / "sample-manifest.json"
COHORT_PATH = HUMAN_ROOT / "cohorts" / "lincoln-en-cmt-launch-1.0.0.json"
PACKET_ROOT = HUMAN_ROOT / "packets" / "lincoln-human-cmt-launch-1.0.0-cmt"
PACKET_MANIFEST_PATH = PACKET_ROOT / "packet-manifest.json"
PACKET_PAYLOAD_PATH = PACKET_ROOT / "cmt-packet.jsonl"


class HumanReliabilityLaunchArtifactsTest(unittest.TestCase):
    def test_launch_manifests_validate_and_hashes_are_current(self) -> None:
        sample = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
        cohort = json.loads(COHORT_PATH.read_text(encoding="utf-8"))
        packet = json.loads(PACKET_MANIFEST_PATH.read_text(encoding="utf-8"))

        for value, schema_name in (
            (sample, "sample-manifest-schema.json"),
            (cohort, "cohort-manifest-schema.json"),
            (packet, "packet-manifest-schema.json"),
        ):
            schema = json.loads(
                (ROOT / "schemas" / "human-reliability" / schema_name).read_text(
                    encoding="utf-8"
                )
            )
            Draft202012Validator(schema).validate(value)

        self.assertEqual(sample["approval"]["manifest_sha256"], sample_hash(sample))
        self.assertEqual(cohort["approval"]["manifest_sha256"], cohort_hash(cohort))
        unsigned_packet = dict(packet)
        expected_packet_hash = unsigned_packet.pop("packet_hash")
        self.assertEqual(expected_packet_hash, sha256_bytes(canonical_json_bytes(unsigned_packet)))
        for payload in packet["payloads"]:
            payload_path = ROOT / "cases" / packet["case_id"] / payload["path"]
            self.assertTrue(payload_path.is_file())
            self.assertEqual(payload["hash"], sha256_bytes(payload_path.read_bytes()))
        self.assertEqual(cohort["packet_id"], packet["packet_id"])
        self.assertEqual(cohort["sample_id"], packet["sample_id"])
        self.assertEqual(cohort["sample_version"], packet["sample_version"])
        self.assertEqual(cohort["task_layer"], "cmt")
        self.assertEqual(cohort["required_primary_coders"], 2)
        self.assertFalse(cohort["ai_assistance_allowed"])

    def test_launch_packet_is_blind_and_status_is_designed_not_complete(self) -> None:
        payload_text = PACKET_PAYLOAD_PATH.read_text(encoding="utf-8")
        forbidden_strings = (
            "accepted_decision",
            "adjudicated_decision",
            "support_score",
            "model_output",
            "issue147-",
            "source_domain_primary",
            "target_domain",
            "conceptual_metaphor",
            "lincoln-01-body-organism",
        )
        for forbidden in forbidden_strings:
            self.assertNotIn(forbidden, payload_text)

        rows = [json.loads(line) for line in payload_text.splitlines() if line.strip()]
        self.assertEqual(7, len(rows))
        for row in rows:
            self.assertEqual(row["task_layer"], "cmt")
            self.assertEqual(row["source_language"], "en")
            self.assertFalse(set(row).intersection(PROHIBITED_PACKET_KEYS))
            self.assertIn("sentence_source_text", row)
            self.assertIn("lexical_units", row)

        status = evaluate_case(ROOT, "lincoln")
        self.assertTrue(status["valid"])
        self.assertEqual("designed", status["state"])
        self.assertEqual(1, status["counts"]["cohorts"])
        self.assertEqual(0, status["counts"]["submissions"])
        self.assertEqual(0, status["counts"]["valid_runs"])
        self.assertEqual("designed", status["cohorts"][0]["state"])
        self.assertEqual("absent", status["cohorts"][0]["ingestion_state"])


if __name__ == "__main__":
    unittest.main()
