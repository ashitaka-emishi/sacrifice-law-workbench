from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.model_reliability.generate_consensus_report import (
    ConsensusReportError,
    build_consensus_report,
    generate_case_consensus_report,
)
from scripts.model_reliability.generate_review_queue import (
    generate_case_review_queue,
)
from test.test_model_reliability_review_queue import review_queue_root


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def consensus_root(base: Path) -> Path:
    root = review_queue_root(base)
    generate_case_review_queue(root, "demo")
    return root


def inputs(root: Path) -> tuple[dict, dict, dict]:
    model_root = (
        root / "cases" / "demo" / "quality" / "model-reliability"
    )
    return (
        json.loads(
            (model_root / "comparisons" / "agreement-results.json").read_text()
        ),
        json.loads(
            (model_root / "comparisons" / "disagreement-log.json").read_text()
        ),
        json.loads(
            (model_root / "review-queue" / "model-review-queue.json").read_text()
        ),
    )


class ModelReliabilityConsensusReportTest(unittest.TestCase):
    def test_generates_schema_valid_report_with_separate_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = consensus_root(Path(temp_dir))
            corpus_root = root / "cases" / "demo" / "corpus"
            before = {
                path.relative_to(corpus_root).as_posix(): path.read_bytes()
                for path in corpus_root.rglob("*")
                if path.is_file()
            }

            report = generate_case_consensus_report(root, "demo")

            after = {
                path.relative_to(corpus_root).as_posix(): path.read_bytes()
                for path in corpus_root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before, after)
            self.assertFalse(report["authority"]["consensus_is_evidence"])
            self.assertEqual(
                report["authority"]["decision_authority"], "human-only"
            )
            stability = {
                (row["task_layer"], row["field"]): row
                for row in report["model_stability"]
            }
            self.assertEqual(
                stability[("identification", "identification.decision")][
                    "status"
                ],
                "unstable",
            )
            self.assertEqual(
                stability[
                    ("identification", "identification.boundary_decision")
                ]["status"],
                "stable",
            )
            reference = {
                (row["task_layer"], row["field"]): row
                for row in report["reference_diagnostics"]
            }
            self.assertIn(
                reference[("cmt", "cmt.target_domain")]["status"],
                {"mixed-reference-alignment", "diverges-from-reference"},
            )
            self.assertGreater(len(report["risk_dimensions"]["by_document"]), 0)
            self.assertEqual(
                len(report["review_priorities"]),
                report["summary"]["review_queue_count"],
            )
            self.assertTrue(
                all(
                    row["decision_authority"] == "human-only"
                    for row in report["review_priorities"]
                )
            )

            schema = json.loads(
                (
                    SOURCE_ROOT
                    / "schemas"
                    / "model-reliability"
                    / "consensus-report-schema.json"
                ).read_text()
            )
            Draft202012Validator(schema).validate(report)
            markdown = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "comparisons"
                / "consensus-report.md"
            ).read_text()
            self.assertIn("## Model-to-model field stability", markdown)
            self.assertIn("## Reference diagnostics", markdown)
            self.assertIn("not scholarly evidence", markdown)

    def test_report_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = consensus_root(Path(temp_dir))
            first = generate_case_consensus_report(root, "demo")
            output = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "comparisons"
                / "consensus-report.json"
            )
            first_bytes = output.read_bytes()
            second = generate_case_consensus_report(root, "demo")
            self.assertEqual(first, second)
            self.assertEqual(first_bytes, output.read_bytes())

    def test_unanimous_reference_challenges_are_not_reported_as_support(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = consensus_root(Path(temp_dir))
            agreement, disagreement, queue = inputs(root)
            target = next(
                record
                for record in disagreement["disagreements"]
                if record["field"] == "cmt.target_domain"
            )
            target["unanimous_reference_challenge"] = True
            target["agreement_pattern"] = "unanimous-reference-challenge"
            target["category"] = "reference-challenge"
            disagreement["summary"]["unanimous_reference_challenges"] += 1

            report = build_consensus_report(
                "demo", agreement, disagreement, queue
            )

            target_diagnostic = next(
                row
                for row in report["reference_diagnostics"]
                if row["field"] == "cmt.target_domain"
            )
            self.assertEqual(
                target_diagnostic["unanimous_reference_challenge_count"], 1
            )
            self.assertEqual(
                target_diagnostic["status"], "challenged-reference"
            )
            self.assertGreater(
                report["summary"]["unanimous_reference_challenge_count"], 0
            )
            self.assertFalse(report["authority"]["consensus_is_evidence"])

    def test_rejects_stale_or_inconsistent_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = consensus_root(Path(temp_dir))
            agreement, disagreement, queue = inputs(root)

            stale = copy.deepcopy(queue)
            stale["run_ids"] = ["different-a", "different-b"]
            with self.assertRaisesRegex(ConsensusReportError, "run_ids"):
                build_consensus_report(
                    "demo", agreement, disagreement, stale
                )

            untrusted = copy.deepcopy(agreement)
            untrusted["generator"] = "untrusted"
            with self.assertRaisesRegex(ConsensusReportError, "untrusted"):
                build_consensus_report(
                    "demo", untrusted, disagreement, queue
                )

            missing = copy.deepcopy(queue)
            missing["entries"].pop()
            missing["summary"]["queue_count"] -= 1
            with self.assertRaisesRegex(ConsensusReportError, "IDs"):
                build_consensus_report(
                    "demo", agreement, disagreement, missing
                )

            unreconciled = copy.deepcopy(disagreement)
            unreconciled["summary"]["total_disagreements"] += 1
            with self.assertRaisesRegex(ConsensusReportError, "reconcile"):
                build_consensus_report(
                    "demo", agreement, unreconciled, queue
                )


if __name__ == "__main__":
    unittest.main()
