from __future__ import annotations

import copy
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.model_reliability.compare_runs import (
    ComparisonError,
    compare_runs,
    compute_case_agreement,
    iter_summaries,
)
from test.test_model_reliability_ingestion import FIXTURE_ROOT
from test.test_model_reliability_packets import fixture_root


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def comparison_root(base: Path) -> Path:
    root = fixture_root(base)
    target = (
        root
        / "cases"
        / "demo"
        / "quality"
        / "model-reliability"
        / "normalized"
        / "normalized-runs.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(
        FIXTURE_ROOT / "comparison" / "comparison-inputs.json",
        target,
    )
    return root


class ModelReliabilityComparisonTest(unittest.TestCase):
    def test_computes_separate_layered_families(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = comparison_root(Path(temp_dir))
            corpus_root = root / "cases" / "demo" / "corpus"
            before = {
                path.relative_to(corpus_root).as_posix(): path.read_bytes()
                for path in corpus_root.rglob("*")
                if path.is_file()
            }

            result = compute_case_agreement(root, "demo")

            after = {
                path.relative_to(corpus_root).as_posix(): path.read_bytes()
                for path in corpus_root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before, after)
            families = result["comparison_families"]
            self.assertEqual(len(families["model_vs_model"]["pairs"]), 1)
            self.assertEqual(len(families["model_vs_reference"]["runs"]), 2)
            summaries = list(iter_summaries(result))
            requested = {
                (row["comparison_family"], row["task_layer"], row["field"])
                for row in summaries
                if row["document_id"] is None
            }
            for family in ("model_vs_model", "model_vs_reference"):
                self.assertIn(
                    (family, "identification", "identification.decision"),
                    requested,
                )
                self.assertIn(
                    (family, "identification", "identification.boundary_span"),
                    requested,
                )
                self.assertIn((family, "cmt", "cmt.target_domain"), requested)
                self.assertIn(
                    (family, "interpretation", "interpretation.agency.agents"),
                    requested,
                )
                self.assertIn(
                    (family, "interpretation", "interpretation.absence.status"),
                    requested,
                )
                self.assertIn((family, "cmt", "confidence"), requested)
                self.assertIn((family, "cmt", "uncertainty.status"), requested)

            schema = json.loads(
                (
                    SOURCE_ROOT
                    / "schemas"
                    / "model-reliability"
                    / "agreement-results-schema.json"
                ).read_text()
            )
            Draft202012Validator(schema).validate(result)
            csv_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "comparisons"
                / "agreement-summary.csv"
            )
            with csv_path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertGreater(len(rows), 0)
            self.assertEqual(
                {row["comparison_family"] for row in rows},
                {"model_vs_model", "model_vs_reference"},
            )

    def test_fixture_disagreements_and_reference_divergence_are_visible(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = comparison_root(Path(temp_dir))

            result = compute_case_agreement(root, "demo")
            model_rows = result["comparison_families"]["model_vs_model"]["pairs"][0][
                "summaries"
            ]
            aggregate = {
                (row["task_layer"], row["field"]): row
                for row in model_rows
                if row["document_id"] is None
            }

            self.assertEqual(
                aggregate[("identification", "identification.decision")]["metric"][
                    "value"
                ],
                0.0,
            )
            self.assertEqual(
                aggregate[("cmt", "cmt.target_domain")]["metric"]["value"],
                0.0,
            )
            self.assertEqual(
                aggregate[("identification", "identification.boundary_decision")][
                    "metric"
                ]["value"],
                1.0,
            )
            reference_rows = result["comparison_families"]["model_vs_reference"][
                "runs"
            ]
            run_b = next(row for row in reference_rows if row["run_id"] == "fixture-run-b")
            run_b_aggregate = {
                (row["task_layer"], row["field"]): row
                for row in run_b["summaries"]
                if row["document_id"] is None
            }
            self.assertEqual(
                run_b_aggregate[("identification", "identification.decision")][
                    "metric"
                ]["value"],
                0.0,
            )

    def test_sparse_and_degenerate_metrics_are_explicitly_undefined(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = comparison_root(Path(temp_dir))
            normalized = json.loads(
                (
                    FIXTURE_ROOT / "comparison" / "comparison-inputs.json"
                ).read_text()
            )

            result = compare_runs(root, "demo", normalized)
            rows = result["comparison_families"]["model_vs_model"]["pairs"][0][
                "summaries"
            ]
            aggregate = {
                (row["task_layer"], row["field"]): row
                for row in rows
                if row["document_id"] is None
            }
            decision = aggregate[("identification", "identification.decision")]
            self.assertEqual(decision["cohens_kappa"]["status"], "undefined")
            self.assertIn("fewer than two", decision["cohens_kappa"]["undefined_reason"])
            target_domain = aggregate[("cmt", "cmt.target_domain")]
            self.assertEqual(target_domain["cohens_kappa"]["status"], "undefined")
            self.assertIn(
                "not applicable", target_domain["cohens_kappa"]["undefined_reason"]
            )
            agency = aggregate[
                ("interpretation", "interpretation.agency.agents")
            ]
            self.assertEqual(agency["metric"]["status"], "undefined")
            self.assertEqual(agency["comparable_count"], 0)
            self.assertEqual(
                agency["metric"]["undefined_reason"], "no comparable observations"
            )

    def test_jaccard_confidence_and_interpretive_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = comparison_root(Path(temp_dir))
            normalized = json.loads(
                (
                    FIXTURE_ROOT / "comparison" / "comparison-inputs.json"
                ).read_text()
            )
            interpretation = {
                "item_id": "interpretation-item",
                "task_layer": "interpretation",
                "case_id": "demo",
                "document_id": "demo-doc-001",
                "sentence_id": "demo-doc-001_s01_p01_s01",
                "source_language": "fr",
                "interpretation": {
                    "functions": {
                        "sacred_object": "present",
                        "sacrificial_body": "absent",
                        "enemy_as_bringer_of_death": "absent",
                        "violence_logic": "absent",
                        "obligatory_frame": "present",
                        "purification": "absent",
                    },
                    "agency": {
                        "agents": ["city", "people"],
                        "patients": [],
                        "beneficiaries": ["people"],
                        "sacrificial_subjects": [],
                        "excluded_agents": [],
                    },
                    "absence": {
                        "status": "present",
                        "expected_presence": "",
                        "possible_absence": "",
                        "displacement_mechanism": "",
                    },
                },
                "confidence": 0.8,
                "uncertainty": {"status": "low"},
            }
            left = copy.deepcopy(interpretation)
            right = copy.deepcopy(interpretation)
            right["interpretation"]["agency"]["agents"] = ["city"]
            right["interpretation"]["absence"]["status"] = "absent"
            right["confidence"] = 0.5
            normalized["runs"][0]["items"].append(left)
            normalized["runs"][1]["items"].append(right)

            result = compare_runs(root, "demo", normalized)
            rows = result["comparison_families"]["model_vs_model"]["pairs"][0][
                "summaries"
            ]
            aggregate = {
                (row["task_layer"], row["field"]): row
                for row in rows
                if row["document_id"] is None
            }
            self.assertEqual(
                aggregate[("interpretation", "interpretation.agency.agents")][
                    "metric"
                ]["value"],
                0.5,
            )
            self.assertEqual(
                aggregate[("interpretation", "interpretation.absence.status")][
                    "metric"
                ]["value"],
                0.0,
            )
            self.assertAlmostEqual(
                aggregate[("interpretation", "confidence")]["metric"]["value"],
                0.3,
            )

    def test_accepts_ingestion_normalized_run_wrappers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = comparison_root(Path(temp_dir))
            fixture = json.loads(
                (
                    FIXTURE_ROOT / "comparison" / "comparison-inputs.json"
                ).read_text()
            )
            normalized = {
                "schema_version": "1.0.0",
                "case_id": "demo",
                "runs": [
                    {
                        "registration_id": f"registration-{index}",
                        "registered_at": "2026-06-18T12:00:00Z",
                        "raw_hash": "sha256:" + str(index) * 64,
                        "submission": {
                            "case_id": "demo",
                            "source_language": run["source_language"],
                            "run": {"run_id": run["run_id"]},
                            "items": run["items"],
                        },
                    }
                    for index, run in enumerate(fixture["runs"], start=1)
                ],
            }

            result = compare_runs(root, "demo", normalized)

            self.assertEqual(result["run_ids"], ["fixture-run-a", "fixture-run-b"])

    def test_set_exact_matches_ignore_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = comparison_root(Path(temp_dir))
            normalized = json.loads(
                (
                    FIXTURE_ROOT / "comparison" / "comparison-inputs.json"
                ).read_text()
            )
            for run in normalized["runs"]:
                run["items"][1]["source_domain_secondary"] = ["motion", "burden"]
            normalized["runs"][1]["items"][1]["source_domain_secondary"].reverse()

            result = compare_runs(root, "demo", normalized)
            rows = result["comparison_families"]["model_vs_model"]["pairs"][0][
                "summaries"
            ]
            summary = next(
                row
                for row in rows
                if row["document_id"] is None
                and row["field"] == "cmt.source_domain_secondary"
            )
            self.assertEqual(summary["metric"]["value"], 1.0)
            self.assertEqual(summary["exact_match_count"], 1)

    def test_boundary_overlap_uses_character_spans(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = comparison_root(Path(temp_dir))
            normalized = {
                "schema_version": "1.0.0",
                "case_id": "demo",
                "runs": [],
            }
            for run_id, proposed_end in (("run-a", 13), ("run-b", 15)):
                normalized["runs"].append(
                    {
                        "run_id": run_id,
                        "case_id": "demo",
                        "source_language": "fr",
                        "items": [
                            {
                                "item_id": "identification-item",
                                "task_layer": "identification",
                                "case_id": "demo",
                                "document_id": "demo-doc-001",
                                "sentence_id": "demo-doc-001_s01_p01_s01",
                                "source_language": "fr",
                                "lexical_units": [
                                    {
                                        "lexical_unit_id": "demo-doc-001_s01_p01_s01_lu002",
                                        "decision": "mipvu_indirect",
                                        "boundary_decision": (
                                            "exact" if proposed_end == 13 else "expand"
                                        ),
                                        "char_offset_start": 8,
                                        "char_offset_end": 13,
                                        "proposed_char_offset_start": 8,
                                        "proposed_char_offset_end": proposed_end,
                                    }
                                ],
                                "confidence": 0.8,
                                "uncertainty": {"status": "low"},
                            }
                        ],
                    }
                )

            result = compare_runs(root, "demo", normalized)
            rows = result["comparison_families"]["model_vs_model"]["pairs"][0][
                "summaries"
            ]
            summary = next(
                row
                for row in rows
                if row["document_id"] is None
                and row["field"] == "identification.boundary_span"
            )
            self.assertAlmostEqual(summary["metric"]["value"], 5 / 7)
            self.assertEqual(summary["metric"]["name"], "jaccard_overlap")

    def test_rejects_cross_language_pooling_and_single_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = comparison_root(Path(temp_dir))
            normalized = json.loads(
                (
                    FIXTURE_ROOT / "comparison" / "comparison-inputs.json"
                ).read_text()
            )
            one_run = copy.deepcopy(normalized)
            one_run["runs"] = one_run["runs"][:1]
            with self.assertRaisesRegex(ComparisonError, "at least two"):
                compare_runs(root, "demo", one_run)

            mixed = copy.deepcopy(normalized)
            mixed["runs"][1]["source_language"] = "en"
            with self.assertRaisesRegex(ComparisonError, "separate cohorts"):
                compare_runs(root, "demo", mixed)


if __name__ == "__main__":
    unittest.main()
