from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CALIBRATION = ROOT / "docs" / "reliability" / "calibration"
GUIDE = ROOT / "docs" / "reliability" / "human-coder-calibration.md"
LANGUAGES = ("en", "fr", "de")


class HumanCoderCalibrationTest(unittest.TestCase):
    def test_each_language_has_separate_packet_and_key(self) -> None:
        for language in LANGUAGES:
            packet = CALIBRATION / "packets" / f"{language}.md"
            key = CALIBRATION / "answer-keys" / f"{language}.md"
            self.assertTrue(packet.is_file(), packet)
            self.assertTrue(key.is_file(), key)
            packet_text = packet.read_text(encoding="utf-8")
            key_text = key.read_text(encoding="utf-8")
            self.assertNotIn("design role", packet_text.lower())
            packet_ids = set(re.findall(r"calibration-synthetic-[a-z]{2}-\d{2}", packet_text))
            key_ids = set(re.findall(r"calibration-synthetic-[a-z]{2}-\d{2}", key_text))
            self.assertEqual(packet_ids, key_ids)

    def test_each_packet_has_six_unique_synthetic_items(self) -> None:
        all_ids: list[str] = []
        for language in LANGUAGES:
            text = (CALIBRATION / "packets" / f"{language}.md").read_text(encoding="utf-8")
            ids = re.findall(r"`(calibration-synthetic-[a-z]{2}-\d{2})`", text)
            self.assertEqual(6, len(ids), language)
            self.assertEqual(6, len(set(ids)), language)
            self.assertTrue(all(f"-{language}-" in item_id for item_id in ids))
            all_ids.extend(ids)
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_keys_cover_required_design_roles(self) -> None:
        required_by_language = {
            "en": ("positive", "negative", "ambiguous", "cmt", "interpret", "agency", "absence"),
            "fr": ("positive", "négatif", "ambiguë", "cmt", "interprétation", "agentivité", "absence"),
            "de": ("positive", "negative", "mehrdeutige", "cmt", "interpretation", "agency", "absenz"),
        }
        for language in LANGUAGES:
            normalized = (
                CALIBRATION / "answer-keys" / f"{language}.md"
            ).read_text(encoding="utf-8").lower()
            for concept in required_by_language[language]:
                self.assertIn(concept, normalized, f"{language}: {concept}")

    def test_guide_forbids_contamination_and_requires_completion_record(self) -> None:
        normalized = " ".join(GUIDE.read_text(encoding="utf-8").lower().split())
        self.assertIn("must never enter a reliability sample", normalized)
        self.assertIn("store keys away from coder-facing packet distribution", normalized)
        self.assertIn("completion-register.json", normalized)
        self.assertIn("remediation_required", normalized)

    def test_completion_register_template_records_release_controls(self) -> None:
        template = json.loads(
            (CALIBRATION / "completion-register-template.json").read_text(encoding="utf-8")
        )
        attempt = template["attempts"][0]
        self.assertTrue(attempt["independent_first_pass_attested"])
        self.assertTrue(attempt["answer_key_withheld_until_first_pass"])
        self.assertIn("qualification_decision", attempt)
        self.assertIn("critical_controls_passed", attempt)
        self.assertIn("remediation", attempt)
        self.assertEqual(
            {
                "pending",
                "qualified",
                "remediation_required",
                "not_qualified",
            },
            set(template["allowed_qualification_decisions"]),
        )


if __name__ == "__main__":
    unittest.main()
