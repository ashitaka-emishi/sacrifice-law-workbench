#!/usr/bin/env python3
"""Run a blind model-reliability packet against a fresh external model session.

The runner is intentionally narrow: it reads the committed blind packet, sends
only the packet prompt/payload plus a submission template, writes the provider's
raw JSON submission to an ignored local directory, and validates the response
against the existing model-reliability submission contract. It does not ingest
the response or modify accepted artifacts.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from scripts.model_reliability.ingest_submission import (
        IngestionError,
        SENSITIVE_PATTERN,
        _case_vocabulary_errors,
        _metadata_errors,
        _packet_alignment_errors,
        load_packet_context,
        read_json_object,
    )
    from scripts.model_reliability.submission_contract import (
        load_controlled_vocabularies,
        validate_submission,
    )
except ModuleNotFoundError:  # Direct execution from scripts/model_reliability/.
    from ingest_submission import (  # type: ignore
        IngestionError,
        SENSITIVE_PATTERN,
        _case_vocabulary_errors,
        _metadata_errors,
        _packet_alignment_errors,
        load_packet_context,
        read_json_object,
    )
    from submission_contract import load_controlled_vocabularies, validate_submission  # type: ignore


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = ROOT / "reports" / "tmp" / "model-reliability"
PROVIDERS = {"anthropic", "openai"}
LAYER_PAYLOAD_FILENAMES = {
    "identification": "identification-packet.jsonl",
    "cmt": "cmt-packet.jsonl",
    "interpretation": "interpretive-packet.jsonl",
}
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class ExternalModelRunnerError(RuntimeError):
    """Raised when a provider call, parse, or validation step fails."""


@dataclass(frozen=True)
class PacketRun:
    root: Path
    case_id: str
    task_layer: str
    manifest: Mapping[str, Any]
    prompt_record: Mapping[str, Any]
    payload_record: Mapping[str, Any]
    prompt_text: str
    packet_rows: list[dict[str, Any]]


def _safe_slug(value: str) -> str:
    rendered = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())
    return rendered.strip("-") or "run"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ExternalModelRunnerError(f"{path}:{line_number}: invalid JSONL: {exc}") from exc
        if not isinstance(value, dict):
            raise ExternalModelRunnerError(f"{path}:{line_number}: packet row must be an object")
        rows.append(value)
    return rows


def _case_packet_path(root: Path, case_id: str, relative: str) -> Path:
    case_root = (root / "cases" / case_id).resolve()
    path = (case_root / relative).resolve()
    packet_root = (case_root / "quality" / "model-reliability" / "packets").resolve()
    try:
        path.relative_to(packet_root)
    except ValueError as exc:
        raise ExternalModelRunnerError(f"packet artifact escapes packet directory: {relative}") from exc
    return path


def load_packet_run(root: Path, case_id: str, task_layer: str) -> PacketRun:
    root = root.resolve()
    packet_root = root / "cases" / case_id / "quality" / "model-reliability" / "packets"
    manifest = read_json_object(packet_root / "packet-manifest.json")
    prompt_record = next(
        (
            item
            for item in manifest.get("prompts", [])
            if isinstance(item, Mapping) and item.get("task_layer") == task_layer
        ),
        None,
    )
    payload_record = next(
        (
            item
            for item in manifest.get("payloads", [])
            if isinstance(item, Mapping) and item.get("task_layer") == task_layer
        ),
        None,
    )
    if not isinstance(prompt_record, Mapping):
        raise ExternalModelRunnerError(f"packet manifest has no prompt for `{task_layer}`")
    if not isinstance(payload_record, Mapping):
        raise ExternalModelRunnerError(f"packet manifest has no payload for `{task_layer}`")
    prompt_path = _case_packet_path(root, case_id, str(prompt_record.get("path") or ""))
    payload_path = _case_packet_path(root, case_id, str(payload_record.get("path") or ""))
    return PacketRun(
        root=root,
        case_id=case_id,
        task_layer=task_layer,
        manifest=manifest,
        prompt_record=prompt_record,
        payload_record=payload_record,
        prompt_text=prompt_path.read_text(encoding="utf-8"),
        packet_rows=_read_jsonl(payload_path),
    )


def base_submission_template(
    packet: PacketRun,
    *,
    provider: str,
    model: str,
    model_version: str | None,
    run_id: str,
    submission_id: str,
    completed_at: str,
    language_capabilities: Sequence[str],
    settings: Mapping[str, Any],
) -> dict[str, Any]:
    def layer_fields(row: Mapping[str, Any]) -> dict[str, Any]:
        if packet.task_layer == "identification":
            return {
                "identification": {
                    "contextual_meaning": "MODEL MUST REPLACE",
                    "basic_meaning": "MODEL MUST REPLACE",
                    "contrast_explanation": "MODEL MUST REPLACE",
                    "comparison_basis": "MODEL MUST REPLACE",
                },
                "lexical_units": [
                    {
                        **unit,
                        "decision": "uncertain",
                        "boundary_decision": "uncertain",
                    }
                    for unit in row.get("lexical_units", [])
                    if isinstance(unit, Mapping)
                ],
            }
        if packet.task_layer == "cmt":
            return {
                "cmt": {
                    "source_domain_primary": "MODEL MUST REPLACE",
                    "source_domain_secondary": [],
                    "target_domain": "MODEL MUST REPLACE",
                    "conceptual_metaphor": "MODEL MUST REPLACE",
                    "entailments": ["MODEL MUST REPLACE"],
                    "cluster_id": "MODEL MUST REPLACE",
                }
            }
        if packet.task_layer == "interpretation":
            return {
                "interpretation": {
                    "functions": {
                        "sacred_object": "uncertain",
                        "sacrificial_body": "uncertain",
                        "enemy_as_bringer_of_death": "uncertain",
                        "violence_logic": "uncertain",
                        "obligatory_frame": "uncertain",
                        "purification": "uncertain",
                    },
                    "agency": {
                        "agents": [],
                        "patients": [],
                        "beneficiaries": [],
                        "sacrificial_subjects": [],
                        "excluded_agents": [],
                    },
                    "absence": {
                        "status": "uncertain",
                        "expected_presence": "",
                        "possible_absence": "",
                        "displacement_mechanism": "",
                    },
                }
            }
        raise ExternalModelRunnerError(f"unsupported task layer `{packet.task_layer}`")

    return {
        "schema_version": "1.0.0",
        "submission_id": submission_id,
        "case_id": packet.case_id,
        "sample_id": packet.manifest["sample_id"],
        "sample_version": packet.manifest["sample_version"],
        "packet_id": packet.manifest["packet_id"],
        "packet_hash": packet.manifest["packet_hash"],
        "prompt_id": packet.prompt_record["id"],
        "prompt_hash": packet.prompt_record["hash"],
        "source_language": packet.manifest["source_language"],
        "code_revision": packet.manifest["code_revision"],
        "run": {
            "run_id": run_id,
            "provider": provider,
            "model": model,
            "model_version": model_version,
            "completed_at": completed_at,
            "language_capabilities": list(language_capabilities),
            "settings": dict(settings),
        },
        "items": [
            {
                **row,
                **layer_fields(row),
                "confidence": 0.0,
                "uncertainty": {"status": "unresolved", "note": "MODEL MUST REPLACE"},
                "rival_reading": "MODEL MUST REPLACE",
                "case_fields": {},
            }
            for row in packet.packet_rows
        ],
    }


def provider_vocabulary_instruction(packet: PacketRun) -> str:
    guidance: dict[str, Any] = {
        "uncertainty.status": ["none", "low", "material", "unresolved"],
    }
    if packet.task_layer == "identification":
        guidance["lexical_units[].decision"] = [
            "non_metaphor",
            "mipvu_indirect",
            "mipvu_direct",
            "mipvu_implicit",
            "mipvu_personification",
            "uncertain",
            "excluded_nonlexical",
        ]
        guidance["lexical_units[].boundary_decision"] = [
            "exact",
            "expand",
            "contract",
            "split",
            "merge",
            "no_valid_span",
            "uncertain",
        ]
    elif packet.task_layer == "cmt":
        vocab_path = packet.root / "config" / "controlled-vocabularies.json"
        vocab_data = read_json_object(vocab_path)
        guidance["cmt.source_domain_primary"] = [
            item["id"]
            for item in vocab_data.get("source_domains", [])
            if isinstance(item, Mapping) and item.get("id")
        ]
        guidance["cmt.source_domain_secondary[]"] = guidance["cmt.source_domain_primary"]
        guidance["cmt.target_domain"] = [
            item["id"]
            for item in vocab_data.get("target_domains", [])
            if isinstance(item, Mapping) and item.get("id")
        ]
        cluster_path = packet.root / "cases" / packet.case_id / "config" / "case-clusters.json"
        cluster_data = json.loads(cluster_path.read_text(encoding="utf-8"))
        guidance["cmt.cluster_id"] = [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "keywords": item.get("keywords", []),
            }
            for item in cluster_data
            if isinstance(item, Mapping) and item.get("id")
        ]
    elif packet.task_layer == "interpretation":
        field_values = ["present", "absent", "uncertain", "not_applicable"]
        guidance["interpretation.functions.*"] = field_values
        guidance["interpretation.absence.status"] = field_values
    return (
        "Use only these exact controlled values where applicable. Do not invent "
        "new IDs or use labels in place of IDs:\n"
        + json.dumps(guidance, ensure_ascii=False, indent=2)
    )


def format_instruction(packet: PacketRun, template: Mapping[str, Any]) -> str:
    schema_summary = {
        "required_envelope_fields": [
            "schema_version",
            "submission_id",
            "case_id",
            "sample_id",
            "sample_version",
            "packet_id",
            "packet_hash",
            "prompt_id",
            "prompt_hash",
            "source_language",
            "code_revision",
            "run",
            "items",
        ],
        "task_layer": packet.task_layer,
        "layer_specific_fields": {
            "identification": (
                "For each item, add `identification`; for each lexical unit, add "
                "`decision` and `boundary_decision`."
            ),
            "cmt": "For each item, add `cmt`.",
            "interpretation": "For each item, add `interpretation`.",
        }[packet.task_layer],
    }
    return (
        "Return exactly one raw JSON object and no Markdown fences, commentary, "
        "or extra text. Preserve every packet identity/source field exactly. "
        "Do not add accepted annotations, prior outputs, citations, URLs, "
        "credentials, or personal identifiers. Use only the blind packet below. "
        "The JSON must conform to schemas/model-reliability/submission-schema.json.\n\n"
        "Schema/task reminder:\n"
        + json.dumps(schema_summary, ensure_ascii=False, indent=2)
        + "\n\nControlled values:\n"
        + provider_vocabulary_instruction(packet)
        + "\n\nSubmission envelope template to fill:\n"
        + json.dumps(template, ensure_ascii=False, indent=2)
    )


def build_provider_messages(packet: PacketRun, template: Mapping[str, Any]) -> tuple[str, str]:
    system = (
        "You are completing a blind model-reliability packet. You have no tools, "
        "browsing, retrieval, memory, repository access, accepted annotations, "
        "or prior model outputs. Return only the requested JSON submission."
    )
    packet_payload = "\n".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for row in packet.packet_rows
    )
    user = (
        "## Blind task prompt\n\n"
        f"{packet.prompt_text}\n\n"
        "## Blind packet JSONL\n\n"
        f"{packet_payload}\n\n"
        "## Required response format\n\n"
        f"{format_instruction(packet, template)}"
    )
    return system, user


def _request_json(
    url: str,
    headers: Mapping[str, str],
    body: Mapping[str, Any],
    *,
    timeout_seconds: float = 180.0,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ExternalModelRunnerError(f"provider HTTP {exc.code}: {detail}") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise ExternalModelRunnerError(
            f"provider request timed out after {timeout_seconds:g} seconds"
        ) from exc
    except urllib.error.URLError as exc:
        raise ExternalModelRunnerError(f"provider request failed: {exc}") from exc
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExternalModelRunnerError(f"provider returned non-JSON response: {exc}") from exc
    if not isinstance(value, dict):
        raise ExternalModelRunnerError("provider response must be a JSON object")
    return value


def call_openai(
    *,
    api_key: str,
    model: str,
    system: str,
    user: str,
    settings: Mapping[str, Any],
    timeout_seconds: float = 180.0,
) -> str:
    body: dict[str, Any] = {
        "model": model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": system}]},
            {"role": "user", "content": [{"type": "input_text", "text": user}]},
        ],
    }
    for key in ("temperature", "top_p", "max_output_tokens", "seed"):
        if key in settings:
            body[key] = settings[key]
    # Responses API has no persistent memory, browsing, retrieval, or tool use
    # unless tools/vector stores are supplied; this runner supplies none.
    data = _request_json(
        OPENAI_RESPONSES_URL,
        {"Authorization": f"Bearer {api_key}"},
        body,
        timeout_seconds=timeout_seconds,
    )
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    fragments: list[str] = []
    for item in data.get("output", []):
        if not isinstance(item, Mapping):
            continue
        for content in item.get("content", []):
            if not isinstance(content, Mapping):
                continue
            text = content.get("text")
            if isinstance(text, str):
                fragments.append(text)
    if fragments:
        return "\n".join(fragments)
    raise ExternalModelRunnerError("OpenAI response did not contain output text")


def call_anthropic(
    *,
    api_key: str,
    model: str,
    system: str,
    user: str,
    settings: Mapping[str, Any],
    timeout_seconds: float = 180.0,
) -> str:
    try:
        max_tokens = int(settings.get("max_tokens", settings.get("max_output_tokens", 8192)))
    except (TypeError, ValueError) as exc:
        raise ExternalModelRunnerError("Anthropic max_tokens must be an integer") from exc
    body: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    for key in ("temperature", "top_p", "top_k"):
        if key in settings:
            body[key] = settings[key]
    # Messages API has no browsing/retrieval/tools unless tool definitions are
    # supplied; this runner supplies none.
    data = _request_json(
        ANTHROPIC_MESSAGES_URL,
        {"x-api-key": api_key, "anthropic-version": ANTHROPIC_VERSION},
        body,
        timeout_seconds=timeout_seconds,
    )
    fragments = [
        item.get("text")
        for item in data.get("content", [])
        if isinstance(item, Mapping) and item.get("type") == "text" and isinstance(item.get("text"), str)
    ]
    if fragments:
        return "\n".join(str(fragment) for fragment in fragments)
    raise ExternalModelRunnerError("Anthropic response did not contain text content")


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise ExternalModelRunnerError("provider output did not contain a JSON object")
        try:
            value = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ExternalModelRunnerError(f"provider output JSON could not be parsed: {exc}") from exc
    if not isinstance(value, dict):
        raise ExternalModelRunnerError("provider output must parse as a JSON object")
    return value


def validate_external_submission(root: Path, case_id: str, submission: Mapping[str, Any]) -> list[str]:
    packet = load_packet_context(root.resolve(), case_id)
    errors = validate_submission(
        submission,
        packet.validation_context,
        vocabularies=load_controlled_vocabularies(
            root.resolve() / "config" / "controlled-vocabularies.json"
        ),
    )
    errors.extend(_metadata_errors(submission, packet))
    errors.extend(_packet_alignment_errors(submission, packet))
    errors.extend(_case_vocabulary_errors(root.resolve(), case_id, submission))
    return errors


def template_metadata_errors(
    submission: Mapping[str, Any], template: Mapping[str, Any]
) -> list[str]:
    errors: list[str] = []
    for field in (
        "schema_version",
        "submission_id",
        "case_id",
        "sample_id",
        "sample_version",
        "packet_id",
        "packet_hash",
        "prompt_id",
        "prompt_hash",
        "source_language",
        "code_revision",
    ):
        if submission.get(field) != template.get(field):
            errors.append(f"$.{field}: provider response changed runner-supplied metadata")
    actual_run = submission.get("run")
    expected_run = template.get("run")
    if not isinstance(actual_run, Mapping) or not isinstance(expected_run, Mapping):
        return errors
    for field in (
        "run_id",
        "provider",
        "model",
        "model_version",
        "completed_at",
        "language_capabilities",
        "settings",
    ):
        if actual_run.get(field) != expected_run.get(field):
            errors.append(f"$.run.{field}: provider response changed runner-supplied metadata")
    return errors


def write_submission(
    output_root: Path,
    *,
    case_id: str,
    provider: str,
    model: str,
    task_layer: str,
    run_id: str,
    submission: Mapping[str, Any],
) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / (
        f"{_safe_slug(case_id)}-{_safe_slug(provider)}-"
        f"{_safe_slug(model)}-{_safe_slug(task_layer)}-{_safe_slug(run_id)}.json"
    )
    path.write_text(
        json.dumps(submission, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def parse_settings(values: Sequence[str]) -> dict[str, Any]:
    settings: dict[str, Any] = {}
    for value in values:
        if "=" not in value:
            raise ExternalModelRunnerError(f"setting must be KEY=VALUE: {value}")
        key, raw = value.split("=", 1)
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise ExternalModelRunnerError(f"unsafe setting key: {key}")
        if SENSITIVE_PATTERN.search(key) or SENSITIVE_PATTERN.search(raw):
            raise ExternalModelRunnerError(
                f"refusing to serialize sensitive-looking setting `{key}`"
            )
        try:
            settings[key] = json.loads(raw)
        except json.JSONDecodeError:
            settings[key] = raw
    return settings


def load_mock_response(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_inline_comment(value: str) -> str:
    in_single = False
    in_double = False
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_double:
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            continue
        if char == "#" and not in_single and not in_double:
            if index == 0 or value[index - 1].isspace():
                return value[:index].rstrip()
    return value.strip()


def _unquote_dotenv_value(value: str) -> str:
    value = _strip_inline_comment(value)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        inner = value[1:-1]
        if value[0] == '"':
            escapes = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\", '"': '"'}
            rendered: list[str] = []
            escaped = False
            for char in inner:
                if escaped:
                    rendered.append(escapes.get(char, f"\\{char}"))
                    escaped = False
                elif char == "\\":
                    escaped = True
                else:
                    rendered.append(char)
            if escaped:
                rendered.append("\\")
            return "".join(rendered)
        return inner
    return value


def load_dotenv_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    if not path.is_file():
        raise ExternalModelRunnerError(f"dotenv path is not a file: {path}")
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            raise ExternalModelRunnerError(f"{path}:{line_number}: dotenv entry must be KEY=value")
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ExternalModelRunnerError(f"{path}:{line_number}: unsafe dotenv key `{key}`")
        values[key] = _unquote_dotenv_value(raw_value.strip())
    return values


def resolve_api_key(
    *,
    env_name: str,
    root: Path,
    env_file: Path | None,
    no_env_file: bool,
) -> str | None:
    exported = os.environ.get(env_name)
    if exported:
        return exported
    if no_env_file:
        return None
    dotenv_path = env_file or (root / ".env")
    return load_dotenv_values(dotenv_path.resolve()).get(env_name)


def run(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    if args.provider not in PROVIDERS:
        raise ExternalModelRunnerError(f"unsupported provider `{args.provider}`")
    if args.http_timeout <= 0:
        raise ExternalModelRunnerError("--http-timeout must be positive")
    settings = parse_settings(args.setting)
    if args.disable_tools_note:
        settings.setdefault("tools_disabled", True)
        settings.setdefault("browsing_disabled", True)
        settings.setdefault("retrieval_disabled", True)
        settings.setdefault("memory_disabled", True)
    completed_at = args.completed_at or _utc_now()
    run_id = args.run_id or f"{args.provider}-{_safe_slug(args.model)}-{args.task_layer}-{completed_at}"
    submission_id = args.submission_id or f"{args.case_id}-{run_id}"
    packet = load_packet_run(root, args.case_id, args.task_layer)
    language_capabilities = args.language_capability or [str(packet.manifest["source_language"])]
    if str(packet.manifest["source_language"]) not in language_capabilities:
        language_capabilities = [*language_capabilities, str(packet.manifest["source_language"])]
    template = base_submission_template(
        packet,
        provider=args.provider,
        model=args.model,
        model_version=args.model_version,
        run_id=run_id,
        submission_id=submission_id,
        completed_at=completed_at,
        language_capabilities=language_capabilities,
        settings=settings,
    )
    system, user = build_provider_messages(packet, template)

    if args.dry_run:
        dry_run_path = write_submission(
            args.output_root,
            case_id=args.case_id,
            provider=args.provider,
            model=args.model,
            task_layer=args.task_layer,
            run_id=f"{run_id}-template",
            submission=template,
        )
        prompt_path = dry_run_path.with_suffix(".prompt.txt")
        prompt_path.write_text(
            "SYSTEM:\n" + system + "\n\nUSER:\n" + user,
            encoding="utf-8",
        )
        print(f"dry-run template: {dry_run_path}")
        print(f"dry-run provider prompt: {prompt_path}")
        return 0

    if args.mock_response:
        raw_provider_text = load_mock_response(args.mock_response)
    else:
        env_name = args.api_key_env or (
            "OPENAI_API_KEY" if args.provider == "openai" else "ANTHROPIC_API_KEY"
        )
        api_key = resolve_api_key(
            env_name=env_name,
            root=root,
            env_file=args.env_file,
            no_env_file=args.no_env_file,
        )
        if not api_key:
            raise ExternalModelRunnerError(
                f"missing API key `{env_name}` in environment or dotenv file"
            )
        if args.provider == "openai":
            raw_provider_text = call_openai(
                api_key=api_key,
                model=args.model,
                system=system,
                user=user,
                settings=settings,
                timeout_seconds=args.http_timeout,
            )
        else:
            raw_provider_text = call_anthropic(
                api_key=api_key,
                model=args.model,
                system=system,
                user=user,
                settings=settings,
                timeout_seconds=args.http_timeout,
            )

    submission = extract_json_object(raw_provider_text)
    if SENSITIVE_PATTERN.search(json.dumps(submission, ensure_ascii=False)):
        raise ExternalModelRunnerError(
            "refusing to write provider output that appears to contain credentials or account IDs"
        )
    output_path = write_submission(
        args.output_root,
        case_id=args.case_id,
        provider=args.provider,
        model=args.model,
        task_layer=args.task_layer,
        run_id=run_id,
        submission=submission,
    )
    errors = validate_external_submission(root, args.case_id, submission)
    errors.extend(template_metadata_errors(submission, template))
    if errors:
        report_path = output_path.with_suffix(".validation-errors.txt")
        report_path.write_text("\n".join(errors) + "\n", encoding="utf-8")
        print(f"wrote invalid submission: {output_path}")
        print(f"validation errors: {report_path}")
        return 1
    print(f"wrote valid submission: {output_path}")
    print(
        "ingest with: "
        f"python3 scripts/model_reliability/pipeline.py ingest --case {args.case_id} --json {output_path}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--case", dest="case_id", default="lincoln")
    parser.add_argument("--task-layer", choices=sorted(LAYER_PAYLOAD_FILENAMES), required=True)
    parser.add_argument("--provider", choices=sorted(PROVIDERS), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-version")
    parser.add_argument("--run-id")
    parser.add_argument("--submission-id")
    parser.add_argument("--completed-at")
    parser.add_argument("--language-capability", action="append", default=[])
    parser.add_argument(
        "--setting",
        action="append",
        default=[],
        help="Non-secret provider/run setting as KEY=JSON_VALUE, e.g. temperature=0",
    )
    parser.add_argument("--api-key-env")
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Read API keys from this dotenv file after checking exported environment variables.",
    )
    parser.add_argument(
        "--no-env-file",
        action="store_true",
        help="Do not read the default repository .env file or any dotenv file.",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--http-timeout",
        type=float,
        default=180.0,
        help="Provider HTTP read timeout in seconds.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mock-response", type=Path)
    parser.add_argument(
        "--disable-tools-note",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Record non-secret settings noting tools/browsing/retrieval/memory are disabled or not supplied.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except IngestionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except ExternalModelRunnerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
