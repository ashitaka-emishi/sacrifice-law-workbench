from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.human_reliability.preflight_submission import (
    forbidden_field_errors,
    preflight_submission,
)
from scripts.human_reliability.ingest_submission import (
    parse_json_submission,
)
from test.test_human_reliability_ingestion import (
    ingestion_root,
    valid_submission,
    write_identification_csv,
)
from test.test_human_reliability_packets import write_json
from scripts.human_reliability.submission_contract import load_csv_contract
from scripts.human_reliability.ingest_submission import parse_csv_submission


def human_tree_snapshot(root: Path) -> dict[str, bytes]:
    human_root = root / "cases" / "demo" / "quality" / "human-reliability"
    return {
        path.relative_to(human_root).as_posix(): path.read_bytes()
        for path in human_root.rglob("*")
        if path.is_file()
    }


class HumanReliabilityPreflightTest(unittest.TestCase):
    def test_valid_json_preflight_has_no_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, cohort_path = ingestion_root(Path(temp_dir))
            source = Path(temp_dir) / "submission.json"
            write_json(source, valid_submission(root))
            before = human_tree_snapshot(root)

            report = preflight_submission(
                root,
                "demo",
                cohort_path,
                parse_json_submission(source),
            )

            self.assertEqual("valid", report["status"])
            self.assertEqual([], report["errors"])
            self.assertFalse(report["writes_artifacts"])
            self.assertEqual(before, human_tree_snapshot(root))
            self.assertFalse(
                (root / "cases" / "demo" / "quality" / "human-reliability" / "submissions").exists()
            )

    def test_wrong_packet_hash_wrong_cohort_and_missing_declarations_are_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, cohort_path = ingestion_root(Path(temp_dir))
            submission = valid_submission(root)
            submission["packet_hash"] = "sha256:" + "0" * 64
            submission["cohort_id"] = "wrong-cohort"
            submission["qualification_attested"] = False
            submission["source_language_qualified"] = False
            submission["independence_attested"] = False
            submission["training_completed_at"] = ""
            submission["calibration_completed_at"] = ""
            source = Path(temp_dir) / "bad.json"
            write_json(source, submission)

            report = preflight_submission(root, "demo", cohort_path, parse_json_submission(source))

            self.assertEqual("invalid", report["status"])
            joined = "\n".join(report["errors"])
            self.assertIn("$.packet_hash: does not match", joined)
            self.assertIn("$.cohort_id: does not match", joined)
            self.assertIn("$.qualification_attested: True was expected", joined)
            self.assertIn("$.source_language_qualified: True was expected", joined)
            self.assertIn("$.independence_attested: True was expected", joined)
            self.assertIn("$.training_completed_at: required declaration timestamp is missing", joined)
            self.assertIn("$.calibration_completed_at: required declaration timestamp is missing", joined)

    def test_malformed_controlled_value_and_leakage_fields_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, cohort_path = ingestion_root(Path(temp_dir))
            submission = valid_submission(root)
            response = submission["responses"][0]
            response["cmt_response"]["source_domain_primary"] = "invented-domain"
            response["accepted_decision"] = "mipvu_indirect"
            submission["model_output"] = {"verdict": "leaked"}
            source = Path(temp_dir) / "leaky.json"
            write_json(source, submission)

            report = preflight_submission(root, "demo", cohort_path, parse_json_submission(source))

            self.assertEqual("invalid", report["status"])
            joined = "\n".join(report["errors"])
            self.assertIn("unknown controlled value `invented-domain`", joined)
            self.assertIn("$.responses[0].accepted_decision: forbidden leakage/internal field", joined)
            self.assertIn("$.model_output: forbidden leakage/internal field", joined)

    def test_valid_csv_preflight_uses_existing_contract_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, cohort_path = ingestion_root(Path(temp_dir), "identification")
            source = Path(temp_dir) / "submission.csv"
            write_identification_csv(source, valid_submission(root, layer="identification"))
            before = human_tree_snapshot(root)

            report = preflight_submission(
                root,
                "demo",
                cohort_path,
                parse_csv_submission(source, load_csv_contract()),
            )

            self.assertEqual("valid", report["status"])
            self.assertEqual(2, len(report["raw_rows"]))
            self.assertEqual(before, human_tree_snapshot(root))

    def test_forbidden_field_walker_reports_nested_paths(self) -> None:
        errors = forbidden_field_errors({"responses": [{"adjudicated_decision": "x"}]})
        self.assertEqual(
            ["$.responses[0].adjudicated_decision: forbidden leakage/internal field `adjudicated_decision`"],
            errors,
        )


if __name__ == "__main__":
    unittest.main()
