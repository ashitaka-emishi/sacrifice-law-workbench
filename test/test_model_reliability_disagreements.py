from __future__ import annotations

import copy
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.model_reliability.classify_disagreements import (
    DisagreementError,
    category_for_field,
    classify_case_disagreements,
    compute_case_disagreements,
    value_groups,
)
from scripts.model_reliability.compare_runs import compute_case_agreement
from scripts.model_reliability.ingest_submission import (
    ingest_submission,
    parse_json_submission,
)
from test.test_model_reliability_ingestion import FIXTURE_ROOT, ingestion_root


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def disagreement_root(base: Path, include_invalid: bool = False) -> Path:
    root = ingestion_root(base)
    if include_invalid:
        for filename in ("unknown-ids.json", "invalid-field.json"):
            ingest_submission(
                root,
                "demo",
                parse_json_submission(FIXTURE_ROOT / "submissions" / filename),
            )
    normalized = (
        root
        / "cases"
        / "demo"
        / "quality"
        / "model-reliability"
        / "normalized"
        / "normalized-runs.json"
    )
    normalized.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(
        FIXTURE_ROOT / "comparison" / "comparison-inputs.json",
        normalized,
    )
    compute_case_agreement(root, "demo")
    return root


class ModelReliabilityDisagreementTest(unittest.TestCase):
    def test_classifies_fixture_disagreements_and_writes_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = disagreement_root(Path(temp_dir))
            corpus_root = root / "cases" / "demo" / "corpus"
            before = {
                path.relative_to(corpus_root).as_posix(): path.read_bytes()
                for path in corpus_root.rglob("*")
                if path.is_file()
            }

            result = compute_case_disagreements(root, "demo")

            after = {
                path.relative_to(corpus_root).as_posix(): path.read_bytes()
                for path in corpus_root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before, after)
            observed = {
                (record["item_id"], record["field"], record["category"])
                for record in result["disagreements"]
            }
            expected = json.loads(
                (
                    FIXTURE_ROOT / "comparison" / "expected-disagreements.json"
                ).read_text()
            )["expected"]
            for item in expected:
                field = (
                    f"identification.{item['field']}"
                    if item["field"] == "decision"
                    else f"cmt.{item['field']}"
                )
                self.assertIn(
                    (item["item_id"], field, item["classification"]),
                    observed,
                )
            split = next(
                record
                for record in result["disagreements"]
                if record["field"] == "identification.decision"
            )
            self.assertEqual(split["agreement_pattern"], "two-way-split")
            self.assertEqual(
                sorted(group["run_count"] for group in split["value_groups"]),
                [1, 1],
            )
            target = next(
                record
                for record in result["disagreements"]
                if record["field"] == "cmt.target_domain"
            )
            self.assertEqual(target["cluster_id"], "demo-carrying-hope")

            model_root = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "comparisons"
            )
            schema = json.loads(
                (
                    SOURCE_ROOT
                    / "schemas"
                    / "model-reliability"
                    / "disagreement-log-schema.json"
                ).read_text()
            )
            Draft202012Validator(schema).validate(result)
            with (model_root / "disagreement-log.csv").open(
                encoding="utf-8", newline=""
            ) as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), result["summary"]["total_disagreements"])
            self.assertEqual(
                len(
                    {
                        record["disagreement_id"]
                        for record in result["disagreements"]
                    }
                ),
                len(result["disagreements"]),
            )
            for dimension in (
                "by_case",
                "by_language",
                "by_document",
                "by_cluster",
                "by_layer",
                "by_category",
                "by_priority",
            ):
                self.assertEqual(
                    sum(
                        row["disagreement_count"]
                        for row in result["summary"][dimension]
                    ),
                    result["summary"]["total_disagreements"],
                )
            report = (model_root / "instability-report.md").read_text()
            self.assertIn("## Layer instability", report)
            self.assertIn("## Cluster instability", report)
            self.assertIn("Diagnostic stress-test output only", report)

    def test_flags_unanimous_reference_challenge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = disagreement_root(Path(temp_dir))
            model_root = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
            )
            normalized_path = model_root / "normalized" / "normalized-runs.json"
            normalized = json.loads(normalized_path.read_text())
            for run in normalized["runs"]:
                run["items"][1]["target_domain"] = "nation"
            normalized_path.write_text(json.dumps(normalized, indent=2) + "\n")
            compute_case_agreement(root, "demo")

            result = compute_case_disagreements(root, "demo")

            challenges = [
                record
                for record in result["disagreements"]
                if record["unanimous_reference_challenge"]
            ]
            target = next(
                record for record in challenges if record["field"] == "cmt.target_domain"
            )
            self.assertEqual(target["category"], "reference-challenge")
            self.assertEqual(
                target["agreement_pattern"], "unanimous-reference-challenge"
            )
            self.assertEqual(target["review_priority"], "high")
            self.assertEqual(target["reference_value"], "hope")

    def test_three_run_majority_pattern_is_auditable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = disagreement_root(Path(temp_dir))
            model_root = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
            )
            normalized_path = model_root / "normalized" / "normalized-runs.json"
            normalized = json.loads(normalized_path.read_text())
            third = copy.deepcopy(normalized["runs"][0])
            third["run_id"] = "fixture-run-c"
            normalized["runs"].append(third)
            normalized_path.write_text(json.dumps(normalized, indent=2) + "\n")
            compute_case_agreement(root, "demo")

            result = compute_case_disagreements(root, "demo")

            target = next(
                record
                for record in result["disagreements"]
                if record["field"] == "cmt.target_domain"
            )
            self.assertEqual(
                target["agreement_pattern"], "majority-minority-split"
            )
            self.assertEqual(
                sorted(group["run_count"] for group in target["value_groups"]),
                [1, 2],
            )

    def test_coverage_gap_is_not_assumed_to_be_codebook_ambiguity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = disagreement_root(Path(temp_dir))
            model_root = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
            )
            normalized_path = model_root / "normalized" / "normalized-runs.json"
            normalized = json.loads(normalized_path.read_text())
            normalized["runs"][1]["items"] = normalized["runs"][1]["items"][:1]
            normalized_path.write_text(json.dumps(normalized, indent=2) + "\n")
            compute_case_agreement(root, "demo")

            result = compute_case_disagreements(root, "demo")

            target = next(
                record
                for record in result["disagreements"]
                if record["field"] == "cmt.target_domain"
            )
            self.assertEqual(target["agreement_pattern"], "coverage-gap")
            self.assertFalse(target["possible_codebook_ambiguity"])
            self.assertIn("omit", target["review_question"])

    def test_small_unanimous_confidence_delta_is_not_a_reference_challenge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = disagreement_root(Path(temp_dir))
            model_root = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
            )
            normalized_path = model_root / "normalized" / "normalized-runs.json"
            normalized = json.loads(normalized_path.read_text())
            for run in normalized["runs"]:
                run["items"][1]["confidence"] = 0.73
            normalized_path.write_text(json.dumps(normalized, indent=2) + "\n")
            compute_case_agreement(root, "demo")

            result = compute_case_disagreements(root, "demo")

            confidence_challenges = [
                record
                for record in result["disagreements"]
                if record["field"] == "confidence"
                and record["unanimous_reference_challenge"]
            ]
            self.assertEqual(confidence_challenges, [])

    def test_classifies_schema_and_hallucinated_identifier_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = disagreement_root(Path(temp_dir), include_invalid=True)

            result = compute_case_disagreements(root, "demo")

            categories = {record["category"] for record in result["disagreements"]}
            patterns = {
                record["agreement_pattern"] for record in result["disagreements"]
            }
            self.assertIn("hallucination-instability", categories)
            self.assertIn("schema-instability", categories)
            self.assertIn("hallucinated-identifier", patterns)
            invalid = [
                record
                for record in result["disagreements"]
                if record["evidence_source"] == "validation-report"
            ]
            self.assertTrue(invalid)
            self.assertTrue(
                all(record["review_priority"] == "high" for record in invalid)
            )

    def test_taxonomy_covers_required_field_families(self) -> None:
        expectations = {
            "identification.decision": "metaphor-identification-instability",
            "identification.boundary_span": "boundary-instability",
            "identification.contextual_meaning": "context-instability",
            "identification.basic_meaning": "semantic-instability",
            "cmt.source_domain_primary": "domain-instability",
            "cmt.target_domain": "target-domain-instability",
            "cmt.conceptual_metaphor": "semantic-instability",
            "cmt.cluster_id": "cluster-instability",
            "interpretation.functions.violence_logic": "violence-instability",
            "interpretation.functions.obligatory_frame": "obligation-instability",
            "interpretation.agency.agents": "agency-absence-instability",
            "interpretation.absence.status": "agency-absence-instability",
            "confidence": "confidence-instability",
            "uncertainty.status": "context-instability",
        }
        for field, category in expectations.items():
            with self.subTest(field=field):
                self.assertEqual(category_for_field(field), category)

    def test_set_value_groups_ignore_array_order(self) -> None:
        groups = value_groups(
            "interpretation.agency.agents",
            {
                "run-a": ["people", "city"],
                "run-b": ["city", "people"],
                "run-c": ["city"],
            },
        )
        self.assertEqual(
            sorted(group["run_count"] for group in groups),
            [1, 2],
        )

    def test_rejects_stale_agreement_run_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = disagreement_root(Path(temp_dir))
            model_root = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
            )
            normalized = json.loads(
                (model_root / "normalized" / "normalized-runs.json").read_text()
            )
            agreement = json.loads(
                (model_root / "comparisons" / "agreement-results.json").read_text()
            )
            stale = copy.deepcopy(agreement)
            stale["run_ids"] = ["stale-a", "stale-b"]

            with self.assertRaisesRegex(DisagreementError, "run_ids do not match"):
                classify_case_disagreements(root, "demo", normalized, stale)

            wrong_generator = copy.deepcopy(agreement)
            wrong_generator["generator"] = "untrusted-generator"
            with self.assertRaisesRegex(DisagreementError, "comparison stage"):
                classify_case_disagreements(
                    root, "demo", normalized, wrong_generator
                )


if __name__ == "__main__":
    unittest.main()
