from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.model_reliability.completion_checklist import (
    REPOSITORY_COMMANDS,
    evaluate_completion,
    write_completion,
)
from scripts.model_reliability.pipeline import run_pipeline
from scripts.model_reliability.status import evaluate_case
from scripts.model_reliability.ingest_submission import (
    ingest_submission,
    parse_json_submission,
)
from test.test_model_reliability_ingestion import (
    ingestion_root,
    valid_submission,
)
from test.test_model_reliability_packets import SOURCE_ROOT, write_json


def completed_root(base: Path) -> Path:
    root = ingestion_root(base)
    for suffix in ("completion-a", "completion-b"):
        submission_path = base / f"{suffix}.json"
        write_json(submission_path, valid_submission(root, suffix))
        ingest_submission(root, "demo", parse_json_submission(submission_path))
    run_pipeline(root, "demo", revision="fixture-revision-v1")
    for relative in (
        "model-reliability-methodology.qmd",
        "model-reliability-results.qmd",
        "publication/model-reliability.md",
        "docs/reliability/external-model-review-procedures.md",
        "docs/reliability/model-reliability-governance.md",
        "docs/reliability/model-reliability-completion-checklist.md",
        "scripts/model_reliability/boundaries.py",
        "test/test_model_reliability_boundaries.py",
    ):
        source = SOURCE_ROOT / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, target)
    model_root = root / "cases" / "demo" / "quality" / "model-reliability"
    for relative in (
        "comparisons/agreement-summary.csv",
        "comparisons/disagreement-log.csv",
        "comparisons/instability-report.md",
        "review-queue/model-review-queue.csv",
    ):
        path = model_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")
    return root


def passing_repository_results() -> list[dict[str, object]]:
    return [
        {"command": command, "status": "pass", "exit_code": 0}
        for command in REPOSITORY_COMMANDS
    ]


class ModelReliabilityCompletionTest(unittest.TestCase):
    def test_complete_gate_requires_artifacts_authority_and_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = completed_root(Path(temp_dir))

            report = evaluate_completion(
                root,
                "demo",
                repository_results=passing_repository_results(),
            )

            self.assertEqual(report["status"], "complete")
            self.assertEqual(report["summary"]["failed_count"], 0)
            self.assertFalse(
                report["authority"]["consensus_changes_accepted_annotations"]
            )

    def test_gate_blocks_without_runs_and_repository_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = ingestion_root(Path(temp_dir))

            report = evaluate_completion(root, "demo")

            self.assertEqual(report["status"], "blocked")
            failed = set(report["summary"]["failed_check_ids"])
            self.assertIn("validated-runs", failed)
            self.assertIn("repository-validation", failed)

    def test_gate_rejects_unsafe_consensus_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = completed_root(Path(temp_dir))
            consensus_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "comparisons"
                / "consensus-report.json"
            )
            consensus = json.loads(consensus_path.read_text())
            consensus["authority"]["consensus_is_evidence"] = True
            consensus_path.write_text(json.dumps(consensus), encoding="utf-8")

            report = evaluate_completion(
                root,
                "demo",
                repository_results=passing_repository_results(),
            )

            self.assertEqual(report["status"], "blocked")
            self.assertIn(
                "consensus-authority",
                report["summary"]["failed_check_ids"],
            )

    def test_written_report_matches_schema_and_stays_in_writable_subtree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = completed_root(Path(temp_dir))
            report = evaluate_completion(
                root,
                "demo",
                repository_results=passing_repository_results(),
            )

            json_path, markdown_path = write_completion(root, "demo", report)

            schema = json.loads(
                (
                    SOURCE_ROOT
                    / "schemas"
                    / "model-reliability"
                    / "completion-checklist-schema.json"
                ).read_text()
            )
            Draft202012Validator(schema).validate(
                json.loads(json_path.read_text())
            )
            self.assertIn(
                "quality/model-reliability/completion",
                json_path.as_posix(),
            )
            self.assertIn("Status: **complete**", markdown_path.read_text())
            self.assertEqual(evaluate_case(root, "demo")["state"], "complete")

            tampered = json.loads(json_path.read_text())
            tampered["checks"][0]["status"] = "fail"
            json_path.write_text(json.dumps(tampered), encoding="utf-8")
            invalid = evaluate_case(root, "demo")
            self.assertEqual(invalid["state"], "invalid")
            self.assertTrue(
                any(
                    "completion status does not reconcile" in error
                    for error in invalid["errors"]
                )
            )


if __name__ == "__main__":
    unittest.main()
