from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.model_reliability.pipeline import run_pipeline
from scripts.model_reliability.status import evaluate_case, write_case_status
from test.test_model_reliability_ingestion import (
    FIXTURE_ROOT,
    ingestion_root,
    valid_submission,
)
from test.test_model_reliability_packets import SOURCE_ROOT, fixture_root
from test.test_model_reliability_packets import write_json
from scripts.model_reliability.ingest_submission import (
    ingest_submission,
    parse_json_submission,
)


def status_root(base: Path, *, packets: bool = False) -> Path:
    root = fixture_root(base)
    schemas = root / "schemas" / "model-reliability"
    schemas.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE_ROOT / "schemas" / "model-reliability", schemas)
    if packets:
        from scripts.model_reliability.generate_packets import generate_packets

        generate_packets(root, "demo", revision="fixture-revision-v1")
    return root


class ModelReliabilityStatusTest(unittest.TestCase):
    def test_distinguishes_absent_and_designed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = status_root(Path(temp_dir))
            self.assertEqual(evaluate_case(root, "demo")["state"], "partial")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = status_root(Path(temp_dir), packets=True)
            result = evaluate_case(root, "demo")
            self.assertEqual(result["state"], "designed")
            self.assertTrue(result["valid"])
            self.assertIn("no valid external model submissions", result["warnings"][0])

    def test_absent_case_has_warning_but_no_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = status_root(Path(temp_dir))
            model_root = (
                root / "cases" / "demo" / "quality" / "model-reliability"
            )
            shutil.rmtree(model_root)

            result = evaluate_case(root, "demo")

            self.assertEqual(result["state"], "absent")
            self.assertTrue(result["valid"])
            self.assertEqual(result["errors"], [])

    def test_partial_invalid_and_complete_states(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = ingestion_root(Path(temp_dir))
            target_schemas = root / "schemas" / "model-reliability"
            shutil.copy(
                SOURCE_ROOT
                / "schemas"
                / "model-reliability"
                / "status-schema.json",
                target_schemas / "status-schema.json",
            )
            first_path = Path(temp_dir) / "first.json"
            write_json(first_path, valid_submission(root, "status-first"))
            ingest_submission(root, "demo", parse_json_submission(first_path))
            self.assertEqual(evaluate_case(root, "demo")["state"], "partial")

            normalized = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "normalized"
                / "normalized-runs.json"
            )
            normalized_data = json.loads(normalized.read_text())
            normalized.write_text(
                json.dumps({**normalized_data, "runs": []}, indent=2) + "\n"
            )
            missing_run = evaluate_case(root, "demo")
            self.assertEqual(missing_run["state"], "invalid")
            self.assertTrue(
                any(
                    "do not match valid registrations" in error
                    for error in missing_run["errors"]
                )
            )

            normalized.write_text(json.dumps(normalized_data, indent=2) + "\n")
            stale = json.loads(normalized.read_text())
            stale["runs"][0]["submission"]["packet_hash"] = "sha256:" + "0" * 64
            normalized.write_text(json.dumps(stale, indent=2) + "\n")
            self.assertEqual(evaluate_case(root, "demo")["state"], "invalid")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = ingestion_root(Path(temp_dir))
            target_schemas = root / "schemas" / "model-reliability"
            shutil.copy(
                SOURCE_ROOT
                / "schemas"
                / "model-reliability"
                / "status-schema.json",
                target_schemas / "status-schema.json",
            )
            for suffix in ("status-a", "status-b"):
                submission_path = Path(temp_dir) / f"{suffix}.json"
                write_json(submission_path, valid_submission(root, suffix))
                ingest_submission(
                    root, "demo", parse_json_submission(submission_path)
                )
            run_pipeline(root, "demo", revision="fixture-revision-v1")
            result = evaluate_case(root, "demo")
            self.assertEqual(result["state"], "complete")
            self.assertEqual(result["counts"]["valid_runs"], 2)

    def test_written_status_matches_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = status_root(Path(temp_dir), packets=True)

            status = write_case_status(root, "demo")

            schema = json.loads(
                (
                    SOURCE_ROOT
                    / "schemas"
                    / "model-reliability"
                    / "status-schema.json"
                ).read_text()
            )
            Draft202012Validator(schema).validate(status)
            path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "status.json"
            )
            self.assertEqual(json.loads(path.read_text()), status)
            self.assertEqual(
                write_case_status(root, "demo")["state"], "designed"
            )

    def test_document_manifest_expansion_warns_without_invalidating_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = status_root(Path(temp_dir), packets=True)
            manifest_path = root / "cases" / "demo" / "metadata" / "document-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["documents"].append(
                {
                    "document_id": "demo-doc-002",
                    "title": "Expansion document",
                    "source_language": "en",
                    "source_url": "https://example.test/demo-doc-002",
                    "expected_raw_path": "corpus/raw/demo-doc-002.txt",
                    "date": "1900-01-01",
                    "register": "expansion",
                    "rights_status": "public-domain",
                }
            )
            write_json(manifest_path, manifest)

            result = evaluate_case(root, "demo")

            self.assertEqual(result["state"], "designed")
            self.assertTrue(result["valid"])
            self.assertEqual(result["errors"], [])
            self.assertTrue(
                any("expanded corpus" in warning for warning in result["warnings"])
            )


if __name__ == "__main__":
    unittest.main()
