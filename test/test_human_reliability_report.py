from __future__ import annotations

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
from scripts.human_reliability.generate_report import (
    HumanReliabilityReportError,
    generate_case_report,
    render_markdown,
)
from scripts.human_reliability.ingest_submission import (
    ingest_submission,
    parse_json_submission,
)
from test.test_human_reliability_ingestion import (
    ingestion_root,
    valid_submission,
)
from test.test_human_reliability_packets import write_json


SOURCE_ROOT = Path(__file__).resolve().parents[1]
COHORT_ID = "demo-fr-cmt-cohort"
COHORT_VERSION = "1.0.0"


def ingest_coder(
    root: Path, cohort_path: Path, base: Path, coder_id: str
) -> None:
    source = base / f"{coder_id}.json"
    write_json(source, valid_submission(root, coder_id, "cmt"))
    ingest_submission(
        root, "demo", cohort_path, parse_json_submission(source)
    )


class HumanReliabilityReportTest(unittest.TestCase):
    def test_designed_state_renders_without_claiming_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir))

            report = generate_case_report(
                root,
                "demo",
                COHORT_ID,
                COHORT_VERSION,
                revision="fixture-report-v1",
            )

            self.assertEqual("designed", report["report_state"])
            self.assertEqual("absent", report["execution"]["state"])
            self.assertEqual([], report["agreement_metrics"])
            self.assertIsNone(report["disagreements"]["total_disagreements"])
            rendered = render_markdown(report)
            self.assertIn("No agreement metrics are available", rendered)
            self.assertIn("no empirical reliability claim", rendered)
            self.assertIn("project-wide reliability", rendered.lower())

    def test_partial_state_preserves_incomplete_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base)
            ingest_coder(root, cohort_path, base, "coder-fr-001")

            report = generate_case_report(
                root,
                "demo",
                COHORT_ID,
                COHORT_VERSION,
                revision="fixture-report-v1",
            )

            self.assertEqual("partial", report["report_state"])
            self.assertEqual("partial", report["execution"]["state"])
            self.assertEqual(1, report["execution"]["valid_submission_count"])
            self.assertEqual(
                "not_available",
                report["input_artifacts"]["agreement"]["status"],
            )

    def test_complete_state_reports_separate_analysis_families(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base)
            ingest_coder(root, cohort_path, base, "coder-fr-001")
            second = valid_submission(root, "coder-fr-002", "cmt")
            second["responses"][0]["cmt_response"]["target_domain"] = "hope"
            source = base / "coder-fr-002.json"
            write_json(source, second)
            ingest_submission(
                root, "demo", cohort_path, parse_json_submission(source)
            )
            compute_case_agreement(
                root, "demo", COHORT_ID, COHORT_VERSION
            )
            compute_case_reference_comparison(
                root, "demo", COHORT_ID, COHORT_VERSION
            )
            compute_case_disagreements(
                root, "demo", COHORT_ID, COHORT_VERSION
            )

            report = generate_case_report(
                root,
                "demo",
                COHORT_ID,
                COHORT_VERSION,
                revision="fixture-report-v1",
            )

            self.assertEqual("complete", report["report_state"])
            self.assertGreater(len(report["agreement_metrics"]), 1)
            self.assertGreater(
                report["reference_comparison"]["coder_field_comparisons"][
                    "aligned"
                ],
                0,
            )
            self.assertGreater(
                report["disagreements"]["total_disagreements"], 0
            )
            self.assertEqual("not_started", report["adjudication"]["status"])
            target_metric = next(
                metric
                for metric in report["agreement_metrics"]
                if metric["field"] == "cmt.target_domain"
            )
            self.assertEqual(
                "defined",
                target_metric["statistics"]["observed_agreement"]["status"],
            )
            self.assertIn("cohens_kappa", target_metric["statistics"])
            rendered = render_markdown(report)
            self.assertIn("Human-human agreement by field", rendered)
            self.assertIn("Coder-to-reference comparison", rendered)
            self.assertIn("Adjudication does not replace", rendered)
            self.assertIn("`cmt.target_domain`", rendered)
            self.assertIn("`observed_agreement`", rendered)
            self.assertIn("`cohens_kappa`", rendered)

            schema = json.loads(
                (
                    SOURCE_ROOT
                    / "schemas"
                    / "human-reliability"
                    / "human-reliability-report-schema.json"
                ).read_text(encoding="utf-8")
            )
            Draft202012Validator(
                schema, format_checker=FormatChecker()
            ).validate(report)
            output_root = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "comparisons"
                / f"{COHORT_ID}-{COHORT_VERSION}"
            )
            first_json = (output_root / "human-reliability-report.json").read_bytes()
            first_markdown = (
                output_root / "human-reliability-report.md"
            ).read_bytes()
            generate_case_report(
                root,
                "demo",
                COHORT_ID,
                COHORT_VERSION,
                revision="fixture-report-v1",
            )
            self.assertEqual(
                first_json,
                (output_root / "human-reliability-report.json").read_bytes(),
            )
            self.assertEqual(
                first_markdown,
                (output_root / "human-reliability-report.md").read_bytes(),
            )

    def test_rejects_cross_cohort_analysis_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base)
            for coder_id in ("coder-fr-001", "coder-fr-002"):
                ingest_coder(root, cohort_path, base, coder_id)
            compute_case_agreement(
                root, "demo", COHORT_ID, COHORT_VERSION
            )
            agreement_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "comparisons"
                / f"{COHORT_ID}-{COHORT_VERSION}"
                / "human-agreement.json"
            )
            agreement = json.loads(agreement_path.read_text(encoding="utf-8"))
            agreement["source_language"] = "de"
            write_json(agreement_path, agreement)

            with self.assertRaisesRegex(
                HumanReliabilityReportError, "source_language"
            ):
                generate_case_report(
                    root,
                    "demo",
                    COHORT_ID,
                    COHORT_VERSION,
                    revision="fixture-report-v1",
                )

    def test_rejects_unsafe_output_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _ = ingestion_root(Path(temp_dir))

            with self.assertRaisesRegex(
                HumanReliabilityReportError, "unsafe cohort ID"
            ):
                generate_case_report(
                    root,
                    "demo",
                    "../outside",
                    COHORT_VERSION,
                    revision="fixture-report-v1",
                )

    def test_rejects_manifest_tampering_after_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, cohort_path = ingestion_root(Path(temp_dir))
            cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
            cohort["training_version"] = "tampered-training"
            write_json(cohort_path, cohort)

            with self.assertRaisesRegex(
                HumanReliabilityReportError, "cohort approval"
            ):
                generate_case_report(
                    root,
                    "demo",
                    COHORT_ID,
                    COHORT_VERSION,
                    revision="fixture-report-v1",
                )

    def test_public_markdown_escapes_metadata(self) -> None:
        report = {
            "report_state": "complete",
            "case_id": "<script>alert(1)</script>",
            "source_language": "fr",
            "task_layer": "cmt",
            "cohort_id": "cohort|one`",
            "cohort_version": "1",
            "scope_claim": "<b>unsafe</b>",
            "design": {
                "sample_item_count": 1,
                "required_primary_coders": 2,
                "training_version": "v1",
                "calibration_id": "c1",
                "codebook_version": "b1",
                "blind_independent_coding": True,
                "ai_assistance_allowed": False,
                "sample_execution_status": "executed",
            },
            "execution": {
                "state": "complete",
                "valid_primary_coders": ["a", "b"],
                "valid_submission_count": 2,
                "invalid_submission_count": 0,
            },
            "agreement_metrics": [],
            "reference_comparison": {
                "coder_field_comparisons": {},
                "pair_patterns": {},
            },
            "disagreements": {
                "total_disagreements": 0,
                "major_claim_impact_count": 0,
                "possible_codebook_ambiguity_count": 0,
            },
            "adjudication": {
                "status": "not_started",
                "decision_count": 0,
                "unresolved_count": 0,
                "correction_candidate_count": 0,
            },
            "limitations": ["Scoped."],
        }

        rendered = render_markdown(report)

        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("cohort\\|one&#96;", rendered)
        self.assertNotIn("<b>", rendered)


if __name__ == "__main__":
    unittest.main()
