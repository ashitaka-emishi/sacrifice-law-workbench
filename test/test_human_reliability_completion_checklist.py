from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HumanReliabilityCompletionChecklistTest(unittest.TestCase):
    def test_completion_checklist_covers_required_milestone_gates(self) -> None:
        checklist = (
            ROOT
            / "docs"
            / "reliability"
            / "human-reliability-completion-checklist.md"
        ).read_text(encoding="utf-8")
        normalized = " ".join(checklist.split()).lower()

        for phrase in (
            "training",
            "calibration",
            "sample manifest",
            "at least two qualified independent primary coders",
            "validated and normalized",
            "human-human agreement metrics",
            "human-vs-reference comparison",
            "disagreement logs",
            "adjudication queue",
            "validated adjudication decisions",
            "codebook revision notes",
            "protected-path tests",
            "publication package",
        ):
            self.assertIn(phrase, normalized)

        for command in (
            "npm run status",
            "npm run validate",
            "npm run pipeline",
            "quarto render",
        ):
            self.assertIn(command, checklist)

    def test_completion_checklist_scopes_incomplete_cases_and_claims(self) -> None:
        checklist = (
            ROOT
            / "docs"
            / "reliability"
            / "human-reliability-completion-checklist.md"
        ).read_text(encoding="utf-8")
        normalized = " ".join(checklist.split()).lower()

        self.assertIn("incomplete cases and languages remain draft disclosures", normalized)
        self.assertIn("no complete human reliability cohort rows", normalized)
        self.assertIn("case, language, layer, or cohort", normalized)
        self.assertIn(
            "human agreement, reference comparison, adjudication, model agreement, and historical corroboration",
            normalized,
        )


if __name__ == "__main__":
    unittest.main()
