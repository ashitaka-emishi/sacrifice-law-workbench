from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.human_reliability.generate_codebook_notes import (
    generate_case_codebook_notes,
)
from scripts.human_reliability.generate_report import generate_case_report
from scripts.human_reliability.ingest_adjudication import ingest_adjudication
from scripts.human_reliability.ingest_submission import (
    ingest_submission,
    parse_json_submission,
)
from scripts.human_reliability.status import evaluate_case, write_case_status
from test.test_human_adjudication_ingestion import (
    adjudication_root,
    valid_adjudication,
)
from test.test_human_reliability_ingestion import (
    ingestion_root,
    valid_submission,
)
from test.test_human_reliability_packets import SOURCE_ROOT, write_json


COHORT_ID = "demo-fr-cmt-cohort"
VERSION = "1.0.0"


def copy_status_schema(root: Path) -> None:
    shutil.copy(
        SOURCE_ROOT / "schemas" / "human-reliability" / "status-schema.json",
        root / "schemas" / "human-reliability" / "status-schema.json",
    )


class HumanReliabilityStatusTest(unittest.TestCase):
    def test_distinguishes_absent_and_designed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir))
            copy_status_schema(root)
            result = evaluate_case(root, "demo")
            self.assertEqual("designed", result["state"])
            self.assertTrue(result["valid"])
            self.assertEqual(1, result["counts"]["cohorts"])
            self.assertIn("cohorts are designed", result["warnings"][0])

        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir))
            shutil.rmtree(root / "cases" / "demo" / "quality" / "human-reliability")
            copy_status_schema(root)
            result = evaluate_case(root, "demo")
            self.assertEqual("absent", result["state"])
            self.assertTrue(result["valid"])

    def test_partial_invalid_awaiting_adjudication_and_complete_states(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base)
            copy_status_schema(root)
            source = base / "coder-fr-001.json"
            write_json(source, valid_submission(root, "coder-fr-001"))
            ingest_submission(root, "demo", cohort_path, parse_json_submission(source))
            self.assertEqual("partial", evaluate_case(root, "demo")["state"])

            normalized = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "normalized"
                / "normalized-coder-runs.json"
            )
            data = json.loads(normalized.read_text())
            data["runs"][0]["submission"]["packet_hash"] = "sha256:" + "0" * 64
            normalized.write_text(json.dumps(data, indent=2) + "\n")
            self.assertEqual("invalid", evaluate_case(root, "demo")["state"])

        with tempfile.TemporaryDirectory() as temp_dir:
            root, _, queue = adjudication_root(Path(temp_dir))
            copy_status_schema(root)
            awaiting = evaluate_case(root, "demo")
            self.assertEqual("awaiting-adjudication", awaiting["state"])
            self.assertGreater(awaiting["cohorts"][0]["queue_count"], 0)

            source = Path(temp_dir) / "adjudication.json"
            write_json(source, valid_adjudication(root, queue))
            ingest_adjudication(root, "demo", COHORT_ID, VERSION, source)
            generate_case_report(root, "demo", COHORT_ID, VERSION)
            generate_case_codebook_notes(root, "demo")
            complete = evaluate_case(root, "demo")
            self.assertEqual("complete", complete["state"])
            self.assertEqual(1, complete["counts"]["correction_candidates"])

    def test_written_status_matches_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir))
            copy_status_schema(root)

            status = write_case_status(root, "demo")

            schema = json.loads(
                (
                    SOURCE_ROOT
                    / "schemas"
                    / "human-reliability"
                    / "status-schema.json"
                ).read_text()
            )
            Draft202012Validator(schema).validate(status)
            path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "status.json"
            )
            self.assertEqual(json.loads(path.read_text()), status)
            self.assertEqual("designed", write_case_status(root, "demo")["state"])


if __name__ == "__main__":
    unittest.main()
