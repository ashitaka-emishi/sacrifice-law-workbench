from __future__ import annotations

import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.human_reliability.compute_agreement import (
    AgreementError,
    compare_cohort,
    compute_case_agreement,
)
from scripts.human_reliability.ingest_submission import ingest_submission, parse_json_submission
from test.test_human_reliability_ingestion import ingestion_root, valid_submission
from test.test_human_reliability_packets import packet_dir, write_json


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def normalized_runs(submissions: list[dict]) -> dict:
    return {
        "schema_version": "1.0.0",
        "case_id": "demo",
        "runs": [
            {
                "registration_id": f"registration-{index}",
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


def interpretation_submission(root: Path, coder_id: str) -> dict:
    layer = "interpretation"
    template = json.loads(
        (packet_dir(root, layer) / f"{layer}-response-template.json").read_text()
    )
    manifest = json.loads((packet_dir(root, layer) / "packet-manifest.json").read_text())
    template.update(
        {
            "submission_id": f"submission-{coder_id}",
            "cohort_id": "demo-fr-interpretation-cohort",
            "cohort_version": "1.0.0",
            "packet_hash": manifest["packet_hash"],
            "coder_id": coder_id,
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
        }
    )
    response = template["responses"][0]
    response.update(
        {
            "disposition": "coded",
            "confidence": 0.8,
            "uncertainty": "low",
            "uncertainty_note": "Synthetic ambiguity note.",
            "out_of_scope_reason": None,
            "notes": "",
            "interpretation_response": {
                "sacred_object": "present",
                "sacrificial_body": "uncertain",
                "enemy_as_bringer_of_death": "absent",
                "violence_logic": "present",
                "obligatory_frame": "present",
                "purification": "not_applicable",
                "agents": ["the people", "the city"],
                "patients": [],
                "beneficiaries": ["the polity"],
                "excluded_agents": [],
                "absence_decision": "uncertain",
                "absence_scope": "complete sentence",
                "presence_criterion": "explicit or recoverable agency",
                "rival_reading": "Ceremonial convention.",
            },
        }
    )
    return template


def metric(result: dict, field: str) -> dict:
    return next(value for value in result["field_metrics"] if value["field"] == field)


class HumanAgreementTest(unittest.TestCase):
    def test_identification_reports_binary_kappa_boundary_and_sparse_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir), "identification")
            left = valid_submission(root, "coder-fr-001", "identification")
            right = valid_submission(root, "coder-fr-002", "identification")
            left_units = left["responses"][0]["lexical_unit_responses"]
            right_units = right["responses"][0]["lexical_unit_responses"]
            left_units[1]["decision_type"] = "non_metaphor"
            right_units[1]["decision_type"] = "mipvu_direct"
            right_units[1]["boundary_response"] = "expand"

            result = compare_cohort(
                "demo",
                normalized_runs([left, right]),
                "demo-fr-identification-cohort",
                "1.0.0",
            )

            decision = metric(result, "identification.decision_type")
            self.assertAlmostEqual(2 / 3, decision["positive_agreement"]["value"])
            self.assertEqual(0.0, decision["negative_agreement"]["value"])
            self.assertEqual(0.5, decision["observed_agreement"]["value"])
            self.assertAlmostEqual(1 / 3, decision["cohens_kappa"]["value"])
            boundary = metric(result, "identification.selected_unit_boundary")
            self.assertAlmostEqual(0.5, boundary["mean_jaccard"]["value"])
            self.assertEqual("sparse", decision["sample_assessment"])
            self.assertFalse(result["scope"]["pooled"])
            self.assertEqual(1, len(result["coder_pairs"]))
            self.assertEqual(2, len(result["input_runs"]))

    def test_cmt_keeps_nominal_set_numeric_ordinal_and_text_fields_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir), "cmt")
            left = valid_submission(root, "coder-fr-001", "cmt")
            right = valid_submission(root, "coder-fr-002", "cmt")
            right_response = right["responses"][0]
            right_response["cmt_response"]["source_domain_secondary"] = []
            right_response["cmt_response"]["target_domain"] = "hope"
            right_response["confidence"] = 0.5
            right_response["uncertainty"] = "unresolved"
            right_response["cmt_response"]["conceptual_mapping"] = "A different mapping"

            result = compare_cohort(
                "demo",
                normalized_runs([left, right]),
                "demo-fr-cmt-cohort",
                "1.0.0",
            )

            self.assertEqual(
                0.0,
                metric(result, "cmt.target_domain")["observed_agreement"]["value"],
            )
            self.assertEqual(
                0.0,
                metric(result, "cmt.source_domain_secondary")["mean_jaccard"]["value"],
            )
            self.assertAlmostEqual(
                0.3,
                metric(result, "confidence")["mean_absolute_difference"]["value"],
            )
            self.assertEqual(
                "not_applicable",
                metric(result, "confidence")["observed_agreement"]["status"],
            )
            self.assertAlmostEqual(
                2 / 3,
                metric(result, "uncertainty")["mean_ordinal_distance"]["value"],
            )
            text = metric(result, "cmt.conceptual_mapping")
            self.assertEqual("not_applicable", text["observed_agreement"]["status"])
            self.assertIn("qualitative", text["observed_agreement"]["undefined_reason"])

    def test_interpretation_reports_each_function_agency_and_absence_separately(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir), "interpretation")
            left = interpretation_submission(root, "coder-fr-001")
            right = interpretation_submission(root, "coder-fr-002")
            payload = right["responses"][0]["interpretation_response"]
            payload["sacred_object"] = "absent"
            payload["agents"] = ["the city"]
            payload["absence_decision"] = "present"

            result = compare_cohort(
                "demo",
                normalized_runs([left, right]),
                "demo-fr-interpretation-cohort",
                "1.0.0",
            )

            self.assertEqual(
                0.0,
                metric(result, "interpretation.sacred_object")[
                    "observed_agreement"
                ]["value"],
            )
            self.assertEqual(
                0.5,
                metric(result, "interpretation.agents")["mean_jaccard"]["value"],
            )
            self.assertEqual(
                0.0,
                metric(result, "interpretation.absence_decision")[
                    "observed_agreement"
                ]["value"],
            )

    def test_out_of_scope_is_missing_not_empty_set_agreement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir), "cmt")
            left = valid_submission(root, "coder-fr-001", "cmt")
            right = valid_submission(root, "coder-fr-002", "cmt")
            for submission in (left, right):
                response = submission["responses"][0]
                response["disposition"] = "out_of_scope"
                response["confidence"] = None
                response["out_of_scope_reason"] = "missing_context"
                response.pop("cmt_response")

            result = compare_cohort(
                "demo",
                normalized_runs([left, right]),
                "demo-fr-cmt-cohort",
                "1.0.0",
            )

            secondary = metric(result, "cmt.source_domain_secondary")
            self.assertEqual(0, secondary["comparable_count"])
            self.assertEqual(1, secondary["missing_count"])
            self.assertEqual("undefined", secondary["mean_jaccard"]["status"])

    def test_compute_writes_schema_valid_json_and_csv_from_ingested_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base, "cmt")
            for coder_id in ("coder-fr-001", "coder-fr-002"):
                source = base / f"{coder_id}.json"
                write_json(source, valid_submission(root, coder_id, "cmt"))
                ingest_submission(
                    root, "demo", cohort_path, parse_json_submission(source)
                )

            result = compute_case_agreement(
                root, "demo", "demo-fr-cmt-cohort", "1.0.0"
            )

            schema = json.loads(
                (
                    SOURCE_ROOT
                    / "schemas"
                    / "human-reliability"
                    / "agreement-results-schema.json"
                ).read_text()
            )
            Draft202012Validator(schema).validate(result)
            output = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "comparisons"
                / "demo-fr-cmt-cohort-1.0.0"
            )
            self.assertTrue((output / "human-agreement.json").is_file())
            with (output / "human-agreement.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(2 * len(result["field_metrics"]), len(rows))

    def test_rejects_cross_cohort_pooling_duplicate_coders_and_incomplete_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir), "cmt")
            left = valid_submission(root, "coder-fr-001", "cmt")
            right = valid_submission(root, "coder-fr-002", "cmt")
            right["source_language"] = "de"
            with self.assertRaisesRegex(AgreementError, "source_language"):
                compare_cohort(
                    "demo",
                    normalized_runs([left, right]),
                    "demo-fr-cmt-cohort",
                    "1.0.0",
                )
            right["source_language"] = "fr"
            right["coder_id"] = left["coder_id"]
            with self.assertRaisesRegex(AgreementError, "distinct"):
                compare_cohort(
                    "demo",
                    normalized_runs([left, right]),
                    "demo-fr-cmt-cohort",
                    "1.0.0",
                )
            with self.assertRaisesRegex(AgreementError, "at least two"):
                compare_cohort(
                    "demo",
                    normalized_runs([left]),
                    "demo-fr-cmt-cohort",
                    "1.0.0",
                )

    def test_compute_rejects_unsafe_output_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir), "cmt")
            with self.assertRaisesRegex(AgreementError, "unsafe cohort_id"):
                compute_case_agreement(root, "demo", "../submissions", "1.0.0")

    def test_compute_rejects_normalized_submission_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base, "cmt")
            for coder_id in ("coder-fr-001", "coder-fr-002"):
                source = base / f"{coder_id}.json"
                write_json(source, valid_submission(root, coder_id, "cmt"))
                ingest_submission(
                    root, "demo", cohort_path, parse_json_submission(source)
                )
            normalized_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "normalized"
                / "normalized-coder-runs.json"
            )
            normalized = json.loads(normalized_path.read_text())
            normalized["runs"][0]["submission"]["responses"][0]["cmt_response"][
                "target_domain"
            ] = "hope"
            write_json(normalized_path, normalized)

            with self.assertRaisesRegex(AgreementError, "immutable raw submission"):
                compute_case_agreement(
                    root, "demo", "demo-fr-cmt-cohort", "1.0.0"
                )


if __name__ == "__main__":
    unittest.main()
