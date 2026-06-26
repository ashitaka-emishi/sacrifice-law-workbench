from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from scripts.human_reliability.boundaries import (
    ProtectedPathError,
    immutable_accepted_artifact_guard,
)
from scripts.human_reliability.classify_disagreements import (
    classify_disagreements,
)
from scripts.human_reliability.compute_agreement import compare_cohort
from scripts.human_reliability.generate_adjudication_queue import build_queue
from scripts.human_reliability.generate_packets import sha256_bytes
from scripts.human_reliability.ingest_adjudication import (
    _summary,
    validate_adjudication,
)
from scripts.human_reliability.submission_contract import (
    ResponseContext,
    SubmissionContext,
    validate_submission,
)


SOURCE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = (
    SOURCE_ROOT
    / "test"
    / "fixtures"
    / "human-reliability"
    / "rights-safe-fixtures.json"
)


def load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def submission_context(fixture: Mapping[str, Any]) -> SubmissionContext:
    raw = fixture["submission_context"]
    return SubmissionContext(
        cohort_id=raw["cohort_id"],
        cohort_version=raw["cohort_version"],
        case_id=raw["case_id"],
        sample_id=raw["sample_id"],
        sample_version=raw["sample_version"],
        packet_id=raw["packet_id"],
        packet_hash=raw["packet_hash"],
        source_language=raw["source_language"],
        task_layer=raw["task_layer"],
        codebook_version=raw["codebook_version"],
        training_version=raw["training_version"],
        calibration_id=raw["calibration_id"],
        primary_coder_ids=frozenset(raw["primary_coder_ids"]),
        responses={
            item_id: ResponseContext(
                document_id=response["document_id"],
                sentence_id=response["sentence_id"],
                source_span_id=response["source_span_id"],
                lexical_unit_ids=tuple(response["lexical_unit_ids"]),
            )
            for item_id, response in raw["responses"].items()
        },
    )


def normalized_runs(submissions: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "case_id": "human-fixture",
        "runs": [
            {
                "registration_id": f"human-fixture-registration-{index:03d}",
                "registered_at": "2026-06-21T12:00:00Z",
                "raw_hash": "sha256:" + str(index) * 64,
                "cohort_id": submission["cohort_id"],
                "cohort_version": submission["cohort_version"],
                "coder_id": submission["coder_id"],
                "submission": submission,
            }
            for index, submission in enumerate(submissions, start=1)
        ],
    }


