from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts.human_reliability.ingest_submission import (
    ingest_submission,
    parse_json_submission,
)
from scripts.human_reliability.pipeline import main, readiness, run_pipeline
from test.test_human_reliability_ingestion import (
    corpus_snapshot,
    ingestion_root,
    valid_submission,
)
from test.test_human_reliability_packets import write_json


COHORT_ID = "demo-fr-cmt-cohort"
COHORT_VERSION = "1.0.0"


def ingest_fixture_coder(root: Path, base: Path, cohort_path: Path, coder_id: str) -> None:
    source = base / f"{coder_id}.json"
    write_json(source, valid_submission(root, coder_id))
    ingest_submission(root, "demo", cohort_path, parse_json_submission(source))


class HumanReliabilityPipelineTest(unittest.TestCase):
    def test_no_submission_state_succeeds_with_clear_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, cohort_path = ingestion_root(Path(temp_dir))
            before = corpus_snapshot(root)

            result = run_pipeline(
                root,
                "demo",
                cohort_path,
                cohort_id=COHORT_ID,
                cohort_version=COHORT_VERSION,
                revision="fixture-human-ingestion-v1",
            )

            self.assertEqual("awaiting-submissions", result["status"])
            self.assertEqual(["packets"], result["completed_stages"])
            self.assertIn("no human submissions", result["warning"])
            self.assertEqual(before, corpus_snapshot(root))
            self.assertFalse(
                (
                    root
                    / "cases"
                    / "demo"
                    / "quality"
                    / "human-reliability"
                    / "comparisons"
                ).exists()
            )

    def test_partial_submission_state_succeeds_without_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base)
            ingest_fixture_coder(root, base, cohort_path, "coder-fr-001")

            result = run_pipeline(
                root,
                "demo",
                cohort_path,
                cohort_id=COHORT_ID,
                cohort_version=COHORT_VERSION,
                revision="fixture-human-ingestion-v1",
            )

            self.assertEqual("awaiting-primary-coders", result["status"])
            self.assertEqual(1, result["valid_submission_count"])
            self.assertEqual(["coder-fr-001"], result["valid_primary_coders"])
            self.assertIn("2 primary coder", result["warning"])

    def test_end_to_end_run_produces_downstream_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base)
            ingest_fixture_coder(root, base, cohort_path, "coder-fr-001")
            ingest_fixture_coder(root, base, cohort_path, "coder-fr-002")
            before = corpus_snapshot(root)

            result = run_pipeline(
                root,
                "demo",
                cohort_path,
                cohort_id=COHORT_ID,
                cohort_version=COHORT_VERSION,
                revision="fixture-human-ingestion-v1",
            )

            self.assertEqual("complete", result["status"])
            self.assertEqual(
                [
                    "packets",
                    "agreement",
                    "reference",
                    "disagreements",
                    "adjudication-queue",
                    "report",
                    "codebook-notes",
                ],
                result["completed_stages"],
            )
            self.assertEqual(before, corpus_snapshot(root))
            comparison_root = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "comparisons"
                / f"{COHORT_ID}-{COHORT_VERSION}"
            )
            for relative in (
                "human-agreement.json",
                "reference-comparison.json",
                "disagreement-log.json",
                "adjudication-queue.json",
                "human-reliability-report.json",
                "human-reliability-report.md",
            ):
                self.assertTrue((comparison_root / relative).is_file(), relative)
            self.assertTrue(
                (
                    root
                    / "cases"
                    / "demo"
                    / "quality"
                    / "human-reliability"
                    / "codebook"
                    / "codebook-revision-notes.json"
                ).is_file()
            )

    def test_cli_run_reports_warning_and_returns_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, cohort_path = ingestion_root(Path(temp_dir))
            stdout = io.StringIO()
            stderr = io.StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(
                    [
                        "--root",
                        str(root),
                        "run",
                        "--case",
                        "demo",
                        "--cohort",
                        COHORT_ID,
                        "--cohort-version",
                        COHORT_VERSION,
                        "--cohort-manifest",
                        str(cohort_path),
                        "--code-revision",
                        "fixture-human-pipeline-v1",
                    ]
                )

            self.assertEqual(0, code)
            self.assertIn("awaiting-submissions", stdout.getvalue())
            self.assertIn("WARNING:", stderr.getvalue())
            self.assertEqual(
                "awaiting-submissions",
                readiness(root, "demo", COHORT_ID, COHORT_VERSION)["status"],
            )

    def test_cli_ingest_exposes_manual_json_submission(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base)
            source = base / "coder-fr-001.json"
            write_json(source, valid_submission(root, "coder-fr-001"))
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                code = main(
                    [
                        "--root",
                        str(root),
                        "ingest",
                        "--case",
                        "demo",
                        "--cohort-manifest",
                        str(cohort_path),
                        "--json",
                        str(source),
                    ]
                )

            self.assertEqual(0, code)
            self.assertIn("cohort ingestion is partial", stdout.getvalue())
            status_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "ingestion-status.json"
            )
            self.assertEqual(
                "partial",
                json.loads(status_path.read_text())["cohorts"][0]["state"],
            )


if __name__ == "__main__":
    unittest.main()
