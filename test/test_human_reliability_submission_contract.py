from __future__ import annotations

import copy
import unittest

from jsonschema import Draft202012Validator

from scripts.human_reliability.generate_packets import (
    COMMON_COLUMNS,
    LAYER_COLUMNS,
    SUBMISSION_COLUMNS,
)
from scripts.human_reliability.submission_contract import (
    ResponseContext,
    SubmissionContext,
    load_csv_contract,
    load_schema,
    validate_submission,
)


PACKET_HASH = "sha256:" + "a" * 64


def context(task_layer: str = "cmt") -> SubmissionContext:
    return SubmissionContext(
        cohort_id=f"fixture-cohort-fr-{task_layer}",
        cohort_version="1.0.0",
        case_id="fixture-case",
        sample_id="fixture-sample",
        sample_version="1.0.0",
        packet_id="fixture-packet",
        packet_hash=PACKET_HASH,
        source_language="fr",
        task_layer=task_layer,
        codebook_version="fixture-codebook-v1",
        training_version="human-training-v1",
        calibration_id="calibration-fr-v1",
        primary_coder_ids=frozenset({"coder-fr-001", "coder-fr-002"}),
        responses={
            "fixture-item-001": ResponseContext(
                document_id="fixture-doc-001",
                sentence_id="fixture-sentence-001",
                source_span_id="fixture-span-001",
                lexical_unit_ids=("fixture-lu-001", "fixture-lu-002"),
            )
        },
    )


def valid_submission(task_layer: str = "cmt") -> dict:
    response = {
        "item_id": "fixture-item-001",
        "task_layer": task_layer,
        "document_id": "fixture-doc-001",
        "sentence_id": "fixture-sentence-001",
        "source_span_id": "fixture-span-001",
        "lexical_unit_ids": ["fixture-lu-001", "fixture-lu-002"],
        "disposition": "coded",
        "confidence": 0.8,
        "uncertainty": "low",
        "uncertainty_note": "A conventional reading remains possible.",
        "out_of_scope_reason": None,
        "notes": "Coded from the French source.",
        "case_fields": {"fixture-case__register_note": "ceremonial"},
    }
    if task_layer == "cmt":
        response["cmt_response"] = {
            "source_domain_primary": "war_combat",
            "source_domain_secondary": ["body"],
            "target_domain": "nation",
            "conceptual_mapping": "NATION IS A DEFENDED BODY",
            "entailments": ["collective action protects the polity"],
            "cluster_id": "fixture-cluster-001",
            "rival_reading": "Literal political defense.",
        }
    elif task_layer == "identification":
        response["lexical_unit_responses"] = [
            {
                "lexical_unit_id": unit_id,
                "boundary_response": "exact",
                "decision_type": "mipvu_indirect",
                "contextual_meaning": "A contextual meaning.",
                "basic_meaning": "A basic meaning.",
                "basic_meaning_source": "Synthetic lexicon.",
                "contrast_explanation": "The meanings contrast.",
                "comparison_basis": "The context invokes another domain.",
            }
            for unit_id in ("fixture-lu-001", "fixture-lu-002")
        ]
    else:
        response["interpretation_response"] = {
            "sacred_object": "present",
            "sacrificial_body": "uncertain",
            "enemy_as_bringer_of_death": "absent",
            "violence_logic": "present",
            "obligatory_frame": "present",
            "purification": "not_applicable",
            "agents": ["the people"],
            "patients": [],
            "beneficiaries": ["the polity"],
            "excluded_agents": [],
            "absence_decision": "uncertain",
            "absence_scope": "complete sentence",
            "presence_criterion": "explicit or grammatically recoverable agency",
            "rival_reading": "Ceremonial convention.",
        }
    return {
        "schema_version": "1.0.0",
        "submission_id": "fixture-submission-001",
        "cohort_id": "fixture-cohort-fr-cmt",
        "cohort_version": "1.0.0",
        "case_id": "fixture-case",
        "sample_id": "fixture-sample",
        "sample_version": "1.0.0",
        "packet_id": "fixture-packet",
        "packet_hash": PACKET_HASH,
        "source_language": "fr",
        "task_layer": task_layer,
        "codebook_version": "fixture-codebook-v1",
        "coder_id": "coder-fr-001",
        "coder_role": "primary",
        "qualification_attested": True,
        "source_language_qualified": True,
        "training_version": "human-training-v1",
        "training_completed_at": "2026-06-20T12:00:00Z",
        "calibration_id": "calibration-fr-v1",
        "calibration_completed_at": "2026-06-20T13:00:00Z",
        "conflict_status": "none_declared",
        "conflict_details": None,
        "independence_attested": True,
        "ai_assistance_used": False,
        "completed_at": "2026-06-21T12:00:00Z",
        "responses": [response],
    }


