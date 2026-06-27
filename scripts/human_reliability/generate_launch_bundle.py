#!/usr/bin/env python3
"""Generate coder-facing launch bundles for approved human cohorts."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from scripts.human_reliability.boundaries import protect_accepted_artifacts, safe_output_path
except ModuleNotFoundError:
    from boundaries import protect_accepted_artifacts, safe_output_path  # type: ignore


ROOT = Path(__file__).resolve().parents[2]
GENERATOR_VERSION = "1.0.0"
GENERATOR_PATH = "scripts/human_reliability/generate_launch_bundle.py"
DOC_PATHS = {
    "training/human-coder-training-guide.md": Path("docs/reliability/human-coder-training-guide.md"),
    "references/MIPVU_ANNOTATION_GUIDE.md": Path("MIPVU_ANNOTATION_GUIDE.md"),
    "references/human-coder-submission-contract.md": Path("docs/reliability/human-coder-submission-contract.md"),
}
PROHIBITED_BUNDLE_PATH_PARTS = {
    "accepted",
    "adjudication",
    "answer-keys",
    "model-reliability",
    "normalized",
    "submissions",
}
PROHIBITED_BUNDLE_TEXT = (
    "accepted_decision",
    "adjudicated_decision",
    "model_output",
    "support_score",
)


class LaunchBundleError(ValueError):
    """Raised when a coder launch bundle cannot be safely generated."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def hash_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LaunchBundleError(f"required input not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LaunchBundleError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LaunchBundleError(f"expected an object in {path}")
    return value


