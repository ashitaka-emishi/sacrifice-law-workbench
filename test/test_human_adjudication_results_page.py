from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.human_reliability.generate_adjudication_results_page import (
    AdjudicationResultsPageError,
    collect_results,
    generate_results_page,
    render_results_page,
)
from scripts.human_reliability.ingest_adjudication import ingest_adjudication
from scripts.human_reliability.ingest_submission import cohort_hash
from test.test_human_adjudication_ingestion import (
    adjudication_root,
    valid_adjudication,
)
from test.test_human_reliability_ingestion import ingestion_root
from test.test_human_reliability_packets import write_json


COHORT_ID = "demo-fr-cmt-cohort"
VERSION = "1.0.0"


def ingest_decisions(
    base: Path, *, unresolved: bool = False
) -> tuple[Path, Path]:
    root, cohort_path, queue = adjudication_root(base)
    submission = valid_adjudication(root, queue)
    if unresolved:
        for decision in submission["decisions"]:
            decision.update(
                {
                    "status": "unresolved",
                    "selected_basis": "no_resolution",
                    "adjudicated_value": None,
                    "confidence": None,
                    "correction_candidate": {
                        "status": "deferred",
                        "candidate_id": None,
                        "target": None,
                        "rationale": (
                            "No correction can be proposed before resolution."
                        ),
                        "promotion_status": "pending_separate_authorization",
                        "promotion_id": None,
                        "direct_write_permitted": False,
                    },
                    "follow_up": {
                        "required": True,
                        "actions": [
                            "Consult additional source-language evidence."
                        ],
                        "owner_role": "adjudication_coordinator",
                        "due_at": None,
                    },
                }
            )
    source = base / "adjudication.json"
    write_json(source, submission)
    ingest_adjudication(root, "demo", COHORT_ID, VERSION, source)
    return root, cohort_path