class HumanSubmissionContractTest(unittest.TestCase):
    def test_json_schema_and_csv_contract_are_valid_and_aligned(self) -> None:
        schema = load_schema()
        Draft202012Validator.check_schema(schema)
        csv_contract = load_csv_contract()
        self.assertEqual(SUBMISSION_COLUMNS, csv_contract["metadata_columns"])
        self.assertEqual(
            COMMON_COLUMNS[len(SUBMISSION_COLUMNS):],
            csv_contract["common_response_columns"],
        )
        self.assertEqual(LAYER_COLUMNS, csv_contract["layer_columns"])

    def test_valid_multilingual_contract_supports_multiple_lexical_units(self) -> None:
        for task_layer in ("identification", "cmt", "interpretation"):
            with self.subTest(task_layer=task_layer):
                submission = valid_submission(task_layer)
                submission["cohort_id"] = f"fixture-cohort-fr-{task_layer}"
                active_context = context(task_layer)
                self.assertEqual(validate_submission(submission, active_context), [])

    def test_rejects_unknown_ids_packet_identity_and_controlled_vocabulary(self) -> None:
        submission = copy.deepcopy(valid_submission())
        submission["packet_hash"] = "sha256:" + "b" * 64
        submission["coder_id"] = "unknown-coder"
        submission["calibration_id"] = "unknown-calibration"
        response = submission["responses"][0]
        response["sentence_id"] = "unknown-sentence"
        response["lexical_unit_ids"] = ["unknown-lu"]
        response["cmt_response"]["source_domain_primary"] = "invented-domain"

        errors = validate_submission(submission, context())

        self.assertTrue(any("packet_hash" in error and "does not match" in error for error in errors))
        self.assertTrue(any("coder_id" in error and "not an assigned" in error for error in errors))
        self.assertTrue(any("calibration_id" in error and "does not match" in error for error in errors))
        self.assertTrue(any("sentence_id" in error and "does not match" in error for error in errors))
        self.assertTrue(any("lexical_unit_ids" in error and "does not match" in error for error in errors))
        self.assertTrue(any("unknown controlled value" in error for error in errors))

    def test_requires_exact_identification_coverage_and_case_namespace(self) -> None:
        submission = valid_submission("identification")
        submission["cohort_id"] = "fixture-cohort-fr-identification"
        response = submission["responses"][0]
        response["lexical_unit_responses"].pop()
        response["case_fields"] = {"lincoln__note": "wrong namespace"}
        active_context = context("identification")

        errors = validate_submission(submission, active_context)

        self.assertTrue(any("must cover every packet lexical unit" in error for error in errors))
        self.assertTrue(any("fixture-case__" in error for error in errors))

    def test_out_of_scope_forbids_substantive_response(self) -> None:
        submission = valid_submission()
        response = submission["responses"][0]
        response["disposition"] = "out_of_scope"
        response["confidence"] = None
        response["out_of_scope_reason"] = "missing_context"

        errors = validate_submission(submission, context())

        self.assertTrue(any("should not be valid" in error for error in errors))

    def test_rejects_undeclared_ai_assistance(self) -> None:
        submission = valid_submission()
        submission["ai_assistance_used"] = True

        errors = validate_submission(submission, context())

        self.assertTrue(any("not allowed by this independent cohort" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
