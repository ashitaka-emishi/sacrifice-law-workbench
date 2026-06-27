from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build-corpus-analysis.py"


def load_module():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("build_corpus_analysis", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load build-corpus-analysis.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BuildCorpusAnalysisTest(unittest.TestCase):
    def test_diachronic_notes_are_case_local(self) -> None:
        module = load_module()
        timeline = [
            {
                "document_date": "1805-12-10",
                "period": "imperial-campaign",
                "register": "bulletin",
                "document_id": "napoleon-austerlitz",
                "mapping_id": "napoleon-cmt-001",
                "cluster_id": "napoleon-02-army-body",
                "conceptual_metaphor": "ARMY IS SACRIFICE",
                "rhetorical_salience": "high",
            },
            {
                "document_date": "1807-02-09",
                "period": "imperial-campaign",
                "register": "bulletin",
                "document_id": "napoleon-eylau",
                "mapping_id": "napoleon-cmt-011",
                "cluster_id": "napoleon-05-soldier-sacrifice",
                "conceptual_metaphor": "WAR DEATH IS SACRIFICE",
                "rhetorical_salience": "high",
            },
        ]

        rendered = module.build_diachronic_markdown(
            "napoleon", "2026-06-27T00:00:00", timeline
        )
        classifications = module.diachronic_classification(timeline)

        self.assertIn("case-local MIPVU evidence", rendered)
        self.assertIn("napoleon-02-army-body", rendered)
        self.assertIn("napoleon-05-soldier-sacrifice", rendered)
        self.assertIn("ARMY IS SACRIFICE", rendered)
        self.assertNotIn("reviewed Lincoln", rendered)
        self.assertNotIn("lincoln-01-body-organism", rendered)
        self.assertEqual(
            classifications["napoleon-02-army-body"],
            "localized in current evidence; 1 high-salience mapping(s)",
        )


if __name__ == "__main__":
    unittest.main()
