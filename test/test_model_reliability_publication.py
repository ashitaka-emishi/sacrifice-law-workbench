from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ModelReliabilityPublicationTest(unittest.TestCase):
    def test_publication_package_preserves_authority_boundaries(self) -> None:
        disclosure = (
            ROOT / "publication" / "model-reliability.md"
        ).read_text(encoding="utf-8")
        for phrase in (
            "Accepted annotations",
            "Prior review artifacts",
            "Multi-model stress test",
            "Human reliability study",
            "does not prove scholarly reproducibility",
        ):
            self.assertIn(phrase, disclosure)

        ai_use = (ROOT / "publication" / "ai-use-statement.md").read_text(
            encoding="utf-8"
        )
        normalized_ai_use = " ".join(ai_use.split())
        self.assertIn(
            "are not human inter-annotator reliability",
            normalized_ai_use,
        )
        self.assertIn("do not adjudicate accepted annotations", ai_use)

    def test_publication_package_preserves_rights_boundaries(self) -> None:
        disclosure = (
            ROOT / "publication" / "model-reliability.md"
        ).read_text(encoding="utf-8")
        availability = (
            ROOT / "publication" / "data-availability.md"
        ).read_text(encoding="utf-8")
        for text in (disclosure, availability):
            normalized = " ".join(text.lower().split())
            self.assertIn("raw model responses", normalized)
            self.assertIn("local-only", normalized)
            self.assertIn("short compliant spans", normalized)

    def test_audit_manifest_includes_reliability_disclosure(self) -> None:
        manifest = json.loads(
            (
                ROOT / "publication" / "audit" / "publication-package.json"
            ).read_text(encoding="utf-8")
        )
        components = {
            item["component_id"]: item for item in manifest["components"]
        }
        self.assertEqual(
            components["model-reliability-disclosure"]["path"],
            "publication/model-reliability.md",
        )
        self.assertEqual(
            components["model-reliability-completion"]["path"],
            "docs/reliability/model-reliability-completion-checklist.md",
        )
        limitations = " ".join(manifest["known_limitations"])
        self.assertIn("human inter-annotator reliability", limitations)
        self.assertIn("rights and storage restrictions", limitations)


if __name__ == "__main__":
    unittest.main()
