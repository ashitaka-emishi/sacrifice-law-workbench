from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from scripts.human_reliability.classify_disagreements import (
    compute_case_disagreements,
)
from scripts.human_reliability.compare_references import (
    compute_case_reference_comparison,
)
from scripts.human_reliability.compute_agreement import compute_case_agreement
from scripts.human_reliability.generate_adjudication_queue import (
    generate_case_adjudication_queue,
)
from scripts.human_reliability.generate_packets import sha256_bytes
from scripts.human_reliability.ingest_adjudication import (
    AdjudicationIngestionError,
    ingest_adjudication,
)
from scripts.human_reliability.ingest_submission import (
    ingest_submission,
    parse_json_submission,
)
from test.test_human_reliability_ingestion import (
    corpus_snapshot,
    ingestion_root,
    valid_submission,
)
from test.test_human_reliability_packets import write_json


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def adjudication_root(base: Path) -> tuple[Path, Path, dict]:
    root, cohort_path = ingestion_root(base, "cmt")
    left = valid_submission(root, "coder-fr-001", "cmt")
    right = valid_submission(root, "coder-fr-002", "cmt")
    right["responses"][0]["cmt_response"]["target_domain"] = "hope"
    for submission in (left, right):
        source = base / f"{submission['coder_id']}.json"
        write_json(source, submission)
        ingest_submission(
            root, "demo", cohort_path, parse_json_submission(source)
        )
    compute_case_agreement(root, "demo", "demo-fr-cmt-cohort", "1.0.0")
    compute_case_reference_comparison(
        root, "demo", "demo-fr-cmt-cohort", "1.0.0"
    )
    compute_case_disagreements(
        root, "demo", "demo-fr-cmt-cohort", "1.0.0"
    )
    queue = generate_case_adjudication_queue(
        root, "demo", "demo-fr-cmt-cohort", "1.0.0"
    )
    return root, cohort_path, queue


def valid_adjudication(root: Path, queue: dict) -> dict:
    queue_path = (
        root / "cases" / "demo" / "quality" / "human-reliability"
        / "comparisons" / "demo-fr-cmt-cohort-1.0.0"
        / "adjudication-queue.json"
    )
    decisions = []
    for index, entry in enumerate(queue["entries"], start=1):
        candidate = {
            "status": "not_candidate",
            "candidate_id": None,
            "target": None,
            "rationale": "No correction candidate is proposed for this decision.",
            "promotion_status": "pending_separate_authorization",
            "promotion_id": None,
            "direct_write_permitted": False,
        }
        if entry["field"] == "cmt.target_domain":
            candidate = {
                "status": "candidate",
                "candidate_id": "correction-candidate-demo-target-001",
                "target": {
                    "canonical_artifact": (
                        "cases/demo/corpus/annotated/"
                        "demo-doc-001_annotated.json"
                    ),
                    "target_id": entry["reference_id"],
                    "field": entry["field"],
                    "current_value": entry["reference_summary"]["value"],
                    "proposed_value": entry["coder_values"][0]["value"],
                },
                "rationale": (
                    "The adjudicated coder value differs from the current reference."
                ),
                "promotion_status": "pending_separate_authorization",
                "promotion_id": None,
                "direct_write_permitted": False,
            }
        decisions.append(
            {
                "adjudication_id": f"adjudication-demo-{index:03d}",
                "queue_id": entry["queue_id"],
                "disagreement_id": entry["disagreement_id"],
                "item_id": entry["item_id"],
                "reference_id": entry["reference_id"],
                "unit_id": entry["unit_id"],
                "field": entry["field"],
                "status": "accepted",
                "selected_basis": "left_coder",
                "adjudicated_value": entry["coder_values"][0]["value"],
                "rationale": (
                    "The source context and field criteria support the left coder value."
                ),
                "evidence_consulted": [
                    {
                        "evidence_id": f"queue-evidence-{index:03d}",
                        "evidence_type": "queue_source_text",
                        "source": f"adjudication-queue.json#{entry['queue_id']}",
                        "sha256": None,
                        "note": "The frozen queue source text and coding context were reviewed.",
                    }
                ],
                "confidence": 0.85,
                "codebook_need": {
                    "status": "none",
                    "affected_sections": [],
                    "rationale": "The existing field guidance is sufficient.",
                    "recoding_required": False,
                },
                "correction_candidate": candidate,
                "affected_claims": [
                    {
                        "claim_id": claim["claim_id"],
                        "disposition": "review_required",
                        "rationale": (
                            "The claim should be checked against the adjudicated value."
                        ),
                    }
                    for claim in entry["affected_claims"]
                ],
                "affected_claim_dimensions": entry[
                    "affected_claim_dimensions"
                ],
                "follow_up": {
                    "required": False,
                    "actions": [],
                    "owner_role": None,
                    "due_at": None,
                },
                "decided_at": "2026-06-22T14:00:00Z",
            }
        )
    generator = queue["generator"]
    return {
        "schema_version": "1.0.0",
        "adjudication_submission_id": "adjudication-submission-demo-v1",
        "case_id": "demo",
        "cohort_id": "demo-fr-cmt-cohort",
        "cohort_version": "1.0.0",
        "source_language": "fr",
        "task_layer": "cmt",
        "queue_snapshot": {
            "queue_version": "1.0.0",
            "queue_schema_version": queue["schema_version"],
            "queue_source": (
                "quality/human-reliability/comparisons/"
                "demo-fr-cmt-cohort-1.0.0/adjudication-queue.json"
            ),
            "queue_sha256": sha256_bytes(queue_path.read_bytes()),
            "queue_generator_script": generator["script"],
            "queue_generator_version": generator["version"],
            "queue_generator_script_hash": generator["script_hash"],
            "queue_code_revision": generator["code_revision"],
            "frozen_at": "2026-06-22T13:00:00Z",
        },
        "adjudicator": {
            "adjudicator_id": "adjudicator-demo-001",
            "role": "authorized_human_adjudicator",
            "authorization_id": "authorization-demo-001",
            "independence_attested": True,
            "primary_coder_for_cohort": False,
            "sole_adjudicator": True,
            "source_language_qualified": True,
            "conflict_status": "none_declared",
            "conflict_details": None,
        },
        "submitted_at": "2026-06-22T15:00:00Z",
        "decisions": decisions,
    }


