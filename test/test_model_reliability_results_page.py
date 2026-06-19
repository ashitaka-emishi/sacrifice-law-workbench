from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.model_reliability.generate_results_page import (
    generate_results_page,
    render_results_page,
)
from test.test_model_reliability_ingestion import (
    ingestion_root,
    valid_submission,
)
from test.test_model_reliability_packets import write_json
from scripts.model_reliability.ingest_submission import (
    ingest_submission,
    parse_json_submission,
)
from scripts.model_reliability.pipeline import run_pipeline


class ModelReliabilityResultsPageTest(unittest.TestCase):
    def test_designed_state_renders_before_submissions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = ingestion_root(Path(temp_dir))
            output = Path(temp_dir) / "results.qmd"

            generate_results_page(root, output)

            rendered = output.read_text(encoding="utf-8")
            generate_results_page(root, output)
            self.assertEqual(output.read_text(encoding="utf-8"), rendered)
            self.assertIn("Designed but not executed", rendered)
            self.assertIn("designed — not executed", rendered)
            for layer in ("identification", "cmt", "interpretation"):
                self.assertIn(f"| {layer} | designed", rendered)
            self.assertIn(
                "No validated model-to-model field results are available",
                rendered,
            )
            self.assertIn("Consensus is not adjudication", rendered)

    def test_complete_state_renders_separate_field_families(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = ingestion_root(Path(temp_dir))
            for suffix in ("results-a", "results-b"):
                path = Path(temp_dir) / f"{suffix}.json"
                write_json(path, valid_submission(root, suffix))
                ingest_submission(
                    root, "demo", parse_json_submission(path)
                )
            run_pipeline(root, "demo", revision="fixture-revision-v1")
            output = Path(temp_dir) / "results.qmd"

            generate_results_page(root, output)

            rendered = output.read_text(encoding="utf-8")
            self.assertIn("| cmt | complete | 2 |", rendered)
            self.assertIn("## Model-to-model field stability", rendered)
            self.assertIn("## Model-to-reference field divergence", rendered)
            self.assertIn("`cmt.source_domain_primary`", rendered)
            self.assertIn("human-only decision authority", rendered)
            self.assertNotIn("Designed but not executed", rendered)

    def test_empty_case_list_remains_honest(self) -> None:
        rendered = render_results_page([])
        self.assertIn("No cases discovered", rendered)
        self.assertIn("not evidence of agreement or reproducibility", rendered)

    def test_run_metadata_is_escaped_for_public_markdown(self) -> None:
        summary = {
            "case_id": "demo",
            "source_language": "en",
            "task_layer": "cmt",
            "field": "cmt.target_domain",
            "left_id": "<script>alert(1)</script>",
            "right_id": "run|two`",
            "document_id": None,
            "comparable_count": 1,
            "metric": {
                "name": "observed_agreement",
                "status": "defined",
                "value": 1,
                "undefined_reason": None,
            },
            "cohens_kappa": {
                "status": "undefined",
                "value": None,
                "undefined_reason": "degenerate categories",
            },
        }
        rendered = render_results_page(
            [
                {
                    "case_id": "demo",
                    "status": {
                        "state": "complete",
                        "counts": {"valid_runs": 2},
                        "warnings": [],
                    },
                    "model_summaries": [summary],
                    "reference_summaries": [],
                    "report": None,
                }
            ]
        )
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("run\\|two&#96;", rendered)
        self.assertIn("undefined: degenerate categories", rendered)


if __name__ == "__main__":
    unittest.main()
