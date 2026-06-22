from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from scripts.human_reliability.generate_codebook_notes import (
    HumanCodebookNotesError,
    generate_case_codebook_notes,
)
from scripts.human_reliability.ingest_adjudication import ingest_adjudication
from scripts.human_reliability.ingest_submission import cohort_hash
from test.test_human_adjudication_ingestion import (
    adjudication_root,
    valid_adjudication,
)
from test.test_human_reliability_ingestion import corpus_snapshot
from test.test_human_reliability_packets import write_json


SOURCE_ROOT = Path(__file__).resolve().parents[1]
COHORT_ID = "demo-fr-cmt-cohort"
VERSION = "1.0.0"


def ambiguity_root(base: Path) -> tuple[Path, dict]:
    root, _, queue = adjudication_root(base)
    log_path = (
        root
        / "cases"
        / "demo"
        / "quality"
        / "human-reliability"
        / "comparisons"
        / f"{COHORT_ID}-{VERSION}"
        / "disagreement-log.json"
    )
    log = json.loads(log_path.read_text(encoding="utf-8"))
    for disagreement in log["disagreements"]:
        disagreement["possible_codebook_ambiguity"] = True
        disagreement["codebook_ambiguity_reasons"] = [
            "Repeated contrastive coding requires clearer field guidance."
        ]
    seed = log["disagreements"][0]
    for suffix, field, category in (
        ("aaaaaaaaaaaaaaaa", "cmt.cluster_id", "clusters"),
        ("bbbbbbbbbbbbbbbb", "cmt.source_domain_primary", "domains"),
    ):
        duplicate = copy.deepcopy(seed)
        duplicate["disagreement_id"] = f"human-disagreement-{suffix}"
        duplicate["field"] = field
        duplicate["category"] = category
        duplicate["field_category"] = category
        log["disagreements"].append(duplicate)
    log["summary"]["total_disagreements"] = len(log["disagreements"])
    log["summary"]["possible_codebook_ambiguity_count"] = len(
        log["disagreements"]
    )
    write_json(log_path, log)
    return root, queue


def adjudicated_revision(base: Path) -> Path:
    root, queue = ambiguity_root(base)
    submission = valid_adjudication(root, queue)
    for decision in submission["decisions"]:
        decision["codebook_need"] = {
            "status": "revision",
            "affected_sections": ["CMT target-domain decision rule"],
            "rationale": (
                "The reviewed contrast requires a more explicit distinction."
            ),
            "recoding_required": True,
        }
    source = base / "adjudication.json"
    write_json(source, submission)
    ingest_adjudication(root, "demo", COHORT_ID, VERSION, source)
    return root


