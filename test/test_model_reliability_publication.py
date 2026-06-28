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
        self.assertIn(
            "absent or partial cohorts cannot be converted into publication-ready reliability claims",
            normalized_ai_use,
        )

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
        self.assertEqual(
            components["human-reliability-methodology"]["path"],
            "human-reliability-methodology.qmd",
        )
        self.assertEqual(
            components["human-adjudication-results"]["path"],
            "human-adjudication-results.qmd",
        )
        self.assertEqual(
            components["human-reliability-status"]["path"],
            "cases/*/quality/human-reliability/status.json",
        )
        self.assertNotIn(
            "cases/hitler/quality/human-reliability/status.json",
            components["human-reliability-status"]["files"],
        )
        self.assertEqual(
            components["human-reliability-completion"]["path"],
            "docs/reliability/human-reliability-completion-checklist.md",
        )
        limitations = " ".join(manifest["known_limitations"])
        self.assertIn("human inter-annotator reliability", limitations)
        self.assertIn("rights and storage restrictions", limitations)
        self.assertIn("Human agreement, model agreement", limitations)

    def test_human_reliability_claim_gate_scopes_complete_cohorts(self) -> None:
        manifest = json.loads(
            (
                ROOT / "publication" / "audit" / "publication-package.json"
            ).read_text(encoding="utf-8")
        )
        human = manifest["human_reliability"]
        self.assertEqual(
            human["claim_status"], "no-complete-human-reliability-cohorts"
        )
        self.assertEqual(human["complete_cohorts"], [])

        case_statuses = {
            row["case_id"]: row
            for row in human["case_statuses"]
        }
        self.assertEqual(
            set(case_statuses),
            {"am-rev", "fr-rev", "hitler", "lincoln", "napoleon", "wwi-britain"},
        )
        self.assertEqual(case_statuses["lincoln"]["state"], "designed")
        self.assertEqual(case_statuses["lincoln"]["cohort_count"], 1)
        for case_id, row in case_statuses.items():
            if case_id == "lincoln":
                continue
            self.assertEqual(row["state"], "absent")
            self.assertTrue(row["valid"])
            self.assertEqual(row["complete_cohort_count"], 0)
            self.assertEqual(row["unresolved_adjudications"], 0)
        for row in case_statuses.values():
            self.assertTrue(row["valid"])
            self.assertEqual(row["complete_cohort_count"], 0)
            self.assertEqual(row["unresolved_adjudications"], 0)

        audit_package = (ROOT / "publication" / "audit-package.md").read_text(
            encoding="utf-8"
        )
        site_readiness = (
            ROOT / "publication" / "public-site-readiness.md"
        ).read_text(encoding="utf-8")
        validation_gate = (ROOT / "publication" / "validation-gate.md").read_text(
            encoding="utf-8"
        )
        for text in (audit_package, site_readiness):
            normalized = " ".join(text.split())
            self.assertIn("no complete human reliability cohort rows", normalized)
            self.assertIn("case/language/layer/cohort", normalized)
        self.assertIn(
            "Human agreement, model agreement, adjudication, and historical corroboration",
            validation_gate,
        )


if __name__ == "__main__":
    unittest.main()
