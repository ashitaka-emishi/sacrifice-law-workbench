from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs" / "reliability" / "human-coder-recruitment-protocol.md"


class HumanCoderRecruitmentProtocolTest(unittest.TestCase):
    def protocol_text(self) -> str:
        return PROTOCOL.read_text(encoding="utf-8")

    def test_protocol_covers_recruitment_acceptance_criteria(self) -> None:
        normalized = " ".join(self.protocol_text().lower().split())

        for phrase in (
            "required background",
            "source-language competence",
            "estimated time",
            "compensation and credit",
            "independence requirements",
            "allowed resources",
            "prohibited resources",
            "what coders receive",
            "what coders return",
            "uncertainty and questions",
            "ai-use restrictions and disclosure",
            "privacy and data handling",
        ):
            self.assertIn(phrase, normalized)

    def test_protocol_states_blind_scope_and_ai_limits(self) -> None:
        normalized = " ".join(self.protocol_text().lower().split())

        for phrase in (
            "blind coding",
            "not adjudication",
            "not model evaluation",
            "ai assistance is prohibited",
            "coders must disclose any ai assistance",
            "pseudonymous coder ids",
        ):
            self.assertIn(phrase, normalized)

    def test_protocol_links_to_required_operational_materials(self) -> None:
        text = self.protocol_text()

        expected_targets = {
            "human-coder-training-guide.md",
            "human-coder-calibration.md",
            "human-coder-submission-contract.md",
            "human-coder-launch-bundles.md",
            "human-submission-ingestion.md",
            "../../cases/lincoln/quality/human-reliability/launch-bundles/lincoln-en-cmt-launch-1.0.0/README.md",
            "../../cases/lincoln/quality/human-reliability/launch-bundles/lincoln-en-cmt-launch-1.0.0/packet/cmt-response-template.csv",
            "../../cases/lincoln/quality/human-reliability/launch-bundles/lincoln-en-cmt-launch-1.0.0/packet/cmt-response-template.json",
        }
        actual_targets = set(re.findall(r"\]\(([^)]+)\)", text))
        self.assertTrue(expected_targets.issubset(actual_targets))

        for target in expected_targets:
            self.assertTrue((PROTOCOL.parent / target).resolve().is_file(), target)


if __name__ == "__main__":
    unittest.main()
