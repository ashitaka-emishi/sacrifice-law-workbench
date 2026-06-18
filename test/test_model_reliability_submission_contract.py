from __future__ import annotations

import copy
import unittest

from jsonschema import Draft202012Validator

from scripts.model_reliability.submission_contract import (
    SubmissionContext,
    load_schema,
    validate_submission,
)


HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64


def valid_submission() -> dict:
    return {
        "schema_version": "1.0.0",
        "submission_id": "submission-001",
        "case_id": "fixture-case",
        "sample_id": "sample-001",
        "sample_version": "1",
        "packet_id": "packet-001",
        "packet_hash": HASH_A,
        "prompt_id": "prompt-001",
        "prompt_hash": HASH_B,
        "source_language": "fr",
        "code_revision": "abc1234",
        "run": {
            "run_id": "run-001",
            "provider": "example-provider",
            "model": "example-model",
            "model_version": None,
            "completed_at": "2026-06-18T12:00:00Z",
            "language_capabilities": ["fr", "en"],
            "settings": {"temperature": 0},
        },
        "items": [
            {
                "item_id": "item-001",
                "task_layer": "cmt",
                "case_id": "fixture-case",
                "document_id": "doc-001",
                "sentence_id": "sentence-001",
                "span_ids": ["span-001", "span-002"],
                "source_language": "fr",
                "sentence_source_text": "Le peuple porte et défend la patrie.",
                "sentence_gloss_en": "The people carry and defend the homeland.",
                "source_risk_flags": ["translation-check"],
                "lexical_units": [
                    {
                        "lexical_unit_id": "lu-001",
                        "span_id": "span-001",
                        "source_text": "porte",
                        "gloss_en": "carries",
                        "char_offset_start": 10,
                        "char_offset_end": 15,
                        "decision": "mipvu_indirect",
                        "boundary_decision": "exact",
                    },
                    {
                        "lexical_unit_id": "lu-002",
                        "span_id": "span-002",
                        "source_text": "défend",
                        "gloss_en": "defends",
                        "char_offset_start": 19,
                        "char_offset_end": 25,
                        "decision": "mipvu_indirect",
                        "boundary_decision": "exact",
                    },
                ],
                "cmt": {
                    "source_domain_primary": "war_combat",
                    "source_domain_secondary": ["body"],
                    "target_domain": "nation",
                    "conceptual_metaphor": "NATION IS A DEFENDED BODY",
                    "entailments": ["collective action protects the polity"],
                    "cluster_id": "fixture-cluster-001",
                },
                "confidence": 0.78,
                "uncertainty": {"status": "low", "note": "Conventional usage is possible."},
                "rival_reading": "A literal statement of political defense.",
                "case_fields": {"fixture-case__register_note": "ceremonial"},
            }
        ],
    }


def context() -> SubmissionContext:
    return SubmissionContext(
        packet_id="packet-001",
        packet_hash=HASH_A,
        case_id="fixture-case",
        document_ids=frozenset({"doc-001"}),
        sentence_documents={"sentence-001": "doc-001"},
        span_sentences={"span-001": "sentence-001", "span-002": "sentence-001"},
        item_ids=frozenset({"item-001"}),
        lexical_unit_ids=frozenset({"lu-001", "lu-002"}),
    )


class SubmissionContractTest(unittest.TestCase):
    def test_schema_is_valid_draft_2020_12(self) -> None:
        Draft202012Validator.check_schema(load_schema())

    def test_valid_multilingual_multi_lexical_unit_submission(self) -> None:
        self.assertEqual(validate_submission(valid_submission(), context()), [])

    def test_cmt_does_not_require_identification_decisions(self) -> None:
        submission = valid_submission()
        for unit in submission["items"][0]["lexical_units"]:
            del unit["decision"]
            del unit["boundary_decision"]

        self.assertEqual(validate_submission(submission, context()), [])

    def test_identification_requires_lexical_unit_decisions(self) -> None:
        submission = valid_submission()
        item = submission["items"][0]
        item["task_layer"] = "identification"
        del item["cmt"]
        item["identification"] = {
            "contextual_meaning": "A contextual meaning.",
            "basic_meaning": "A basic meaning.",
            "contrast_explanation": "The meanings contrast.",
            "comparison_basis": "Comparison across domains.",
        }
        del item["lexical_units"][0]["decision"]

        errors = validate_submission(submission, context())

        self.assertTrue(any("decision" in error and "required property" in error for error in errors))

    def test_rejects_packet_hash_unknown_ids_and_vocabulary(self) -> None:
        submission = copy.deepcopy(valid_submission())
        submission["packet_hash"] = HASH_B
        item = submission["items"][0]
        item["sentence_id"] = "sentence-unknown"
        item["span_ids"] = ["span-unknown"]
        item["lexical_units"][0]["span_id"] = "span-unknown"
        item["cmt"]["source_domain_primary"] = "invented-domain"

        errors = validate_submission(submission, context())

        self.assertTrue(any("packet_hash" in error and "does not match" in error for error in errors))
        self.assertTrue(any("unknown sentence ID" in error for error in errors))
        self.assertTrue(any("unknown span ID" in error for error in errors))
        self.assertTrue(any("unknown controlled value" in error for error in errors))

    def test_rejects_gloss_without_source_text(self) -> None:
        submission = copy.deepcopy(valid_submission())
        del submission["items"][0]["lexical_units"][0]["source_text"]

        errors = validate_submission(submission, context())

        self.assertTrue(any("source_text" in error and "required property" in error for error in errors))

    def test_rejects_non_namespaced_case_extension(self) -> None:
        submission = copy.deepcopy(valid_submission())
        submission["items"][0]["case_fields"] = {"other-case__note": "wrong namespace"}

        errors = validate_submission(submission, context())

        self.assertTrue(any("must use the `fixture-case__` namespace" in error for error in errors))

    def test_rejects_mixed_task_layers_and_language_mismatch(self) -> None:
        submission = copy.deepcopy(valid_submission())
        item = submission["items"][0]
        item["source_language"] = "en"
        item["identification"] = {
            "contextual_meaning": "A contextual meaning.",
            "basic_meaning": "A basic meaning.",
            "contrast_explanation": "The meanings contrast.",
            "comparison_basis": "Comparison across domains.",
        }

        errors = validate_submission(submission, context())

        self.assertTrue(any("source_language" in error and "does not match" in error for error in errors))
        self.assertTrue(any("identification" in error and "should not be valid" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
