from __future__ import annotations

import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.human_reliability.compare_references import (
    ReferenceComparisonError,
    compare_references,
    compute_case_reference_comparison,
)
from scripts.human_reliability.ingest_submission import (
    ingest_submission,
    parse_json_submission,
)
from test.test_human_reliability_agreement import interpretation_submission
from test.test_human_reliability_ingestion import ingestion_root, valid_submission
from test.test_human_reliability_packets import write_json


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


def patterns(result: dict) -> set[str]:
    return {record["pattern"] for record in result["pattern_records"]}


class HumanReferenceComparisonTest(unittest.TestCase):
    def test_coder_comparisons_are_separate_from_pair_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir), "cmt")
            left = valid_submission(root, "coder-fr-001", "cmt")
            right = valid_submission(root, "coder-fr-002", "cmt")

            result = compare_references(
                root,
                "demo",
                normalized_runs([left, right]),
                "demo-fr-cmt-cohort",
                "1.0.0",
            )

            self.assertEqual(2, len(result["coder_comparisons"]))
            left_rows = result["coder_comparisons"][0]["comparisons"]
            source = next(
                row for row in left_rows if row["field"] == "cmt.source_domain_primary"
            )
            target = next(
                row for row in left_rows if row["field"] == "cmt.target_domain"
            )
            self.assertEqual("aligned", source["alignment"])
            self.assertEqual("divergent", target["alignment"])
            self.assertIn("both_with_reference", patterns(result))
            self.assertIn("both_against_reference", patterns(result))
            self.assertNotIn("comparison_families", result)
            for record in result["pattern_records"]:
                self.assertTrue(record["item_id"].startswith("demo-item-"))
                self.assertEqual("demo-ann-001", record["reference_id"])

    def test_flags_split_with_reference_split_against_both_and_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir), "cmt")
            left = valid_submission(root, "coder-fr-001", "cmt")
            right = valid_submission(root, "coder-fr-002", "cmt")
            left_payload = left["responses"][0]["cmt_response"]
            right_payload = right["responses"][0]["cmt_response"]
            right_payload["source_domain_primary"] = "body"
            left_payload["target_domain"] = "nation"
            right_payload["target_domain"] = "freedom"
            left_payload["cluster_id"] = "cluster-a"
            right_payload["cluster_id"] = "cluster-b"

            result = compare_references(
                root,
                "demo",
                normalized_runs([left, right]),
                "demo-fr-cmt-cohort",
                "1.0.0",
            )

            self.assertIn("split_with_reference", patterns(result))
            self.assertIn("split_against_both", patterns(result))
            self.assertIn("reference_unavailable", patterns(result))
            flagged = [
                record
                for record in result["pattern_records"]
                if record["pattern"] in {"split_with_reference", "split_against_both"}
            ]
            self.assertTrue(all(record["adjudication_recommended"] for record in flagged))
            self.assertTrue(
                all("correct" not in record["neutral_interpretation"].lower() for record in flagged)
            )

    def test_flags_uncertain_vs_confident_before_reference_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir), "identification")
            left = valid_submission(root, "coder-fr-001", "identification")
            right = valid_submission(root, "coder-fr-002", "identification")
            left["responses"][0]["lexical_unit_responses"][1]["decision_type"] = "uncertain"

            result = compare_references(
                root,
                "demo",
                normalized_runs([left, right]),
                "demo-fr-identification-cohort",
                "1.0.0",
            )

            uncertain = [
                record
                for record in result["pattern_records"]
                if record["pattern"] == "uncertain_vs_confident"
            ]
            self.assertEqual(1, len(uncertain))
            self.assertTrue(uncertain[0]["adjudication_recommended"])

            left["responses"][0]["lexical_unit_responses"][1][
                "decision_type"
            ] = "mipvu_indirect"
            left["responses"][0]["uncertainty"] = "unresolved"
            result = compare_references(
                root,
                "demo",
                normalized_runs([left, right]),
                "demo-fr-identification-cohort",
                "1.0.0",
            )
            uncertainty = [
                record
                for record in result["pattern_records"]
                if record["field"] == "uncertainty"
                and record["pattern"] == "uncertain_vs_confident"
            ]
            self.assertEqual(1, len(uncertainty))

    def test_optional_adjudicated_result_is_compared_but_not_substituted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir), "cmt")
            left = valid_submission(root, "coder-fr-001", "cmt")
            right = valid_submission(root, "coder-fr-002", "cmt")
            adjudicated_response = copy.deepcopy(left["responses"][0])
            adjudicated_response["cmt_response"]["target_domain"] = "hope"
            adjudicated = {
                "adjudication_id": "adjudication-demo-001",
                "cohort_id": "demo-fr-cmt-cohort",
                "cohort_version": "1.0.0",
                "responses": [adjudicated_response],
            }

            result = compare_references(
                root,
                "demo",
                normalized_runs([left, right]),
                "demo-fr-cmt-cohort",
                "1.0.0",
                adjudicated=adjudicated,
            )

            self.assertEqual(2, len(result["coder_comparisons"]))
            self.assertEqual(1, len(result["adjudicated_comparisons"]))
            target = next(
                row
                for row in result["adjudicated_comparisons"][0]["comparisons"]
                if row["field"] == "cmt.target_domain"
            )
            self.assertEqual("aligned", target["alignment"])

    def test_interpretation_boolean_reference_mapping_is_narrow_and_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir), "interpretation")
            left = interpretation_submission(root, "coder-fr-001")
            right = interpretation_submission(root, "coder-fr-002")
            for submission in (left, right):
                response = submission["responses"][0]
                response["source_span_id"] = "demo-ann-001"
                response["interpretation_response"] = {
                    "sacred_object": "uncertain",
                    "sacrificial_body": "uncertain",
                    "enemy_as_bringer_of_death": "uncertain",
                    "violence_logic": "uncertain",
                    "obligatory_frame": "absent",
                    "purification": "uncertain",
                    "agents": [],
                    "patients": [],
                    "beneficiaries": [],
                    "excluded_agents": [],
                    "absence_decision": "uncertain",
                    "absence_scope": "complete sentence",
                    "presence_criterion": "explicit evidence",
                    "rival_reading": "Insufficient context.",
                }

            result = compare_references(
                root,
                "demo",
                normalized_runs([left, right]),
                "demo-fr-interpretation-cohort",
                "1.0.0",
            )

            rows = result["coder_comparisons"][0]["comparisons"]
            obligatory = next(
                row
                for row in rows
                if row["field"] == "interpretation.obligatory_frame"
            )
            sacred = next(
                row for row in rows if row["field"] == "interpretation.sacred_object"
            )
            self.assertEqual("aligned", obligatory["alignment"])
            self.assertEqual("reviewable_reference", obligatory["reference_authority"])
            self.assertEqual("unavailable", sacred["alignment"])

    def test_qualitative_fields_never_become_reference_accuracy_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir), "cmt")
            left = valid_submission(root, "coder-fr-001", "cmt")
            right = valid_submission(root, "coder-fr-002", "cmt")
            right["responses"][0]["cmt_response"][
                "conceptual_mapping"
            ] = "A different free-text mapping"

            result = compare_references(
                root,
                "demo",
                normalized_runs([left, right]),
                "demo-fr-cmt-cohort",
                "1.0.0",
            )

            record = next(
                value
                for value in result["pattern_records"]
                if value["field"] == "cmt.conceptual_mapping"
            )
            self.assertEqual("reference_unavailable", record["pattern"])
            self.assertEqual("not_comparable", record["reference_status"])
            self.assertTrue(record["adjudication_recommended"])

    def test_reference_unavailable_works_with_no_reference_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir), "cmt")
            annotated = (
                root
                / "cases"
                / "demo"
                / "corpus"
                / "annotated"
                / "demo-doc-001_annotated.json"
            )
            annotated.unlink()
            left = valid_submission(root, "coder-fr-001", "cmt")
            right = valid_submission(root, "coder-fr-002", "cmt")

            result = compare_references(
                root,
                "demo",
                normalized_runs([left, right]),
                "demo-fr-cmt-cohort",
                "1.0.0",
            )

            self.assertEqual([], result["reference_sources"])
            self.assertEqual({"reference_unavailable"}, patterns(result))
            schema = json.loads(
                (
                    SOURCE_ROOT
                    / "schemas"
                    / "human-reliability"
                    / "reference-comparison-schema.json"
                ).read_text()
            )
            Draft202012Validator(schema).validate(result)

    def test_sentence_boundary_reference_requires_complete_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir), "identification")
            mipvu_path = (
                root
                / "cases"
                / "demo"
                / "corpus"
                / "mipvu"
                / "demo-doc-001_mipvu.json"
            )
            mipvu = json.loads(mipvu_path.read_text())
            mipvu["lexical_units"][0]["review_status"] = "pending"
            write_json(mipvu_path, mipvu)
            left = valid_submission(root, "coder-fr-001", "identification")
            right = valid_submission(root, "coder-fr-002", "identification")

            result = compare_references(
                root,
                "demo",
                normalized_runs([left, right]),
                "demo-fr-identification-cohort",
                "1.0.0",
            )

            boundary = next(
                record
                for record in result["pattern_records"]
                if record["field"] == "identification.selected_unit_boundary"
            )
            self.assertEqual("reference_unavailable", boundary["pattern"])

    def test_compute_writes_schema_valid_artifacts_without_changing_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base, "cmt")
            annotated = (
                root
                / "cases"
                / "demo"
                / "corpus"
                / "annotated"
                / "demo-doc-001_annotated.json"
            )
            before = annotated.read_bytes()
            for coder_id in ("coder-fr-001", "coder-fr-002"):
                source = base / f"{coder_id}.json"
                write_json(source, valid_submission(root, coder_id, "cmt"))
                ingest_submission(
                    root, "demo", cohort_path, parse_json_submission(source)
                )

            result = compute_case_reference_comparison(
                root, "demo", "demo-fr-cmt-cohort", "1.0.0"
            )

            self.assertEqual(before, annotated.read_bytes())
            schema = json.loads(
                (
                    SOURCE_ROOT
                    / "schemas"
                    / "human-reliability"
                    / "reference-comparison-schema.json"
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
            self.assertTrue((output / "reference-comparison.json").is_file())
            with (output / "reference-patterns.csv").open(
                newline="", encoding="utf-8"
            ) as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(result["pattern_records"]), len(rows))

    def test_rejects_incomplete_ingestion_and_unsafe_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir), "cmt")
            with self.assertRaisesRegex(ReferenceComparisonError, "unsafe cohort_id"):
                compute_case_reference_comparison(
                    root, "demo", "../adjudication", "1.0.0"
                )
            with self.assertRaisesRegex(ReferenceComparisonError, "unable to read JSON"):
                compute_case_reference_comparison(
                    root, "demo", "demo-fr-cmt-cohort", "1.0.0"
                )

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

            with self.assertRaisesRegex(
                ReferenceComparisonError, "immutable raw submission"
            ):
                compute_case_reference_comparison(
                    root, "demo", "demo-fr-cmt-cohort", "1.0.0"
                )


if __name__ == "__main__":
    unittest.main()
