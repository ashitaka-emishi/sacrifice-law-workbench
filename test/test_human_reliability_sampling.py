from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
STRATEGY = ROOT / "docs" / "reliability" / "human-reliability-sampling-strategy.md"
TEMPLATE = ROOT / "docs" / "reliability" / "sampling" / "sample-manifest-template.json"
SCHEMA = ROOT / "schemas" / "human-reliability" / "sample-manifest-schema.json"
LINCOLN_SAMPLE = ROOT / "cases" / "lincoln" / "quality" / "reliability-sample.json"


class HumanReliabilitySamplingTest(unittest.TestCase):
    def test_template_conforms_to_sample_manifest_schema(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(template)

    def test_strategy_covers_required_stratification_and_controls(self) -> None:
        text = STRATEGY.read_text(encoding="utf-8").lower()
        for phrase in (
            "source languages",
            "phase and genre/register",
            "ordinary negative controls",
            "ambiguous items",
            "provenance risk",
            "high-impact items",
            "qualified independent coders",
            "planned_not_executable",
        ):
            self.assertIn(phrase, text)

    def test_strategy_declares_layer_specific_sample_floors(self) -> None:
        normalized = " ".join(STRATEGY.read_text(encoding="utf-8").lower().split())
        self.assertIn("at least 400 lexical units", normalized)
        self.assertIn("at least 30 complete sentences", normalized)
        self.assertGreaterEqual(normalized.count("target at least 60 items"), 2)
        self.assertIn("do not use this sample to estimate corpus metaphor prevalence", normalized)
        self.assertIn("about 2.5 percentage points", normalized)
        self.assertIn("sentence-aware uncertainty", normalized)

    def test_lincoln_legacy_sample_is_preserved_and_exposure_is_addressed(self) -> None:
        legacy = json.loads(LINCOLN_SAMPLE.read_text(encoding="utf-8"))
        legacy_ids = {
            item["sentence_id"]
            for item in legacy["reliability_sample"]["sampled_sentences"]
        }
        self.assertEqual(7, len(legacy_ids))
        text = STRATEGY.read_text(encoding="utf-8")
        self.assertIn("lincoln-reliability-v1", text)
        self.assertIn("legacy_continuity_reserve", text)
        self.assertIn("prior_public_answer_exposure_risk", text)
        self.assertIn("seven IDs", text)

    def test_manifest_roles_are_coordinator_only(self) -> None:
        text = STRATEGY.read_text(encoding="utf-8").lower()
        normalized = " ".join(text.split())
        self.assertIn("access-controlled coordinator manifest", text)
        self.assertIn("roles never enter coder-facing files", text)
        self.assertIn("until both independent submissions are frozen", normalized)
        template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        self.assertIn("design_roles", template["items"][0])


if __name__ == "__main__":
    unittest.main()