class HumanAdjudicationResultsPageTest(unittest.TestCase):
    def test_empty_repository_renders_honest_not_started_page(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "cases").mkdir()
            output = root / "results.qmd"

            generate_results_page(root, output)

            rendered = output.read_text(encoding="utf-8")
            generate_results_page(root, output)
            self.assertEqual(
                rendered, output.read_text(encoding="utf-8")
            )
            self.assertIn("No cohorts discovered", rendered)
            self.assertIn("not evidence of agreement", rendered)
            self.assertIn("proposals, not promoted corrections", rendered)

    def test_approved_cohort_without_results_is_not_started(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir))

            cohorts = collect_results(root)

            self.assertEqual(1, len(cohorts))
            self.assertEqual("not_started", cohorts[0]["state"])
            self.assertEqual(0, cohorts[0]["summary"]["decision_count"])
            rendered = render_results_page(cohorts)
            self.assertIn(
                "| not_started | 0 | 0 | 0 | 0 | 0 | 0 |", rendered
            )

    def test_complete_results_render_outcomes_without_sensitive_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, _ = ingest_decisions(base)

            cohorts = collect_results(root)

            self.assertEqual("complete", cohorts[0]["state"])
            self.assertGreater(cohorts[0]["summary"]["accepted_count"], 0)
            self.assertEqual(1, cohorts[0]["candidate_count"])
            self.assertGreater(
                cohorts[0]["codebook_implications"].get("none", 0), 0
            )
            rendered = render_results_page(cohorts)
            self.assertIn("`cmt.target_domain`", rendered)
            self.assertIn("pending_separate_authorization", rendered)
            self.assertNotIn("NATION IS A DEFENDED BODY", rendered)
            self.assertNotIn(
                "The source context and field criteria support", rendered
            )
            self.assertNotIn("demo-doc-001_annotated.json", rendered)
            self.assertIn("No claim impacts are available", rendered)

    def test_unresolved_results_remain_unresolved_with_follow_up(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingest_decisions(Path(temp_dir), unresolved=True)

            cohorts = collect_results(root)

            self.assertEqual("unresolved", cohorts[0]["state"])
            self.assertGreater(cohorts[0]["summary"]["unresolved_count"], 0)
            self.assertEqual(0, cohorts[0]["candidate_count"])
            self.assertTrue(
                all(
                    row["follow_up_required"]
                    for row in cohorts[0]["decision_details"]
                )
            )

    def test_local_only_cohort_withholds_item_level_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, cohort_path = ingest_decisions(Path(temp_dir))
            cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
            cohort["storage_policy"] = "local_only"
            cohort["rights_constraints"] = ["restricted-source"]
            cohort["approval"]["manifest_sha256"] = cohort_hash(cohort)
            write_json(cohort_path, cohort)
            results_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "adjudication"
                / "results"
                / f"{COHORT_ID}-{VERSION}"
                / "adjudication-results.json"
            )
            results = json.loads(results_path.read_text(encoding="utf-8"))
            for row in results["decisions"]:
                row["queue_entry"]["storage_policy"] = "local_only"
                row["queue_entry"]["rights_constraints"] = [
                    "restricted-source"
                ]
            write_json(results_path, results)

            cohorts = collect_results(root)
            rendered = render_results_page(cohorts)

            self.assertEqual([], cohorts[0]["decision_details"])
            self.assertIn("item-level metadata withheld", rendered)
            self.assertNotIn("adjudication-demo-001", rendered)
            self.assertNotIn("`cmt.target_domain`", rendered)

    def test_rejects_tampered_summary_and_candidate_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingest_decisions(Path(temp_dir))
            human = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
            )
            results_path = (
                human
                / "adjudication"
                / "results"
                / f"{COHORT_ID}-{VERSION}"
                / "adjudication-results.json"
            )
            results = json.loads(results_path.read_text(encoding="utf-8"))
            results["summary"]["accepted_count"] += 1
            write_json(results_path, results)

            with self.assertRaisesRegex(
                AdjudicationResultsPageError, "accepted_count"
            ):
                collect_results(root)

    def test_rejects_candidate_identity_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingest_decisions(Path(temp_dir))
            candidate_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "correction-candidates"
                / f"{COHORT_ID}-{VERSION}"
                / "correction-candidates.json"
            )
            candidates = json.loads(candidate_path.read_text(encoding="utf-8"))
            candidates["candidates"][0]["adjudication_id"] = (
                "adjudication-different"
            )
            write_json(candidate_path, candidates)

            with self.assertRaisesRegex(
                AdjudicationResultsPageError, "candidate IDs"
            ):
                collect_results(root)

    def test_public_markdown_escapes_machine_metadata(self) -> None:
        rendered = render_results_page(
            [
                {
                    "case_id": "<script>alert(1)</script>",
                    "cohort_id": "cohort|one`",
                    "cohort_version": "1",
                    "source_language": "fr",
                    "task_layer": "cmt",
                    "state": "complete",
                    "storage_policy": "repository_allowed",
                    "rights_constraints": ["safe|right"],
                    "summary": {
                        "decision_count": 1,
                        "accepted_count": 1,
                        "rejected_count": 0,
                        "deferred_count": 0,
                        "unresolved_count": 0,
                    },
                    "candidate_count": 0,
                    "decision_details": [
                        {
                            "adjudication_id": "<b>decision</b>",
                            "field": "cmt.target|domain",
                            "status": "accepted",
                            "selected_basis": "left_coder",
                            "claim_impact": "ordinary",
                            "source_language_risk": "low",
                            "codebook_need": "none",
                            "recoding_required": False,
                            "correction_candidate": "not_candidate",
                            "follow_up_required": False,
                        }
                    ],
                    "codebook_implications": {},
                    "claim_impacts": {},
                }
            ]
        )

        self.assertNotIn("<script>", rendered)
        self.assertNotIn("<b>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("cohort\\|one&#96;", rendered)
        self.assertIn("cmt.target\\|domain", rendered)


if __name__ == "__main__":
    unittest.main()
