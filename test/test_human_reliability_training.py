from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "reliability" / "human-coder-training-guide.md"


class HumanCoderTrainingGuideTest(unittest.TestCase):
    def test_guide_covers_required_decision_areas(self) -> None:
        text = GUIDE.read_text(encoding="utf-8").lower()
        for phrase in (
            "blindness and independence",
            "units and context",
            "mipvu identification procedure",
            "lexical and source-span boundaries",
            "cmt mapping procedure",
            "interpretive procedure",
            "violence and obligation",
            "agency coding",
            "absence coding",
            "confidence, ambiguity, and uncertainty",
            "rival readings",
            "out-of-scope protocol",
        ):
            self.assertIn(phrase, text)

    def test_examples_are_synthetic_and_excluded_from_blind_samples(self) -> None:
        text = GUIDE.read_text(encoding="utf-8")
        example_ids = re.findall(r"`(training-synthetic-[a-z]{2}-\d{2})`", text)
        self.assertGreaterEqual(len(set(example_ids)), 10)
        self.assertIn("must never be included in a blind reliability sample", text)
        self.assertIn("contain no historical or restricted source text", text)

    def test_source_language_and_gloss_limits_are_explicit(self) -> None:
        normalized = " ".join(GUIDE.read_text(encoding="utf-8").lower().split())
        self.assertIn("familiarity with an english translation is not source-language competence", normalized)
        self.assertIn("the source sentence and source lexical unit control the decision", normalized)
        self.assertIn("unable to evaluate", normalized)
        self.assertIn("must use `out_of_scope`", normalized)


if __name__ == "__main__":
    unittest.main()