class HumanAdjudicationIngestionTest(unittest.TestCase):
    def test_valid_submission_is_preserved_normalized_and_candidates_are_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, _, queue = adjudication_root(base)
            before = corpus_snapshot(root)
            source = base / "adjudication.json"
            submission = valid_adjudication(root, queue)
            write_json(source, submission)

            report = ingest_adjudication(
                root,
                "demo",
                "demo-fr-cmt-cohort",
                "1.0.0",
                source,
            )

            self.assertEqual("valid", report["status"])
            self.assertEqual("complete", report["adjudication_state"])
            self.assertEqual(before, corpus_snapshot(root))
            human = (
                root / "cases" / "demo" / "quality" / "human-reliability"
            )
            raw = (
                human / "adjudication" / "decisions" / "raw"
                / report["registration_id"] / "adjudication.json"
            )
            self.assertEqual(source.read_bytes(), raw.read_bytes())
            results = json.loads(
                (
                    human / "adjudication" / "results"
                    / "demo-fr-cmt-cohort-1.0.0"
                    / "adjudication-results.json"
                ).read_text()
            )
            candidates = json.loads(
                (
                    human / "correction-candidates"
                    / "demo-fr-cmt-cohort-1.0.0"
                    / "correction-candidates.json"
                ).read_text()
            )
            self.assertEqual(len(queue["entries"]), len(results["decisions"]))
            self.assertEqual(1, len(candidates["candidates"]))
            self.assertFalse(candidates["authority"]["promotion_permitted"])
            self.assertFalse(
                candidates["candidates"][0]["direct_write_permitted"]
            )
            artifacts = (
                (report, "adjudication-ingestion-report-schema.json"),
                (
                    json.loads(
                        (
                            human / "adjudication" / "decisions"
                            / "adjudication-register.json"
                        ).read_text()
                    ),
                    "adjudication-register-schema.json",
                ),
                (results, "adjudication-results-schema.json"),
                (candidates, "correction-candidates-schema.json"),
            )
            for artifact, schema_name in artifacts:
                schema = json.loads(
                    (
                        root / "schemas" / "human-reliability" / schema_name
                    ).read_text()
                )
                Draft202012Validator(
                    schema, format_checker=FormatChecker()
                ).validate(artifact)

    def test_unresolved_decisions_are_preserved_without_ready_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, _, queue = adjudication_root(base)
            submission = valid_adjudication(root, queue)
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
            source = base / "unresolved.json"
            write_json(source, submission)

            report = ingest_adjudication(
                root, "demo", "demo-fr-cmt-cohort", "1.0.0", source
            )

            self.assertEqual("valid", report["status"])
            self.assertEqual("unresolved", report["adjudication_state"])
            candidates = json.loads(
                (
                    root / "cases" / "demo" / "quality" / "human-reliability"
                    / "correction-candidates"
                    / "demo-fr-cmt-cohort-1.0.0"
                    / "correction-candidates.json"
                ).read_text()
            )
            self.assertEqual([], candidates["candidates"])

    def test_rejects_queue_identity_duplicates_vocab_and_short_rationale(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, _, queue = adjudication_root(base)
            submission = valid_adjudication(root, queue)
            submission["queue_snapshot"]["queue_sha256"] = "sha256:" + "0" * 64
            submission["decisions"][0]["rationale"] = "Too short"
            target = next(
                decision
                for decision in submission["decisions"]
                if decision["field"] == "cmt.target_domain"
            )
            target["adjudicated_value"] = "invented-target-domain"
            submission["decisions"].append(copy.deepcopy(submission["decisions"][0]))
            unknown = copy.deepcopy(submission["decisions"][0])
            unknown["adjudication_id"] = "adjudication-demo-unknown"
            unknown["queue_id"] = "human-queue-ffffffffffffffff"
            submission["decisions"].append(unknown)
            source = base / "invalid.json"
            write_json(source, submission)

            report = ingest_adjudication(
                root, "demo", "demo-fr-cmt-cohort", "1.0.0", source
            )

            self.assertEqual("invalid", report["status"])
            joined = "\n".join(report["errors"])
            self.assertIn("does not match the frozen queue", joined)
            self.assertIn("unknown queue ID", joined)
            self.assertIn("duplicate queue ID", joined)
            self.assertIn("duplicate adjudication ID", joined)
            self.assertIn("evidence ID(s) already used", joined)
            self.assertIn("unknown controlled value", joined)
            self.assertIn("at least 20", joined)
            results = (
                root / "cases" / "demo" / "quality" / "human-reliability"
                / "adjudication" / "results" / "demo-fr-cmt-cohort-1.0.0"
                / "adjudication-results.json"
            )
            self.assertFalse(results.exists())

    def test_idempotence_duplicate_valid_queue_and_immutable_raw(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, _, queue = adjudication_root(base)
            source = base / "adjudication.json"
            write_json(source, valid_adjudication(root, queue))
            first = ingest_adjudication(
                root, "demo", "demo-fr-cmt-cohort", "1.0.0", source
            )
            repeated = ingest_adjudication(
                root, "demo", "demo-fr-cmt-cohort", "1.0.0", source
            )
            self.assertEqual(first, repeated)

            duplicate = valid_adjudication(root, queue)
            duplicate["adjudication_submission_id"] = (
                "adjudication-submission-demo-v2"
            )
            duplicate["submitted_at"] = "2026-06-22T15:01:00Z"
            duplicate_path = base / "duplicate.json"
            write_json(duplicate_path, duplicate)
            duplicate_report = ingest_adjudication(
                root, "demo", "demo-fr-cmt-cohort", "1.0.0", duplicate_path
            )
            self.assertEqual("invalid", duplicate_report["status"])
            self.assertTrue(
                any(
                    "valid adjudication already exists" in error
                    for error in duplicate_report["errors"]
                )
            )

            raw = (
                root / "cases" / "demo" / "quality" / "human-reliability"
                / "adjudication" / "decisions" / "raw"
                / first["registration_id"] / "adjudication.json"
            )
            raw.chmod(0o644)
            raw.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(
                AdjudicationIngestionError, "raw adjudication registration was altered"
            ):
                ingest_adjudication(
                    root, "demo", "demo-fr-cmt-cohort", "1.0.0", source
                )

    def test_candidate_target_must_match_queue_and_case(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, _, queue = adjudication_root(base)
            submission = valid_adjudication(root, queue)
            target = next(
                decision
                for decision in submission["decisions"]
                if decision["field"] == "cmt.target_domain"
            )
            target["correction_candidate"]["target"].update(
                {
                    "canonical_artifact": (
                        "cases/another-case/corpus/annotated/example.json"
                    ),
                    "target_id": "another-reference",
                    "current_value": "invented-current",
                    "proposed_value": "invented-proposed",
                }
            )
            source = base / "bad-candidate.json"
            write_json(source, submission)

            report = ingest_adjudication(
                root, "demo", "demo-fr-cmt-cohort", "1.0.0", source
            )

            self.assertEqual("invalid", report["status"])
            joined = "\n".join(report["errors"])
            self.assertIn("does not belong to the adjudicated case", joined)
            self.assertIn("does not match the queue reference ID", joined)
            self.assertIn("does not match the queue reference", joined)
            self.assertIn("does not match the adjudicated value", joined)

    def test_rejects_internally_duplicated_queue_before_registration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, _, queue = adjudication_root(base)
            queue_path = (
                root / "cases" / "demo" / "quality" / "human-reliability"
                / "comparisons" / "demo-fr-cmt-cohort-1.0.0"
                / "adjudication-queue.json"
            )
            queue["entries"].append(copy.deepcopy(queue["entries"][0]))
            queue["summary"]["queue_count"] += 1
            write_json(queue_path, queue)
            source = base / "adjudication.json"
            write_json(source, valid_adjudication(root, queue))

            with self.assertRaisesRegex(
                AdjudicationIngestionError, "duplicate.*queue IDs"
            ):
                ingest_adjudication(
                    root, "demo", "demo-fr-cmt-cohort", "1.0.0", source
                )

    def test_rejects_queue_rights_drift_from_approved_cohort(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, _, queue = adjudication_root(base)
            queue_path = (
                root / "cases" / "demo" / "quality" / "human-reliability"
                / "comparisons" / "demo-fr-cmt-cohort-1.0.0"
                / "adjudication-queue.json"
            )
            queue["entries"][0]["storage_policy"] = "local_only"
            write_json(queue_path, queue)
            source = base / "adjudication.json"
            write_json(source, valid_adjudication(root, queue))

            with self.assertRaisesRegex(
                AdjudicationIngestionError, "storage policy differs"
            ):
                ingest_adjudication(
                    root, "demo", "demo-fr-cmt-cohort", "1.0.0", source
                )

    def test_malformed_identity_is_still_preserved_as_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, _, queue = adjudication_root(base)
            submission = valid_adjudication(root, queue)
            submission["cohort_id"] = {"malformed": True}
            submission["adjudication_submission_id"] = ["not", "a", "string"]
            submission["queue_snapshot"]["queue_sha256"] = ["bad"]
            submission["adjudicator"]["adjudicator_id"] = {"bad": "identity"}
            submission["decisions"][0]["evidence_consulted"][0][
                "evidence_id"
            ] = {"bad": "evidence"}
            submission["decisions"][0]["affected_claim_dimensions"] = [
                {"bad": "dimension"}
            ]
            source = base / "malformed.json"
            write_json(source, submission)

            report = ingest_adjudication(
                root, "demo", "demo-fr-cmt-cohort", "1.0.0", source
            )

            self.assertEqual("invalid", report["status"])
            self.assertIsNone(report["cohort_id"])
            self.assertIsNone(report["adjudication_submission_id"])
            self.assertIsNone(report["adjudicator_id"])
            self.assertIsNone(report["queue_sha256"])
            raw = (
                root / "cases" / "demo" / "quality" / "human-reliability"
                / "adjudication" / "decisions" / "raw"
                / report["registration_id"] / "adjudication.json"
            )
            self.assertEqual(source.read_bytes(), raw.read_bytes())


if __name__ == "__main__":
    unittest.main()