def metric(result: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    return next(row for row in result["field_metrics"] if row["field"] == field)


def fixture_queue(fixture: Mapping[str, Any]) -> dict[str, Any]:
    inputs = fixture["disagreement_inputs"]
    log = classify_disagreements(
        inputs["agreement"],
        inputs["reference_comparison"],
        inputs["sample"],
    )
    return build_queue(
        log,
        inputs["packet_items"],
        claim_traces=inputs["claim_traces"],
        storage_policy=fixture["rights_policy"]["storage_policy"],
        revision="human-fixture-revision-v1",
    )


def decision_for_entry(entry: Mapping[str, Any], index: int, status: str) -> dict[str, Any]:
    unresolved = status == "unresolved"
    accepted_value = (
        entry["coder_values"][0]["value"] if not unresolved else None
    )
    candidate = {
        "status": "not_candidate" if not unresolved else "deferred",
        "candidate_id": None,
        "target": None,
        "rationale": (
            "No correction candidate is proposed for this adjudication decision."
            if not unresolved
            else "No correction can be proposed before the item is resolved."
        ),
        "promotion_status": "pending_separate_authorization",
        "promotion_id": None,
        "direct_write_permitted": False,
    }
    if (
        not unresolved
        and entry["field"] == "cmt.target_domain"
        and entry["reference_summary"]["status"] == "available"
    ):
        candidate = {
            "status": "candidate",
            "candidate_id": "correction-candidate-human-fixture-001",
            "target": {
                "canonical_artifact": (
                    "cases/human-fixture/corpus/annotated/"
                    "human-fixture-doc-001_annotated.json"
                ),
                "target_id": entry["reference_id"],
                "field": entry["field"],
                "current_value": entry["reference_summary"]["value"],
                "proposed_value": accepted_value,
            },
            "rationale": (
                "The adjudicated coder value is proposed as a separate correction "
                "candidate for later authorized promotion."
            ),
            "promotion_status": "pending_separate_authorization",
            "promotion_id": None,
            "direct_write_permitted": False,
        }
    return {
        "adjudication_id": f"adjudication-human-fixture-{index:03d}",
        "queue_id": entry["queue_id"],
        "disagreement_id": entry["disagreement_id"],
        "item_id": entry["item_id"],
        "reference_id": entry["reference_id"],
        "unit_id": entry["unit_id"],
        "field": entry["field"],
        "status": status,
        "selected_basis": "left_coder" if not unresolved else "no_resolution",
        "adjudicated_value": accepted_value,
        "rationale": (
            "The source-language evidence supports preserving this coder value."
            if not unresolved
            else "The fixture intentionally leaves this adjudication unresolved."
        ),
        "evidence_consulted": [
            {
                "evidence_id": f"human-fixture-evidence-{index:03d}",
                "evidence_type": "queue_source_text",
                "source": f"adjudication-queue.json#{entry['queue_id']}",
                "sha256": None,
                "note": "The frozen synthetic queue source text was reviewed.",
            }
        ],
        "confidence": 0.85 if not unresolved else None,
        "codebook_need": {
            "status": "none" if not unresolved else "unresolved",
            "affected_sections": [] if not unresolved else ["cmt"],
            "rationale": (
                "The existing field guidance is sufficient."
                if not unresolved
                else "More source-language review is required before guidance changes."
            ),
            "recoding_required": False,
        },
        "correction_candidate": candidate,
        "affected_claims": [
            {
                "claim_id": claim["claim_id"],
                "disposition": (
                    "review_required"
                    if not unresolved
                    else "hold_pending_resolution"
                ),
                "rationale": (
                    "The claim should be checked against the adjudicated value."
                    if not unresolved
                    else "The claim remains pending while adjudication is unresolved."
                ),
            }
            for claim in entry["affected_claims"]
        ],
        "affected_claim_dimensions": entry["affected_claim_dimensions"],
        "follow_up": {
            "required": unresolved,
            "actions": (
                ["Consult an additional source-language adjudicator."]
                if unresolved
                else []
            ),
            "owner_role": "adjudication_coordinator" if unresolved else None,
            "due_at": None,
        },
        "decided_at": "2026-06-22T14:00:00Z",
    }


def adjudication_submission(
    fixture: Mapping[str, Any],
    queue: Mapping[str, Any],
    queue_path: Path,
    *,
    status: str,
) -> dict[str, Any]:
    submission = copy.deepcopy(fixture["adjudication_template"])
    generator = queue["generator"]
    submission["queue_snapshot"].update(
        {
            "queue_schema_version": queue["schema_version"],
            "queue_source": queue_path.relative_to(
                SOURCE_ROOT / "cases" / queue["case_id"]
            ).as_posix(),
            "queue_sha256": sha256_bytes(
                json.dumps(queue, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ),
            "queue_generator_script": generator["script"],
            "queue_generator_version": generator["version"],
            "queue_generator_script_hash": generator["script_hash"],
            "queue_code_revision": generator["code_revision"],
        }
    )
    submission["decisions"] = [
        decision_for_entry(entry, index, status)
        for index, entry in enumerate(queue["entries"], start=1)
    ]
    return submission


class HumanReliabilityFixtureTest(unittest.TestCase):
    def test_fixture_submissions_validate_and_cover_contract_edges(self) -> None:
        fixture = load_fixture()
        context = submission_context(fixture)
        submissions = fixture["coder_submissions"]

        for submission in submissions:
            with self.subTest(coder=submission["coder_id"]):
                self.assertEqual([], validate_submission(submission, context))

        first_response = submissions[0]["responses"][0]
        partial_response = submissions[0]["responses"][1]
        self.assertEqual(2, len(first_response["lexical_unit_ids"]))
        self.assertEqual("out_of_scope", partial_response["disposition"])
        self.assertEqual("missing_context", partial_response["out_of_scope_reason"])
        self.assertNotIn("cmt_response", partial_response)

        invalid = copy.deepcopy(submissions[0])
        invalid["packet_hash"] = "sha256:" + "b" * 64
        invalid["coder_id"] = "unknown-coder"
        invalid["responses"][0]["sentence_id"] = "unknown-sentence"
        invalid["responses"][0]["lexical_unit_ids"] = ["unknown-lu"]
        invalid["responses"][0]["cmt_response"]["target_domain"] = "unknown-domain"

        errors = validate_submission(invalid, context)

        self.assertTrue(any("packet_hash" in error for error in errors))
        self.assertTrue(any("not an assigned primary coder" in error for error in errors))
        self.assertTrue(any("sentence_id" in error for error in errors))
        self.assertTrue(any("lexical_unit_ids" in error for error in errors))
        self.assertTrue(any("unknown controlled value" in error for error in errors))

    def test_fixture_submissions_drive_two_coder_metrics(self) -> None:
        fixture = load_fixture()
        submissions = fixture["coder_submissions"]

        result = compare_cohort(
            "human-fixture",
            normalized_runs(submissions),
            "human-fixture-fr-cmt-cohort",
            "1.0.0",
        )

        self.assertEqual(["coder-fr-001", "coder-fr-002"], result["coder_ids"])
        self.assertEqual(2, result["scope"]["item_count"])
        self.assertEqual({"missing_context": 2}, result["scope"]["out_of_scope_counts"])
        self.assertEqual(
            0.0,
            metric(result, "cmt.target_domain")["observed_agreement"]["value"],
        )
        self.assertAlmostEqual(
            0.2,
            metric(result, "confidence")["mean_absolute_difference"]["value"],
        )
        self.assertAlmostEqual(
            1 / 3,
            metric(result, "uncertainty")["mean_ordinal_distance"]["value"],
        )

    def test_fixture_queue_and_adjudication_cover_valid_and_unresolved(self) -> None:
        fixture = load_fixture()
        queue = fixture_queue(fixture)
        schema = json.loads(
            (
                SOURCE_ROOT
                / "schemas"
                / "human-reliability"
                / "adjudication-queue-schema.json"
            ).read_text(encoding="utf-8")
        )
        Draft202012Validator(schema).validate(queue)

        self.assertGreaterEqual(queue["summary"]["queue_count"], 2)
        self.assertTrue(
            all(
                entry["rights_constraints"] == ["synthetic-test-only"]
                for entry in queue["entries"]
            )
        )
        self.assertTrue(
            all(
                "La cité" in entry["source_text"]
                and "adjudication_decision" not in entry
                for entry in queue["entries"]
            )
        )

        queue_path = (
            SOURCE_ROOT
            / "cases"
            / "human-fixture"
            / "quality"
            / "human-reliability"
            / "comparisons"
            / "human-fixture-fr-cmt-cohort-1.0.0"
            / "adjudication-queue.json"
        )
        queue_hash = sha256_bytes(
            json.dumps(queue, ensure_ascii=False, sort_keys=True).encode("utf-8")
        )
        cohort = {
            "primary_coder_ids": ["coder-fr-001", "coder-fr-002"],
            "storage_policy": "repository_allowed",
        }
        accepted = adjudication_submission(
            fixture, queue, queue_path, status="accepted"
        )
        unresolved = adjudication_submission(
            fixture, queue, queue_path, status="unresolved"
        )

        self.assertEqual(
            [],
            validate_adjudication(
                SOURCE_ROOT, accepted, queue, queue_path, queue_hash, cohort
            ),
        )
        self.assertEqual(
            [],
            validate_adjudication(
                SOURCE_ROOT, unresolved, queue, queue_path, queue_hash, cohort
            ),
        )
        self.assertEqual("complete", _summary(accepted["decisions"])["state"])
        self.assertEqual("unresolved", _summary(unresolved["decisions"])["state"])
        candidates = [
            decision["correction_candidate"]
            for decision in accepted["decisions"]
            if decision["correction_candidate"]["status"] == "candidate"
        ]
        self.assertEqual(1, len(candidates))
        self.assertFalse(candidates[0]["direct_write_permitted"])
        self.assertEqual(
            "pending_separate_authorization",
            candidates[0]["promotion_status"],
        )

    def test_fixture_protected_path_guard_restores_accepted_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            case_root = root / "cases" / "human-fixture"
            protected = case_root / "corpus" / "annotated" / "accepted.json"
            protected.parent.mkdir(parents=True)
            protected.write_text("{\"accepted\":true}\n", encoding="utf-8")
            allowed = (
                case_root
                / "quality"
                / "human-reliability"
                / "fixture-output.json"
            )

            with self.assertRaisesRegex(
                ProtectedPathError, "attempted protected write"
            ):
                with immutable_accepted_artifact_guard(root, "human-fixture"):
                    protected.write_text("{\"accepted\":false}\n", encoding="utf-8")
                    allowed.parent.mkdir(parents=True)
                    allowed.write_text("{\"candidate\":true}\n", encoding="utf-8")

            self.assertEqual("{\"accepted\":true}\n", protected.read_text(encoding="utf-8"))
            self.assertTrue(allowed.exists())


if __name__ == "__main__":
    unittest.main()
