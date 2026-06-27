from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
VALIDATOR_PATH = ROOT / "scripts" / "validate-json.py"


def load_validator_module():
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(
        "validate_json_public_site_test",
        VALIDATOR_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PublicSiteContaminationTest(unittest.TestCase):
    def test_all_public_case_ids_have_foreign_identifier_fixtures(self) -> None:
        module = load_validator_module()

        self.assertEqual(
            {"am-rev", "hitler", "lincoln", "napoleon"},
            set(module.PUBLIC_SITE_CASE_IDENTIFIERS),
        )
        for case_id, identifiers in module.PUBLIC_SITE_CASE_IDENTIFIERS.items():
            self.assertIn(case_id, identifiers)
            self.assertGreaterEqual(len(identifiers), 2)

    def test_current_generated_case_pages_do_not_leak_foreign_case_ids(self) -> None:
        module = load_validator_module()
        validator = module.Validator()

        for case_id in module.PUBLIC_SITE_CASE_IDENTIFIERS:
            validator.validate_public_site_case_contamination(case_id)

        self.assertEqual([], validator.errors)

    def test_generated_case_page_foreign_case_id_requires_path_exception(self) -> None:
        module = load_validator_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            case_root = root / "cases" / "am-rev"
            page = case_root / "analysis" / "diachronic-analysis.md"
            page.parent.mkdir(parents=True)
            page.write_text(
                "# Diachronic Analysis: am-rev\n\nLincoln material leaked here.\n",
                encoding="utf-8",
            )

            def temp_case_dir(case_id: str) -> Path:
                return root / "cases" / case_id

            with patch.object(module, "ROOT", root), patch.object(
                module,
                "case_dir",
                side_effect=temp_case_dir,
            ):
                validator = module.Validator()
                validator.validate_public_site_case_contamination("am-rev")

                self.assertEqual(1, len(validator.errors))
                self.assertIn("foreign case identifier `Lincoln`", validator.errors[0])

                with patch.dict(
                    module.PUBLIC_SITE_CONTAMINATION_EXCEPTIONS,
                    {"cases/am-rev/analysis/diachronic-analysis.md": {"Lincoln"}},
                    clear=True,
                ):
                    validator = module.Validator()
                    validator.validate_public_site_case_contamination("am-rev")

                self.assertEqual([], validator.errors)


if __name__ == "__main__":
    unittest.main()
