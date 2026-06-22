from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.human_reliability.classify_disagreements import (
    HumanDisagreementError,
    category_for_field,
    classify_disagreements,
    compute_case_disagreements,
)
from scripts.human_reliability.compare_references import (
    compute_case_reference_comparison,
)
from scripts.human_reliability.compute_agreement import compute_case_agreement
from scripts.human_reliability.ingest_submission import (
    ingest_submission,
    parse_json_submission,
)
from test.test_human_reliability_ingestion import ingestion_root, valid_submission
from test.test_human_reliability_packets import write_json


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def upstream_artifacts() -> tuple[dict, dict, dict]:
    identity = {
        "case_id": "demo",
        "cohort_id": "demo-fr-cmt-cohort",
        "cohort_version": "1.0.0",
        "source_language": "fr",
        "task_layer": "cmt",
        "packet_id": "demo-packet",
        "input_runs": [
            {
                "registration_id": "registration-1",
                "raw_hash": "sha256:" + "1" * 64,
                "submission_id": "submission-1",
                "coder_id": "coder-fr-001",
            },
            {
                "registration_id": "registration-2",
                "raw_hash": "sha256:" + "2" * 64,
                "submission_id": "submission-2",
                "coder_id": "coder-fr-002",
            },
        ],
    }
    agreement = dict(identity)
    comparison = {
        **identity,
        "pattern_records": [
            {
                "pattern_id": "pattern-domains",
                "left_coder_id": "coder-fr-001",
                "right_coder_id": "coder-fr-002",
                "item_id": "demo-item-cmt",
                "reference_id": "demo-ann-001",
                "unit_id": None,
                "field": "cmt.target_domain",
                "pattern": "split_with_reference",
                "left_value": "nation",
                "right_value": "hope",
                "reference_status": "available",
                "reference_value": "hope",
                "reference_authority": "accepted",
            },
            {
                "pattern_id": "pattern-qualitative",
                "left_coder_id": "coder-fr-001",
                "right_coder_id": "coder-fr-002",
                "item_id": "demo-item-cmt",
                "reference_id": "demo-ann-001",
                "unit_id": None,
                "field": "cmt.conceptual_mapping",
                "pattern": "reference_unavailable",
                "left_value": "NATION IS A BODY",
                "right_value": "POLITY IS A BODY",
                "reference_status": "not_comparable",
                "reference_value": "NATION IS A DEFENDED BODY",
                "reference_authority": "accepted",
            },
            {
                "pattern_id": "pattern-reference",
                "left_coder_id": "coder-fr-001",
                "right_coder_id": "coder-fr-002",
                "item_id": "demo-item-cmt",
                "reference_id": "demo-ann-001",
                "unit_id": None,
                "field": "cmt.cluster_id",
                "pattern": "both_against_reference",
                "left_value": "cluster-b",
                "right_value": "cluster-b",
                "reference_status": "available",
                "reference_value": "cluster-a",
                "reference_authority": "accepted",
            },
            {
                "pattern_id": "pattern-agreement",
                "left_coder_id": "coder-fr-001",
                "right_coder_id": "coder-fr-002",
                "item_id": "demo-item-cmt",
                "reference_id": "demo-ann-001",
                "unit_id": None,
                "field": "uncertainty",
                "pattern": "reference_unavailable",
                "left_value": "low",
                "right_value": "low",
                "reference_status": "unavailable",
                "reference_value": None,
                "reference_authority": None,
            },
        ],
    }
    sample = {
        "case_id": "demo",
        "source_language": "fr",
        "task_layer": "cmt",
        "items": [
            {
                "item_id": "demo-item-cmt",
                "document_id": "demo-doc-001",
                "sentence_id": "demo-sentence-001",
                "design_roles": ["ambiguous", "high_impact", "provenance_risk"],
                "provenance_risks": ["ocr_uncertainty"],
                "claim_impact": "high",
            }
        ],
    }
    return agreement, comparison, sample


