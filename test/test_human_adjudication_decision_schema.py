from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    ROOT / "schemas" / "human-reliability" / "adjudication-decision-schema.json"
)
TEMPLATE_PATH = (
    ROOT / "docs" / "reliability" / "adjudication"
    / "adjudication-decision-template.json"
)


def errors(value: dict) -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return [
        error.message
        for error in Draft202012Validator(schema).iter_errors(value)
    ]


def template() -> dict:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def terminal_base(status: str) -> dict:
    value = template()
    decision = value["decisions"][0]
    decision.update(
        {
            "status": status,
            "confidence": 0.85,
            "follow_up": {
                "required": False,
                "actions": [],
                "owner_role": None,
                "due_at": None,
            },
            "codebook_need": {
                "status": "none",
                "affected_sections": [],
                "rationale": "The existing field guidance is sufficient.",
                "recoding_required": False,
            },
        }
    )
    return value


class HumanAdjudicationDecisionSchemaTest(unittest.TestCase):
    def test_template_is_schema_valid_unresolved_submission(self) -> None:
        self.assertEqual([], errors(template()))

    def test_supports_accepted_with_separate_correction_candidate(self) -> None:
        value = terminal_base("accepted")
        decision = value["decisions"][0]
        decision.update(
            {
                "selected_basis": "new_value",
                "adjudicated_value": "freedom",
                "correction_candidate": {
                    "status": "candidate",
                    "candidate_id": "correction-candidate-example-001",
                    "target": {
                        "canonical_artifact": (
                            "cases/example-case/corpus/annotated/example.json"
                        ),
                        "target_id": "example-reference-001",
                        "field": "cmt.target_domain",
                        "current_value": "nation",
                        "proposed_value": "freedom",
                    },
                    "rationale": (
                        "The adjudicated value differs from the current reference."
                    ),
                    "promotion_status": "pending_separate_authorization",
                    "promotion_id": None,
                    "direct_write_permitted": False,
                },
            }
        )

        self.assertEqual([], errors(value))

    def test_supports_rejected_deferred_and_unresolved(self) -> None:
        rejected = terminal_base("rejected")
        rejected["decisions"][0].update(
            {
                "selected_basis": "out_of_scope",
                "adjudicated_value": None,
                "correction_candidate": {
                    "status": "not_candidate",
                    "candidate_id": None,
                    "target": None,
                    "rationale": "The item cannot be adjudicated within scope.",
                    "promotion_status": "pending_separate_authorization",
                    "promotion_id": None,
                    "direct_write_permitted": False,
                },
            }
        )
        self.assertEqual([], errors(rejected))

        retained = copy.deepcopy(rejected)
        retained["decisions"][0]["selected_basis"] = "retain_current_reference"
        retained["decisions"][0]["rationale"] = (
            "The proposed change is rejected and the current reference is retained."
        )
        self.assertEqual([], errors(retained))

        for status in ("deferred", "unresolved"):
            with self.subTest(status=status):
                value = template()
                value["decisions"][0]["status"] = status
                self.assertEqual([], errors(value))

    def test_terminal_and_nonterminal_value_invariants_fail_closed(self) -> None:
        accepted = terminal_base("accepted")
        accepted["decisions"][0].update(
            {
                "selected_basis": "new_value",
                "adjudicated_value": None,
            }
        )
        self.assertTrue(errors(accepted))

        deferred = template()
        deferred["decisions"][0].update(
            {
                "status": "deferred",
                "selected_basis": "left_coder",
                "adjudicated_value": "nation",
                "confidence": 0.5,
                "follow_up": {
                    "required": False,
                    "actions": [],
                    "owner_role": None,
                    "due_at": None,
                },
            }
        )
        self.assertTrue(errors(deferred))

        cluster = terminal_base("accepted")
        cluster["decisions"][0].update(
            {
                "field": "cmt.cluster_id",
                "selected_basis": "left_coder",
                "adjudicated_value": None,
            }
        )
        self.assertEqual([], errors(cluster))

    def test_correction_candidate_cannot_promote_or_write_directly(self) -> None:
        value = terminal_base("accepted")
        decision = value["decisions"][0]
        decision.update(
            {
                "selected_basis": "reference",
                "adjudicated_value": "hope",
                "correction_candidate": {
                    "status": "candidate",
                    "candidate_id": "correction-candidate-example-002",
                    "target": {
                        "canonical_artifact": (
                            "cases/example-case/corpus/annotated/example.json"
                        ),
                        "target_id": "example-reference-001",
                        "field": "cmt.target_domain",
                        "current_value": "nation",
                        "proposed_value": "hope",
                    },
                    "rationale": "A later review may consider this correction.",
                    "promotion_status": "promoted",
                    "promotion_id": "promotion-example-001",
                    "direct_write_permitted": True,
                },
            }
        )
        self.assertTrue(errors(value))

        forbidden = copy.deepcopy(value)
        forbidden["decisions"][0]["correction_candidate"].update(
            {
                "promotion_status": "pending_separate_authorization",
                "promotion_id": None,
                "direct_write_permitted": False,
            }
        )
        forbidden["decisions"][0]["reference_update"] = {
            "path": "cases/example-case/corpus/annotated/example.json"
        }
        self.assertTrue(errors(forbidden))

        traversal = copy.deepcopy(value)
        traversal["decisions"][0]["correction_candidate"].update(
            {
                "promotion_status": "pending_separate_authorization",
                "promotion_id": None,
                "direct_write_permitted": False,
            }
        )
        traversal["decisions"][0]["correction_candidate"]["target"][
            "canonical_artifact"
        ] = "cases/example-case/corpus/../metadata/example.json"
        self.assertTrue(errors(traversal))

    def test_primary_coder_cannot_be_sole_adjudicator(self) -> None:
        value = template()
        value["adjudicator"]["primary_coder_for_cohort"] = True
        value["adjudicator"]["sole_adjudicator"] = True
        self.assertTrue(errors(value))

        value["adjudicator"]["sole_adjudicator"] = False
        self.assertTrue(errors(value))

        value["adjudicator"]["conflict_status"] = "declared_and_managed"
        value["adjudicator"]["conflict_details"] = (
            "Primary-coder participation is disclosed and panel-managed."
        )
        self.assertEqual([], errors(value))


if __name__ == "__main__":
    unittest.main()
