from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.human_reliability.generate_launch_bundle import (
    LaunchBundleError,
    cohort_hash,
    generate_launch_bundle,
    sha256_bytes,
)


SOURCE_ROOT = Path(__file__).resolve().parents[1]


class HumanCoderLaunchBundleTest(unittest.TestCase):
    def fixture_root(self, base: Path) -> tuple[Path, Path]:
        root = base / "repo"
        shutil.copytree(SOURCE_ROOT, root, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        cohort_path = (
            root
            / "cases"
            / "lincoln"
            / "quality"
            / "human-reliability"
            / "cohorts"
            / "lincoln-en-cmt-launch-1.0.0.json"
        )
        return root, cohort_path

    def test_generates_coder_facing_launch_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, cohort_path = self.fixture_root(Path(temp_dir))
            manifest = generate_launch_bundle(
                root,
                "lincoln",
                cohort_path=cohort_path,
                revision="deadbeef",
            )
            bundle_root = (
                root
                / "cases"
                / "lincoln"
                / "quality"
                / "human-reliability"
                / "launch-bundles"
                / "lincoln-en-cmt-launch-1.0.0"
            )

            expected_files = {
                "README.md",
                "allowed-references.md",
                "calibration-instructions.md",
                "coder-declarations.md",
                "launch-bundle-manifest.json",
                "packet/cmt-packet.jsonl",
                "packet/cmt-response-template.csv",
                "packet/cmt-response-template.json",
                "packet/packet-manifest.json",
                "references/MIPVU_ANNOTATION_GUIDE.md",
                "references/human-coder-submission-contract.md",
                "return-instructions.md",
                "training/human-coder-training-guide.md",
            }
            actual_files = {
                path.relative_to(bundle_root).as_posix()
                for path in bundle_root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(expected_files, actual_files)
            self.assertEqual("lincoln-en-cmt-launch-1.0.0", manifest["bundle_id"])
            self.assertEqual("repository_allowed", manifest["storage_policy"])
            self.assertFalse(manifest["ai_assistance_allowed"])

            readme = (bundle_root / "README.md").read_text(encoding="utf-8")
            declarations = (bundle_root / "coder-declarations.md").read_text(encoding="utf-8")
            allowed = (bundle_root / "allowed-references.md").read_text(encoding="utf-8")
            returns = (bundle_root / "return-instructions.md").read_text(encoding="utf-8")
            combined = "\n".join([readme, declarations, allowed, returns])
            for required in (
                "Estimated time",
                "conflict",
                "Independent completion",
                "AI assistance",
                "source-language competence",
                "accepted annotations",
                "model outputs",
                "adjudication",
                "return the completed response",
                "contact the coordinator",
            ):
                self.assertIn(required.lower(), combined.lower())

            packet_manifest = json.loads((bundle_root / "packet" / "packet-manifest.json").read_text())
            self.assertEqual(packet_manifest["packet_hash"], manifest["packet_hash"])
            bundle_manifest = json.loads((bundle_root / "launch-bundle-manifest.json").read_text())
            rendered_manifest = json.dumps(bundle_manifest)
            self.assertNotIn("quality/human-reliability/cohorts", rendered_manifest)
            self.assertIn("coordinator://cohort-manifest", rendered_manifest)
            unsigned = dict(bundle_manifest)
            expected_hash = unsigned.pop("bundle_hash")
            self.assertEqual(expected_hash, sha256_bytes(json.dumps(
                unsigned,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")))
            for record in bundle_manifest["files"]:
                path = bundle_root / record["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(record["hash"], sha256_bytes(path.read_bytes()))

            packet_text = (bundle_root / "packet" / "cmt-packet.jsonl").read_text(encoding="utf-8")
            for forbidden in (
                "accepted_decision",
                "adjudicated_decision",
                "model_output",
                "support_score",
                "lincoln-01-body-organism",
            ):
                self.assertNotIn(forbidden, packet_text)

    def test_refuses_local_only_storage_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, cohort_path = self.fixture_root(Path(temp_dir))
            cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
            cohort["storage_policy"] = "local_only"
            cohort["approval"]["manifest_sha256"] = cohort_hash(cohort)
            cohort_path.write_text(json.dumps(cohort, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(LaunchBundleError, "repository_allowed"):
                generate_launch_bundle(
                    root,
                    "lincoln",
                    cohort_path=cohort_path,
                    revision="deadbeef",
                )


if __name__ == "__main__":
    unittest.main()