class HumanReliabilityDisagreementTest(unittest.TestCase):
    def test_taxonomy_spans_required_human_dimensions(self) -> None:
        expected = {
            "identification.decision_type": "identification",
            "identification.selected_unit_boundary": "boundary",
            "identification.contextual_meaning": "semantics",
            "cmt.source_domain_primary": "domains",
            "cmt.cluster_id": "clusters",
            "interpretation.sacred_object": "interpretation",
            "interpretation.violence_logic": "violence_obligation",
            "interpretation.obligatory_frame": "violence_obligation",
            "interpretation.agents": "agency_absence",
            "interpretation.absence_decision": "agency_absence",
            "confidence": "confidence",
            "disposition": "scope_disposition",
        }
        self.assertEqual(
            expected,
            {field: category_for_field(field) for field in expected},
        )
        with self.assertRaisesRegex(HumanDisagreementError, "unclassified"):
            category_for_field("unknown.field")

    def test_classifies_splits_and_shared_reference_challenges_neutrally(self) -> None:
        agreement, comparison, sample = upstream_artifacts()

        result = classify_disagreements(agreement, comparison, sample)

        self.assertEqual(3, result["summary"]["total_disagreements"])
        by_pattern = {
            record["agreement_pattern"]: record
            for record in result["disagreements"]
        }
        split = by_pattern["split_with_reference"]
        self.assertEqual("domains", split["category"])
        self.assertEqual("high", split["source_language_risk"]["level"])
        self.assertTrue(split["major_claim_impact"])
        self.assertEqual(
            ["coder-fr-001", "coder-fr-002"],
            [value["coder_id"] for value in split["coder_values"]],
        )
        qualitative = by_pattern["reference_unavailable"]
        self.assertTrue(qualitative["possible_codebook_ambiguity"])
        self.assertEqual("not_comparable", qualitative["reference"]["status"])
        challenge = by_pattern["both_against_reference"]
        self.assertEqual("reference_challenge", challenge["category"])
        self.assertEqual("clusters", challenge["field_category"])
        self.assertIn("shared coder value", challenge["review_question"])
        self.assertNotIn("correct", challenge["review_question"].lower())
        schema = json.loads(
            (
                SOURCE_ROOT / "schemas" / "human-reliability"
                / "disagreement-log-schema.json"
            ).read_text()
        )
        Draft202012Validator(schema).validate(result)

    def test_confidence_delta_must_reach_substantive_threshold(self) -> None:
        agreement, comparison, sample = upstream_artifacts()
        comparison["pattern_records"] = [
            {
                **comparison["pattern_records"][0],
                "pattern_id": "small-confidence-delta",
                "field": "confidence",
                "pattern": "reference_unavailable",
                "left_value": 0.80,
                "right_value": 0.75,
                "reference_status": "unavailable",
                "reference_value": None,
                "reference_authority": None,
            },
            {
                **comparison["pattern_records"][0],
                "pattern_id": "material-confidence-delta",
                "field": "confidence",
                "pattern": "reference_unavailable",
                "left_value": 0.80,
                "right_value": 0.60,
                "reference_status": "unavailable",
                "reference_value": None,
                "reference_authority": None,
            },
        ]

        result = classify_disagreements(agreement, comparison, sample)

        self.assertEqual(1, result["summary"]["total_disagreements"])
        self.assertEqual("confidence", result["disagreements"][0]["category"])
        self.assertEqual(
            "material-confidence-delta",
            result["disagreements"][0]["source_pattern_id"],
        )

    def test_rejects_mismatched_upstream_identity_and_missing_sample_item(self) -> None:
        agreement, comparison, sample = upstream_artifacts()
        comparison["packet_id"] = "another-packet"
        with self.assertRaisesRegex(HumanDisagreementError, "packet_id"):
            classify_disagreements(agreement, comparison, sample)

        agreement, comparison, sample = upstream_artifacts()
        sample["items"] = []
        with self.assertRaisesRegex(HumanDisagreementError, "absent from the sample"):
            classify_disagreements(agreement, comparison, sample)

    def test_compute_writes_schema_valid_json_and_csv_without_changing_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base, "cmt")
            annotated = (
                root / "cases" / "demo" / "corpus" / "annotated"
                / "demo-doc-001_annotated.json"
            )
            before = annotated.read_bytes()
            left = valid_submission(root, "coder-fr-001", "cmt")
            right = valid_submission(root, "coder-fr-002", "cmt")
            right["responses"][0]["cmt_response"]["target_domain"] = "hope"
            for submission in (left, right):
                source = base / f"{submission['coder_id']}.json"
                write_json(source, submission)
                ingest_submission(
                    root, "demo", cohort_path, parse_json_submission(source)
                )
            compute_case_agreement(
                root, "demo", "demo-fr-cmt-cohort", "1.0.0"
            )
            compute_case_reference_comparison(
                root, "demo", "demo-fr-cmt-cohort", "1.0.0"
            )

            result = compute_case_disagreements(
                root, "demo", "demo-fr-cmt-cohort", "1.0.0"
            )

            self.assertEqual(before, annotated.read_bytes())
            schema = json.loads(
                (
                    SOURCE_ROOT / "schemas" / "human-reliability"
                    / "disagreement-log-schema.json"
                ).read_text()
            )
            Draft202012Validator(schema).validate(result)
            output = (
                root / "cases" / "demo" / "quality" / "human-reliability"
                / "comparisons" / "demo-fr-cmt-cohort-1.0.0"
            )
            self.assertTrue((output / "disagreement-log.json").is_file())
            with (output / "disagreement-log.csv").open(
                encoding="utf-8", newline=""
            ) as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(result["disagreements"]), len(rows))
            self.assertGreater(len(rows), 0)
            self.assertTrue(all(row["adjudication_recommended"] == "True" for row in rows))
            self.assertTrue(
                result["input_artifacts"]["sample_manifest"]["source"].endswith(
                    "sample-manifest.json"
                )
            )

    def test_compute_requires_explicit_manifest_when_coordinator_sample_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base, "cmt")
            sample_path = (
                root / "cases" / "demo" / "quality" / "human-reliability"
                / "samples" / "sample-manifest.json"
            )
            held_sample = base / "coordinator-sample.json"
            held_sample.write_bytes(sample_path.read_bytes())
            for coder_id in ("coder-fr-001", "coder-fr-002"):
                source = base / f"{coder_id}.json"
                write_json(source, valid_submission(root, coder_id, "cmt"))
                ingest_submission(
                    root, "demo", cohort_path, parse_json_submission(source)
                )
            compute_case_agreement(
                root, "demo", "demo-fr-cmt-cohort", "1.0.0"
            )
            compute_case_reference_comparison(
                root, "demo", "demo-fr-cmt-cohort", "1.0.0"
            )
            sample_path.unlink()

            with self.assertRaisesRegex(
                HumanDisagreementError, "provide --sample-manifest"
            ):
                compute_case_disagreements(
                    root, "demo", "demo-fr-cmt-cohort", "1.0.0"
                )
            result = compute_case_disagreements(
                root,
                "demo",
                "demo-fr-cmt-cohort",
                "1.0.0",
                sample_manifest_path=held_sample,
            )
            self.assertEqual(
                "coordinator://sample-manifest",
                result["input_artifacts"]["sample_manifest"]["source"],
            )
            tampered = json.loads(held_sample.read_text())
            tampered["items"][0]["claim_impact"] = "high"
            write_json(held_sample, tampered)
            with self.assertRaisesRegex(HumanDisagreementError, "approved hash"):
                compute_case_disagreements(
                    root,
                    "demo",
                    "demo-fr-cmt-cohort",
                    "1.0.0",
                    sample_manifest_path=held_sample,
                )


if __name__ == "__main__":
    unittest.main()
