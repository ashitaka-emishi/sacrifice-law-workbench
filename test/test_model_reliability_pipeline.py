from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts.model_reliability.pipeline import main, readiness, run_pipeline
from scripts.model_reliability.ingest_submission import IngestionError
from test.test_model_reliability_ingestion import (
    FIXTURE_ROOT,
    corpus_snapshot,
    ingestion_root,
)
from test.test_model_reliability_packets import fixture_root


def write_comparison_runs(root: Path, *, limit: int | None = None) -> Path:
    normalized = (
        root
        / "cases"
        / "demo"
        / "quality"
        / "model-reliability"
        / "normalized"
        / "normalized-runs.json"
    )
    source = json.loads(
        (
            FIXTURE_ROOT
            / "comparison"
            / "comparison-inputs.json"
        ).read_text()
    )
    manifest = json.loads(
        (
            root
            / "cases"
            / "demo"
            / "quality"
            / "model-reliability"
            / "packets"
            / "packet-manifest.json"
        ).read_text()
    )
    runs = source["runs"] if limit is None else source["runs"][:limit]
    for run in runs:
        run["packet_id"] = manifest["packet_id"]
        run["packet_hash"] = manifest["packet_hash"]
    source["runs"] = runs
    normalized.parent.mkdir(parents=True, exist_ok=True)
    normalized.write_text(json.dumps(source, indent=2) + "\n")
    return normalized


class ModelReliabilityPipelineTest(unittest.TestCase):
    def test_no_submission_state_succeeds_with_clear_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = fixture_root(Path(temp_dir))
            before = corpus_snapshot(root)

            result = run_pipeline(
                root, "demo", revision="fixture-revision-v1"
            )

            self.assertEqual(result["status"], "awaiting-submissions")
            self.assertEqual(result["completed_stages"], ["packets"])
            self.assertIn("no valid model submissions", result["warning"])
            self.assertEqual(before, corpus_snapshot(root))
            self.assertFalse(
                (
                    root
                    / "cases"
                    / "demo"
                    / "quality"
                    / "model-reliability"
                    / "comparisons"
                ).exists()
            )

    def test_one_run_state_succeeds_without_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = ingestion_root(Path(temp_dir))
            write_comparison_runs(root, limit=1)

            result = run_pipeline(
                root, "demo", revision="fixture-revision-v1"
            )

            self.assertEqual(result["status"], "awaiting-comparable-runs")
            self.assertEqual(result["run_count"], 1)
            self.assertIn("at least two comparable runs", result["warning"])

    def test_end_to_end_run_produces_all_downstream_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = ingestion_root(Path(temp_dir))
            write_comparison_runs(root)
            before = corpus_snapshot(root)

            result = run_pipeline(
                root, "demo", revision="fixture-revision-v1"
            )

            self.assertEqual(result["status"], "complete")
            self.assertEqual(
                result["completed_stages"],
                [
                    "packets",
                    "comparison",
                    "disagreements",
                    "review-queue",
                    "report",
                    "codebook-notes",
                ],
            )
            self.assertGreater(result["disagreement_count"], 0)
            self.assertEqual(before, corpus_snapshot(root))
            model_root = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
            )
            for relative in (
                "comparisons/agreement-results.json",
                "comparisons/disagreement-log.json",
                "review-queue/model-review-queue.json",
                "comparisons/consensus-report.json",
                "comparisons/consensus-report.md",
            ):
                self.assertTrue((model_root / relative).is_file(), relative)

    def test_run_preserves_packet_manifest_when_valid_runs_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = ingestion_root(Path(temp_dir))
            write_comparison_runs(root)
            manifest_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "packets"
                / "packet-manifest.json"
            )
            before = json.loads(manifest_path.read_text(encoding="utf-8"))

            result = run_pipeline(
                root,
                "demo",
                revision="different-revision-that-would-rotate-packets",
            )

            after = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "complete")
            self.assertEqual(before, after)

    def test_rotate_packets_flag_makes_stale_run_rejection_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = ingestion_root(Path(temp_dir))
            write_comparison_runs(root)

            with self.assertRaisesRegex(IngestionError, "current packet_hash"):
                run_pipeline(
                    root,
                    "demo",
                    revision="different-revision-that-rotates-packets",
                    rotate_packets=True,
                )

    def test_cli_run_reports_warning_and_returns_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = fixture_root(Path(temp_dir))
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
                        "--code-revision",
                        "fixture-revision-v1",
                    ]
                )

            self.assertEqual(code, 0)
            self.assertIn("awaiting-submissions", stdout.getvalue())
            self.assertIn("WARNING:", stderr.getvalue())
            self.assertEqual(readiness(root, "demo")["run_count"], 0)

    def test_cli_ingest_exposes_manual_json_submission(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = ingestion_root(Path(temp_dir))
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                code = main(
                    [
                        "--root",
                        str(root),
                        "ingest",
                        "--case",
                        "demo",
                        "--json",
                        str(
                            FIXTURE_ROOT
                            / "submissions"
                            / "valid-cmt.json"
                        ),
                    ]
                )

            self.assertEqual(code, 0)
            self.assertIn("is valid with 0 error(s)", stdout.getvalue())

    def test_run_rejects_submissions_for_a_stale_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = ingestion_root(Path(temp_dir))
            normalized = write_comparison_runs(root)
            data = json.loads(normalized.read_text())
            data["runs"][0]["packet_hash"] = "sha256:" + "0" * 64
            normalized.write_text(json.dumps(data, indent=2) + "\n")

            with self.assertRaisesRegex(IngestionError, "current packet_hash"):
                run_pipeline(
                    root, "demo", revision="fixture-revision-v1"
                )


if __name__ == "__main__":
    unittest.main()
