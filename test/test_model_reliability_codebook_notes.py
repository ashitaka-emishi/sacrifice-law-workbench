from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from scripts.model_reliability.generate_codebook_notes import (
    CodebookNotesError,
    build_codebook_notes,
    generate_case_codebook_notes,
)
from scripts.model_reliability.generate_review_queue import (
    generate_case_review_queue,
)
from scripts.model_reliability.status import evaluate_case
from test.test_model_reliability_review_queue import (
    SOURCE_ROOT,
    review_queue_root,
)


class ModelReliabilityCodebookNotesTest(unittest.TestCase):
    def test_generates_stable_instability_and_training_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = review_queue_root(Path(temp_dir), include_invalid=True)
            generate_case_review_queue(root, "demo")

            notes = generate_case_codebook_notes(root, "demo")

            finding_types = {
                item["finding_type"] for item in notes["recommendations"]
            }
            self.assertIn("stable-category", finding_types)
            self.assertIn("ambiguous-instruction", finding_types)
            self.assertIn("common-model-error", finding_types)
            self.assertIn("multilingual-problem", finding_types)
            self.assertTrue(
                all(
                    item["disposition"] == "deferred"
                    and item["decision_source"] == "generated-default"
                    and item["training_use"]
                    for item in notes["recommendations"]
                )
            )
            self.assertEqual(
                notes["summary"]["deferred_count"],
                notes["summary"]["recommendation_count"],
            )
            self.assertEqual(
                notes["authority"]["decision_authority"], "human-only"
            )
            self.assertFalse(
                notes["authority"]["retroactive_change_permitted"]
            )
            schema = json.loads(
                (
                    SOURCE_ROOT
                    / "schemas"
                    / "model-reliability"
                    / "codebook-revision-notes-schema.json"
                ).read_text()
            )
            Draft202012Validator(
                schema, format_checker=FormatChecker()
            ).validate(notes)
            markdown = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "codebook"
                / "codebook-revision-notes.md"
            ).read_text()
            self.assertIn("## Accepted recommendations", markdown)
            self.assertIn("## Rejected recommendations", markdown)
            self.assertIn("## Deferred recommendations", markdown)
            self.assertIn("Training/calibration", markdown)
            self.assertIn("do not themselves edit the codebook", markdown)

    def test_recommendation_ids_do_not_shift_when_new_findings_arrive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = review_queue_root(Path(temp_dir))
            queue = generate_case_review_queue(root, "demo")
            model_root = (
                root / "cases" / "demo" / "quality" / "model-reliability"
            )
            agreement = json.loads(
                (model_root / "comparisons" / "agreement-results.json").read_text()
            )
            disagreements = json.loads(
                (model_root / "comparisons" / "disagreement-log.json").read_text()
            )
            first = build_codebook_notes(
                "demo", agreement, disagreements, queue
            )
            expanded = copy.deepcopy(queue)
            added = copy.deepcopy(expanded["entries"][0])
            added["queue_id"] = "review-9999"
            added["disagreement_id"] = "disagreement-9999"
            added["field"] = "aaa.new_field"
            added["category"] = "context-instability"
            expanded["entries"].append(added)

            second = build_codebook_notes(
                "demo", agreement, disagreements, expanded
            )

            first_ids = {
                (
                    item["finding_type"],
                    item["source_language"],
                    item["task_layer"],
                    item["field"],
                    tuple(item["categories"]),
                ): item["recommendation_id"]
                for item in first["recommendations"]
            }
            second_ids = {
                (
                    item["finding_type"],
                    item["source_language"],
                    item["task_layer"],
                    item["field"],
                    tuple(item["categories"]),
                ): item["recommendation_id"]
                for item in second["recommendations"]
            }
            self.assertTrue(
                all(second_ids[key] == value for key, value in first_ids.items())
            )

    def test_human_register_distinguishes_all_dispositions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = review_queue_root(Path(temp_dir), include_invalid=True)
            generate_case_review_queue(root, "demo")
            initial = generate_case_codebook_notes(root, "demo")
            ids = [
                item["recommendation_id"]
                for item in initial["recommendations"][:3]
            ]
            decision_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "codebook"
                / "recommendation-decisions.json"
            )
            decision_path.parent.mkdir(parents=True, exist_ok=True)
            decision_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "case_id": "demo",
                        "decision_authority": "human-only",
                        "decisions": [
                            {
                                "recommendation_id": ids[0],
                                "disposition": "accepted",
                                "rationale": "Useful clarification.",
                                "reviewer": "human-reviewer",
                                "decided_at": "2026-06-19T12:00:00Z",
                            },
                            {
                                "recommendation_id": ids[1],
                                "disposition": "rejected",
                                "rationale": "Shared model behavior is misleading.",
                                "reviewer": "human-reviewer",
                                "decided_at": "2026-06-19T12:05:00Z",
                            },
                            {
                                "recommendation_id": ids[2],
                                "disposition": "deferred",
                                "rationale": "Needs more source-language examples.",
                                "reviewer": None,
                                "decided_at": None,
                            },
                        ],
                    },
                    indent=2,
                )
                + "\n"
            )

            notes = generate_case_codebook_notes(root, "demo")

            self.assertEqual(notes["summary"]["accepted_count"], 1)
            self.assertEqual(notes["summary"]["rejected_count"], 1)
            self.assertGreaterEqual(notes["summary"]["deferred_count"], 1)
            decided = {
                item["recommendation_id"]: item
                for item in notes["recommendations"]
            }
            self.assertEqual(decided[ids[0]]["disposition"], "accepted")
            self.assertEqual(
                decided[ids[0]]["decision_source"],
                "human-decision-register",
            )
            decision_schema = json.loads(
                (
                    SOURCE_ROOT
                    / "schemas"
                    / "model-reliability"
                    / "codebook-recommendation-decisions-schema.json"
                ).read_text()
            )
            Draft202012Validator(
                decision_schema, format_checker=FormatChecker()
            ).validate(json.loads(decision_path.read_text()))

            stale_decisions = json.loads(decision_path.read_text())
            stale_decisions["decisions"][0]["rationale"] = "Changed after generation."
            decision_path.write_text(
                json.dumps(stale_decisions, indent=2) + "\n"
            )
            stale = evaluate_case(root, "demo")
            self.assertEqual(stale["state"], "invalid")
            self.assertTrue(
                any("stale relative" in error for error in stale["errors"])
            )

    def test_rejects_untrusted_sources_and_invalid_human_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = review_queue_root(Path(temp_dir))
            queue = generate_case_review_queue(root, "demo")
            model_root = (
                root / "cases" / "demo" / "quality" / "model-reliability"
            )
            agreement = json.loads(
                (model_root / "comparisons" / "agreement-results.json").read_text()
            )
            disagreements = json.loads(
                (model_root / "comparisons" / "disagreement-log.json").read_text()
            )
            untrusted = copy.deepcopy(queue)
            untrusted["generator"] = "untrusted"
            with self.assertRaisesRegex(CodebookNotesError, "untrusted"):
                build_codebook_notes(
                    "demo", agreement, disagreements, untrusted
                )

            initial = build_codebook_notes(
                "demo", agreement, disagreements, queue
            )
            decision_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "codebook"
                / "recommendation-decisions.json"
            )
            decision_path.parent.mkdir(parents=True, exist_ok=True)
            decision_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "case_id": "demo",
                        "decision_authority": "human-only",
                        "decisions": [
                            {
                                "recommendation_id": initial[
                                    "recommendations"
                                ][0]["recommendation_id"],
                                "disposition": "accepted",
                                "rationale": "",
                                "reviewer": None,
                                "decided_at": None,
                            }
                        ],
                    }
                )
            )
            with self.assertRaisesRegex(
                CodebookNotesError, "requires reviewer"
            ):
                generate_case_codebook_notes(root, "demo")


if __name__ == "__main__":
    unittest.main()
