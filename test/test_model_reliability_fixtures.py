from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.model_reliability.generate_packets import generate_packets
from scripts.model_reliability.ingest_submission import ingest_submission, parse_json_submission
from test.test_model_reliability_ingestion import FIXTURE_ROOT, ingestion_root
from test.test_model_reliability_packets import fixture_root


class ModelReliabilityFixtureTest(unittest.TestCase):
    def test_fixture_is_rights_safe_and_small(self) -> None:
        manifest = json.loads((FIXTURE_ROOT / "fixture-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["rights_status"], "synthetic-cc0")
        fixture_files = [path for path in FIXTURE_ROOT.rglob("*") if path.is_file()]
        self.assertLess(sum(path.stat().st_size for path in fixture_files), 250_000)
        source = (
            FIXTURE_ROOT
            / "repository"
            / "cases"
            / "demo"
            / "corpus"
            / "segmented"
            / "demo-doc-001.json"
        ).read_text(encoding="utf-8")
        self.assertIn("La cité porte l'espoir.", source)
        self.assertIn("The city carries hope.", source)

    def test_committed_packet_fixture_regenerates_byte_identically(self) -> None:
        committed_dir = (
            FIXTURE_ROOT
            / "repository"
            / "cases"
            / "demo"
            / "quality"
            / "model-reliability"
            / "packets"
        )
        committed = {
            path.name: path.read_bytes() for path in committed_dir.iterdir() if path.is_file()
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = fixture_root(Path(temp_dir))
            generate_packets(root, "demo", revision="fixture-revision-v1")
            generated_dir = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "packets"
            )
            generated = {
                path.name: path.read_bytes() for path in generated_dir.iterdir() if path.is_file()
            }
        self.assertEqual(generated, committed)

    def test_valid_json_fixture_ingests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = ingestion_root(Path(temp_dir))
            source = FIXTURE_ROOT / "submissions" / "valid-cmt.json"
            report = ingest_submission(root, "demo", parse_json_submission(source))
        self.assertEqual(report["status"], "valid")
        self.assertEqual(report["errors"], [])

    def test_invalid_fixtures_name_the_violated_contract(self) -> None:
        expectations = {
            "invalid-field.json": ["greater than the maximum", "unknown controlled value"],
            "unknown-ids.json": ["unknown packet item ID", "unknown document ID", "unknown span ID"],
            "packet-mismatch.json": ["packet_hash", "exactly one task layer"],
            "duplicate-spans.json": ["duplicate item ID", "duplicate span set"],
        }
        for filename, expected_fragments in expectations.items():
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as temp_dir:
                root = ingestion_root(Path(temp_dir))
                source = FIXTURE_ROOT / "submissions" / filename
                report = ingest_submission(root, "demo", parse_json_submission(source))
                rendered = "\n".join(report["errors"])
                self.assertEqual(report["status"], "invalid")
                for fragment in expected_fragments:
                    self.assertIn(fragment, rendered)

    def test_comparison_fixture_has_two_controlled_disagreements(self) -> None:
        runs = json.loads(
            (FIXTURE_ROOT / "comparison" / "comparison-inputs.json").read_text(encoding="utf-8")
        )["runs"]
        expected = json.loads(
            (FIXTURE_ROOT / "comparison" / "expected-disagreements.json").read_text(
                encoding="utf-8"
            )
        )["expected"]
        by_run = [
            {item["item_id"]: item for item in run["items"]}
            for run in runs
        ]
        observed = []
        for expectation in expected:
            values = [
                run[expectation["item_id"]][expectation["field"]]
                for run in by_run
            ]
            if len(set(values)) > 1:
                observed.append(
                    {
                        "item_id": expectation["item_id"],
                        "field": expectation["field"],
                        "values": values,
                    }
                )
        self.assertEqual(len(observed), 2)
        self.assertEqual(
            {(item["item_id"], item["field"]) for item in observed},
            {(item["item_id"], item["field"]) for item in expected},
        )


if __name__ == "__main__":
    unittest.main()