class HumanCodebookRevisionNotesTest(unittest.TestCase):
    def test_ambiguity_generates_proposed_scoped_notes_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ambiguity_root(Path(temp_dir))
            before = corpus_snapshot(root)

            notes = generate_case_codebook_notes(root, "demo")

            self.assertEqual(before, corpus_snapshot(root))
            self.assertGreater(notes["summary"]["recommendation_count"], 0)
            self.assertEqual(
                notes["summary"]["recommendation_count"],
                notes["summary"]["proposed_count"],
            )
            self.assertTrue(
                all(
                    item["disposition"] == "proposed"
                    and item["affected_cases"] == ["demo"]
                    and item["affected_languages"] == ["fr"]
                    and item["affected_layers"] == ["cmt"]
                    for item in notes["recommendations"]
                )
            )
            self.assertFalse(notes["authority"]["codebook_edit_permitted"])
            self.assertFalse(
                notes["authority"]["retroactive_change_permitted"]
            )
            markdown = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "codebook"
                / "codebook-revision-notes.md"
            ).read_text(encoding="utf-8")
            self.assertIn("## Proposed recommendations", markdown)
            self.assertIn("## Accepted recommendations", markdown)
            self.assertIn("## Rejected recommendations", markdown)
            self.assertIn("## Deferred recommendations", markdown)
            self.assertIn("do not edit a", markdown)

    def test_adjudication_records_revision_migration_and_recoding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = adjudicated_revision(Path(temp_dir))

            notes = generate_case_codebook_notes(root, "demo")

            item = next(
                item
                for item in notes["recommendations"]
                if item["adjudication_ids"]
            )
            self.assertEqual("revision", item["recommended_action"])
            self.assertTrue(item["recoding_required"])
            self.assertEqual(
                ["CMT target-domain decision rule"],
                item["affected_sections"],
            )
            self.assertGreater(len(item["adjudication_ids"]), 0)
            self.assertIn("separately authorized migration", item["migration_implications"])
            self.assertEqual(1, notes["summary"]["recoding_required_count"])
            schema = json.loads(
                (
                    SOURCE_ROOT
                    / "schemas"
                    / "human-reliability"
                    / "codebook-revision-notes-schema.json"
                ).read_text(encoding="utf-8")
            )
            Draft202012Validator(
                schema, format_checker=FormatChecker()
            ).validate(notes)

    def test_human_register_distinguishes_accepted_rejected_and_deferred(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = adjudicated_revision(Path(temp_dir))
            initial = generate_case_codebook_notes(root, "demo")
            ids = [
                (
                    item["recommendation_id"],
                    item["recommendation_sha256"],
                )
                for item in initial["recommendations"]
            ]
            decision_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "codebook"
                / "recommendation-decisions.json"
            )
            decisions = []
            dispositions = ("accepted", "rejected", "deferred")
            for index, (
                recommendation_id,
                recommendation_sha256,
            ) in enumerate(ids):
                disposition = dispositions[index % len(dispositions)]
                decisions.append(
                    {
                        "recommendation_id": recommendation_id,
                        "recommendation_sha256": recommendation_sha256,
                        "disposition": disposition,
                        "rationale": f"Governance disposition: {disposition}.",
                        "reviewer": (
                            "methodology-reviewer"
                            if disposition != "deferred"
                            else None
                        ),
                        "decided_at": (
                            "2026-06-22T20:00:00Z"
                            if disposition != "deferred"
                            else None
                        ),
                    }
                )
            write_json(
                decision_path,
                {
                    "schema_version": "1.0.0",
                    "case_id": "demo",
                    "decision_authority": "human-methodology-review",
                    "decisions": decisions,
                },
            )
            original_register = decision_path.read_bytes()

            governed = generate_case_codebook_notes(root, "demo")

            self.assertEqual(original_register, decision_path.read_bytes())
            self.assertTrue(
                all(
                    item["decision_source"] == "human-decision-register"
                    for item in governed["recommendations"]
                )
            )
            observed = {
                item["disposition"] for item in governed["recommendations"]
            }
            self.assertEqual(set(dispositions), observed)

    def test_ids_and_outputs_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = adjudicated_revision(Path(temp_dir))
            first = generate_case_codebook_notes(root, "demo")
            output = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "codebook"
            )
            first_json = (output / "codebook-revision-notes.json").read_bytes()
            first_md = (output / "codebook-revision-notes.md").read_bytes()

            second = generate_case_codebook_notes(root, "demo")

            self.assertEqual(
                [item["recommendation_id"] for item in first["recommendations"]],
                [item["recommendation_id"] for item in second["recommendations"]],
            )
            self.assertEqual(
                first_json, (output / "codebook-revision-notes.json").read_bytes()
            )
            self.assertEqual(
                first_md, (output / "codebook-revision-notes.md").read_bytes()
            )

    def test_rejects_unknown_or_invalid_governance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ambiguity_root(Path(temp_dir))
            codebook = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "codebook"
            )
            codebook.mkdir(parents=True)
            write_json(
                codebook / "recommendation-decisions.json",
                {
                    "schema_version": "1.0.0",
                    "case_id": "demo",
                    "decision_authority": "human-methodology-review",
                    "decisions": [
                        {
                            "recommendation_id": (
                                "human-codebook-rec-0000000000000000"
                            ),
                            "recommendation_sha256": "sha256:" + "0" * 64,
                            "disposition": "accepted",
                            "rationale": "Unmatched decision.",
                            "reviewer": "reviewer",
                            "decided_at": "2026-06-22T20:00:00Z",
                        }
                    ],
                },
            )

            with self.assertRaisesRegex(
                HumanCodebookNotesError, "unknown recommendation"
            ):
                generate_case_codebook_notes(root, "demo")

    def test_governance_text_is_escaped_in_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ambiguity_root(Path(temp_dir))
            initial = generate_case_codebook_notes(root, "demo")
            recommendation_id = initial["recommendations"][0][
                "recommendation_id"
            ]
            recommendation_sha256 = initial["recommendations"][0][
                "recommendation_sha256"
            ]
            decision_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "codebook"
                / "recommendation-decisions.json"
            )
            write_json(
                decision_path,
                {
                    "schema_version": "1.0.0",
                    "case_id": "demo",
                    "decision_authority": "human-methodology-review",
                    "decisions": [
                        {
                            "recommendation_id": recommendation_id,
                            "recommendation_sha256": recommendation_sha256,
                            "disposition": "accepted",
                            "rationale": "<script>alert(1)</script> | `unsafe`",
                            "reviewer": "<b>reviewer</b>",
                            "decided_at": "2026-06-22T20:00:00Z",
                        }
                    ],
                },
            )

            generate_case_codebook_notes(root, "demo")
            markdown = (
                decision_path.parent / "codebook-revision-notes.md"
            ).read_text(encoding="utf-8")

            self.assertNotIn("<script>", markdown)
            self.assertNotIn("<b>", markdown)
            self.assertIn("&lt;script&gt;", markdown)
            self.assertIn("\\|", markdown)
            self.assertIn("&#96;unsafe&#96;", markdown)

    def test_stale_governance_fingerprint_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ambiguity_root(Path(temp_dir))
            initial = generate_case_codebook_notes(root, "demo")
            item = initial["recommendations"][0]
            decision_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "codebook"
                / "recommendation-decisions.json"
            )
            write_json(
                decision_path,
                {
                    "schema_version": "1.0.0",
                    "case_id": "demo",
                    "decision_authority": "human-methodology-review",
                    "decisions": [
                        {
                            "recommendation_id": item["recommendation_id"],
                            "recommendation_sha256": "sha256:" + "f" * 64,
                            "disposition": "accepted",
                            "rationale": "Approval for an older proposal.",
                            "reviewer": "reviewer",
                            "decided_at": "2026-06-22T20:00:00Z",
                        }
                    ],
                },
            )

            with self.assertRaisesRegex(
                HumanCodebookNotesError, "stale relative"
            ):
                generate_case_codebook_notes(root, "demo")

    def test_local_only_markdown_withholds_recommendation_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ambiguity_root(Path(temp_dir))
            cohort_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "cohorts"
                / f"{COHORT_ID}-{VERSION}.json"
            )
            cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
            cohort["storage_policy"] = "local_only"
            cohort["rights_constraints"] = ["restricted-source"]
            cohort["approval"]["manifest_sha256"] = cohort_hash(cohort)
            write_json(cohort_path, cohort)

            notes = generate_case_codebook_notes(root, "demo")
            markdown = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "codebook"
                / "codebook-revision-notes.md"
            ).read_text(encoding="utf-8")

            self.assertEqual("local_only", notes["storage_policy"])
            self.assertIn(
                "Detailed codebook recommendations are withheld", markdown
            )
            self.assertNotIn(
                notes["recommendations"][0]["recommendation_id"], markdown
            )
            self.assertNotIn(notes["recommendations"][0]["field"], markdown)


if __name__ == "__main__":
    unittest.main()