def write_if_changed(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def relative_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise LaunchBundleError(f"path escapes repository root: {path}") from exc


def case_relative_path(case_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(case_root.resolve()).as_posix()
    except ValueError as exc:
        raise LaunchBundleError(f"path escapes case root: {path}") from exc


def code_revision(root: Path) -> str:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", GENERATOR_PATH],
        cwd=root, check=True, capture_output=True, text=True,
    )
    revision = result.stdout.strip()
    if not revision:
        raise LaunchBundleError(f"generator has no committed revision: {GENERATOR_PATH}")
    return revision


def cohort_hash(cohort: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(cohort))
    approval = payload.get("approval")
    if isinstance(approval, dict):
        approval["manifest_sha256"] = None
    return sha256_bytes(canonical_json_bytes(payload))


def validate_packet_manifest(case_root: Path, packet_manifest: Mapping[str, Any]) -> None:
    unsigned = dict(packet_manifest)
    expected_hash = unsigned.pop("packet_hash", None)
    if expected_hash != sha256_bytes(canonical_json_bytes(unsigned)):
        raise LaunchBundleError("packet manifest hash does not match manifest content")
    for payload in packet_manifest.get("payloads", []):
        if not isinstance(payload, Mapping):
            raise LaunchBundleError("packet manifest payload must be an object")
        path = case_root / str(payload.get("path") or "")
        if not path.is_file():
            raise LaunchBundleError(f"packet payload is missing: {path}")
        if hash_file(path) != payload.get("hash"):
            raise LaunchBundleError(f"packet payload hash mismatch: {path}")


def validate_cohort(cohort: Mapping[str, Any], packet_manifest: Mapping[str, Any]) -> None:
    approval = cohort.get("approval")
    if not isinstance(approval, Mapping) or approval.get("manifest_sha256") != cohort_hash(cohort):
        raise LaunchBundleError("cohort approval.manifest_sha256 does not match canonical cohort content")
    if cohort.get("status") != "approved":
        raise LaunchBundleError("cohort must be approved")
    if cohort.get("storage_policy") != "repository_allowed":
        raise LaunchBundleError("coder launch bundle requires repository_allowed storage_policy")
    if cohort.get("ai_assistance_allowed") is not False:
        raise LaunchBundleError("coder launch bundle currently supports independent unaided cohorts only")
    for field in ("case_id", "sample_id", "sample_version", "packet_id", "source_language", "task_layer"):
        if cohort.get(field) != packet_manifest.get(field):
            raise LaunchBundleError(f"cohort `{field}` does not match packet manifest")
    if sorted(cohort.get("rights_constraints", [])) != sorted(packet_manifest.get("rights_constraints", [])):
        raise LaunchBundleError("cohort rights constraints do not match packet manifest")


def assert_safe_bundle_member(path: str) -> None:
    normalized = path.replace("\\", "/")
    parts = {part.lower() for part in normalized.split("/") if part}
    leaked = sorted(parts.intersection(PROHIBITED_BUNDLE_PATH_PARTS))
    if leaked:
        raise LaunchBundleError(f"bundle member path is not coder-facing: {path}")


def assert_safe_text(path: str, data: bytes) -> None:
    try:
        text = data.decode("utf-8").lower()
    except UnicodeDecodeError:
        return
    leaked = [needle for needle in PROHIBITED_BUNDLE_TEXT if needle in text]
    if leaked:
        raise LaunchBundleError(f"bundle member `{path}` contains prohibited text: {', '.join(leaked)}")


def file_record(bundle_root: Path, path: Path) -> dict[str, str]:
    return {
        "path": path.relative_to(bundle_root).as_posix(),
        "hash": hash_file(path),
    }


def render_readme(cohort: Mapping[str, Any], packet_manifest: Mapping[str, Any]) -> str:
    required_coders = int(cohort.get("required_primary_coders") or 2)
    source_language = str(cohort["source_language"])
    task_layer = str(cohort["task_layer"])
    packet_hash = str(packet_manifest["packet_hash"])
    rights = ", ".join(str(value) for value in cohort.get("rights_constraints", []))
    return f"""# Human Coder Launch Bundle

Bundle: `{cohort["cohort_id"]}` `{cohort["cohort_version"]}`
Case: `{cohort["case_id"]}`
Task layer: `{task_layer}`
Source language: `{source_language}`
Packet: `{cohort["packet_id"]}`
Packet hash: `{packet_hash}`
Required primary coders: `{required_coders}`
Estimated time: 60-90 minutes after training and calibration are complete.

## Task Overview

You are being asked to complete an independent blind human coding packet for
the declared task layer. Code only the assigned items in `packet/`, using the
training and reference materials included in this bundle. The packet contains
source-language text, stable IDs, lexical units, context scope, rights
constraints, and blank response templates.

## What To Return

Return one completed response file in either CSV or JSON format:

- `packet/{task_layer}-response-template.csv`
- `packet/{task_layer}-response-template.json`

Copy the packet hash above into the completed submission before returning it.
Keep all item IDs, sentence IDs, lexical-unit IDs, and metadata fields intact.

## Included Files

- `packet/{task_layer}-packet.jsonl`: blind coding items.
- `packet/{task_layer}-response-template.csv`: spreadsheet response template.
- `packet/{task_layer}-response-template.json`: structured response template.
- `packet/packet-manifest.json`: packet identity, payload hashes, and rights metadata.
- `training/human-coder-training-guide.md`: required training guide copy.
- `calibration-instructions.md`: source-language calibration requirements.
- `coder-declarations.md`: required declarations to complete before return.
- `allowed-references.md`: allowed and prohibited materials.
- `return-instructions.md`: return and escalation procedure.

## Rights And Storage

This bundle was generated only because the approved cohort storage policy is
`repository_allowed`. Its packet rights constraints are: {rights}.

Do not redistribute packet text or completed responses beyond the assigned
coordinator channel. Do not upload packet text to external services.
"""


def render_calibration(cohort: Mapping[str, Any]) -> str:
    return f"""# Calibration Instructions

Complete the required training guide before calibration.

Assigned calibration ID: `{cohort["calibration_id"]}`
Training version: `{cohort["training_version"]}`
Source language: `{cohort["source_language"]}`
Task layer: `{cohort["task_layer"]}`

Use only the coder-facing calibration packet supplied by the coordinator for
your declared source language. Do not request, inspect, or search for
coordinator-held calibration keys. Calibration confirms readiness for this
cohort; calibration responses are not part of the blind reliability sample.

The coordinator must register completion and qualification before releasing or
accepting this study packet as a valid primary-coder submission.
"""


def render_declarations(cohort: Mapping[str, Any]) -> str:
    return f"""# Coder Declarations

Complete these declarations before returning your submission.

- Coder ID: ______________________________
- Source-language competence for `{cohort["source_language"]}`: yes / no
- Training version `{cohort["training_version"]}` completed: yes / no
- Calibration `{cohort["calibration_id"]}` completed: yes / no
- Conflict of interest: none / disclosed below
- Conflict details: ______________________________
- Independent completion: yes / no
- AI assistance used for study decisions: no / yes, disclosed below
- AI-assistance details, if any: ______________________________

By returning a completed packet, you attest that you did not inspect accepted
annotations, model outputs, prior coder submissions, adjudication artifacts,
synthesis claims, coordinator sample roles, or answer keys while coding this
packet.
"""


def render_allowed_references(cohort: Mapping[str, Any]) -> str:
    return f"""# Allowed References And Prohibited Materials

## Allowed

- Materials included in this launch bundle.
- The cohort-authorized codebook and controlled vocabulary.
- Lawful dictionaries, lexicons, grammar references, and neutral historical
  context needed for `{cohort["source_language"]}` source-language reading.
- Coordinator-approved source access instructions and rights/storage notes.

## Prohibited

- Accepted annotations or answer labels.
- Model outputs, model packets, disagreement reports, or consensus summaries.
- Prior coder submissions, agreement results, or completion status.
- Adjudication queues, adjudication decisions, or adjudication notes.
- Synthesis claims, support scores, claim-impact labels, or hidden sample roles.
- Repository history, filenames, comments, or internal audit material that
  reveals expected answers.
- AI-generated, AI-revised, or AI-checked study decisions unless the coordinator
  explicitly reclassifies the cohort as assisted coding.

If accidental exposure occurs, stop coding and report it through the
coordinator channel before continuing.
"""


def render_return_instructions() -> str:
    return """# Return Instructions

1. Complete the response template independently.
2. Preserve all stable IDs and metadata fields.
3. Copy the packet manifest hash into `packet_hash`.
4. Complete the coder declarations.
5. Return the completed response and declarations through the assigned
   coordinator channel.

For technical problems, rights/access questions, uncertainty about allowed
references, or accidental exposure, stop coding and contact the coordinator
through the assigned recruitment or study channel. Do not use public repository
issues or pull requests for item-level questions.
"""


@protect_accepted_artifacts
def generate_launch_bundle(
    root: Path,
    case_id: str,
    *,
    cohort_path: Path,
    revision: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    case_root = root / "cases" / case_id
    if not case_root.is_dir():
        raise LaunchBundleError(f"unknown case `{case_id}`")
    cohort_path = cohort_path.resolve()
    cohort = read_json(cohort_path)
    if cohort.get("case_id") != case_id:
        raise LaunchBundleError("cohort case_id does not match requested case")
    packet_manifest_path = case_root / str(cohort.get("packet_manifest") or "")
    packet_manifest = read_json(packet_manifest_path)
    validate_packet_manifest(case_root, packet_manifest)
    validate_cohort(cohort, packet_manifest)

    bundle_id = f"{cohort['cohort_id']}-{cohort['cohort_version']}"
    bundle_root = safe_output_path(case_root, f"quality/human-reliability/launch-bundles/{bundle_id}")
    copied_files: list[Path] = []

    packet_dir = bundle_root / "packet"
    for payload in packet_manifest.get("payloads", []):
        source = case_root / str(payload["path"])
        destination = packet_dir / source.name
        assert_safe_bundle_member(destination.relative_to(bundle_root).as_posix())
        data = source.read_bytes()
        assert_safe_text(destination.relative_to(bundle_root).as_posix(), data)
        write_if_changed(destination, data)
        copied_files.append(destination)
    manifest_destination = packet_dir / "packet-manifest.json"
    manifest_bytes = json.dumps(packet_manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    write_if_changed(manifest_destination, manifest_bytes)
    copied_files.append(manifest_destination)

    for bundle_relative, source_relative in DOC_PATHS.items():
        source = root / source_relative
        if not source.is_file():
            raise LaunchBundleError(f"required coder reference not found: {source_relative}")
        destination = bundle_root / bundle_relative
        data = source.read_bytes()
        assert_safe_bundle_member(bundle_relative)
        assert_safe_text(bundle_relative, data)
        write_if_changed(destination, data)
        copied_files.append(destination)

    generated_texts = {
        "README.md": render_readme(cohort, packet_manifest),
        "calibration-instructions.md": render_calibration(cohort),
        "coder-declarations.md": render_declarations(cohort),
        "allowed-references.md": render_allowed_references(cohort),
        "return-instructions.md": render_return_instructions(),
    }
    for relative, text in generated_texts.items():
        assert_safe_bundle_member(relative)
        data = text.encode("utf-8")
        assert_safe_text(relative, data)
        destination = bundle_root / relative
        write_if_changed(destination, data)
        copied_files.append(destination)

    generator_path = root / GENERATOR_PATH
    manifest_without_hash = {
        "schema_version": "1.0.0",
        "bundle_id": bundle_id,
        "case_id": case_id,
        "cohort_id": cohort["cohort_id"],
        "cohort_version": cohort["cohort_version"],
        "packet_id": cohort["packet_id"],
        "packet_hash": packet_manifest["packet_hash"],
        "source_language": cohort["source_language"],
        "task_layer": cohort["task_layer"],
        "training_version": cohort["training_version"],
        "calibration_id": cohort["calibration_id"],
        "required_primary_coders": cohort["required_primary_coders"],
        "ai_assistance_allowed": cohort["ai_assistance_allowed"],
        "rights_constraints": cohort["rights_constraints"],
        "storage_policy": cohort["storage_policy"],
        "generator": {
            "script": GENERATOR_PATH,
            "version": GENERATOR_VERSION,
            "script_hash": hash_file(generator_path) if generator_path.is_file() else hash_file(Path(__file__)),
            "code_revision": revision or code_revision(root),
        },
        "source_inputs": [
            {"id": "cohort-manifest", "path": relative_path(root, cohort_path), "hash": hash_file(cohort_path)},
            {"id": "packet-manifest", "path": relative_path(root, packet_manifest_path), "hash": hash_file(packet_manifest_path)},
        ]
        + [
            {"id": destination.replace("/", "-").replace(".", "-"), "path": source.as_posix(), "hash": hash_file(root / source)}
            for destination, source in DOC_PATHS.items()
        ],
        "files": [
            file_record(bundle_root, path)
            for path in sorted(copied_files, key=lambda value: value.relative_to(bundle_root).as_posix())
        ],
    }
    manifest = {
        **manifest_without_hash,
        "bundle_hash": sha256_bytes(canonical_json_bytes(manifest_without_hash)),
    }
    manifest_path = bundle_root / "launch-bundle-manifest.json"
    write_if_changed(
        manifest_path,
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n",
    )
    return {
        **manifest,
        "path": case_relative_path(case_root, bundle_root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--code-revision")
    args = parser.parse_args()
    try:
        manifest = generate_launch_bundle(
            ROOT,
            args.case_id,
            cohort_path=args.cohort,
            revision=args.code_revision,
        )
    except (LaunchBundleError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
    print(f"{args.case_id}: wrote launch bundle `{manifest['bundle_id']}` at {manifest['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
