#!/usr/bin/env python3
"""Run independent or end-to-end multi-model reliability pipeline stages."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from scripts.model_reliability.boundaries import (
        ProtectedPathError,
        immutable_reference_guard,
    )
    from scripts.model_reliability.classify_disagreements import (
        DisagreementError,
        compute_case_disagreements,
    )
    from scripts.model_reliability.compare_runs import (
        ComparisonError,
        compute_case_agreement,
    )
    from scripts.model_reliability.generate_consensus_report import (
        ConsensusReportError,
        generate_case_consensus_report,
    )
    from scripts.model_reliability.generate_packets import (
        PacketGenerationError,
        generate_packets,
    )
    from scripts.model_reliability.generate_review_queue import (
        ReviewQueueError,
        generate_case_review_queue,
    )
    from scripts.model_reliability.ingest_submission import (
        IngestionError,
        ingest_submission,
        parse_csv_submission,
        parse_json_submission,
        read_json_object,
    )
except ModuleNotFoundError:  # Direct execution from scripts/model_reliability/.
    from boundaries import ProtectedPathError, immutable_reference_guard  # type: ignore
    from classify_disagreements import (  # type: ignore
        DisagreementError,
        compute_case_disagreements,
    )
    from compare_runs import ComparisonError, compute_case_agreement  # type: ignore
    from generate_consensus_report import (  # type: ignore
        ConsensusReportError,
        generate_case_consensus_report,
    )
    from generate_packets import (  # type: ignore
        PacketGenerationError,
        generate_packets,
    )
    from generate_review_queue import (  # type: ignore
        ReviewQueueError,
        generate_case_review_queue,
    )
    from ingest_submission import (  # type: ignore
        IngestionError,
        ingest_submission,
        parse_csv_submission,
        parse_json_submission,
        read_json_object,
    )


ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ERRORS = (
    PacketGenerationError,
    IngestionError,
    ComparisonError,
    DisagreementError,
    ReviewQueueError,
    ConsensusReportError,
    ProtectedPathError,
    OSError,
)


def _normalized_runs(root: Path, case_id: str) -> list[Mapping[str, Any]]:
    path = (
        root
        / "cases"
        / case_id
        / "quality"
        / "model-reliability"
        / "normalized"
        / "normalized-runs.json"
    )
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IngestionError(f"{path}: unable to read normalized runs: {exc}") from exc
    if not isinstance(value, Mapping) or value.get("case_id") != case_id:
        raise IngestionError(f"{path}: invalid normalized-runs case_id")
    runs = value.get("runs")
    if not isinstance(runs, list) or not all(
        isinstance(run, Mapping) for run in runs
    ):
        raise IngestionError(f"{path}: invalid normalized-runs runs array")
    return list(runs)


def readiness(
    root: Path,
    case_id: str,
    *,
    packet_id: str | None = None,
    packet_hash: str | None = None,
) -> dict[str, Any]:
    runs = _normalized_runs(root.resolve(), case_id)
    run_ids: list[str] = []
    languages: set[str] = set()
    for wrapper in runs:
        wrapped_submission = wrapper.get("submission")
        submission = (
            wrapped_submission
            if isinstance(wrapped_submission, Mapping)
            else wrapper
        )
        run = submission.get("run")
        run_id = (
            run.get("run_id")
            if isinstance(run, Mapping)
            else submission.get("run_id")
        )
        if not isinstance(run_id, str) or not run_id:
            raise IngestionError("normalized submission is missing a run ID")
        if packet_id is not None and submission.get("packet_id") != packet_id:
            raise IngestionError(
                f"normalized run `{run_id}` does not match current packet_id"
            )
        if packet_hash is not None and submission.get("packet_hash") != packet_hash:
            raise IngestionError(
                f"normalized run `{run_id}` does not match current packet_hash"
            )
        run_ids.append(run_id)
        language = submission.get("source_language")
        if isinstance(language, str) and language:
            languages.add(language)
    if len(run_ids) != len(set(run_ids)):
        raise IngestionError("normalized runs contain duplicate run IDs")
    if not runs:
        return {
            "status": "awaiting-submissions",
            "run_count": 0,
            "run_ids": [],
            "source_languages": [],
            "warning": (
                f"{case_id}: no valid model submissions are available; packets "
                "are ready, and comparison/reporting stages were skipped."
            ),
        }
    if len(runs) < 2:
        return {
            "status": "awaiting-comparable-runs",
            "run_count": len(runs),
            "run_ids": sorted(run_ids),
            "source_languages": sorted(languages),
            "warning": (
                f"{case_id}: only {len(runs)} valid model run is available; at "
                "least two comparable runs are required, so comparison/reporting "
                "stages were skipped."
            ),
        }
    return {
        "status": "ready",
        "run_count": len(runs),
        "run_ids": sorted(run_ids),
        "source_languages": sorted(languages),
        "warning": None,
    }


def run_pipeline(
    root: Path,
    case_id: str,
    *,
    sample_path: Path | None = None,
    revision: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    with immutable_reference_guard(root, case_id):
        manifest = generate_packets(
            root,
            case_id,
            sample_path=sample_path,
            revision=revision,
        )
        ready = readiness(
            root,
            case_id,
            packet_id=str(manifest["packet_id"]),
            packet_hash=str(manifest["packet_hash"]),
        )
        completed = ["packets"]
        if ready["status"] != "ready":
            return {
                "case_id": case_id,
                "status": ready["status"],
                "completed_stages": completed,
                "packet_id": manifest["packet_id"],
                "run_count": ready["run_count"],
                "run_ids": ready["run_ids"],
                "warning": ready["warning"],
            }

        agreement = compute_case_agreement(root, case_id)
        completed.append("comparison")
        disagreements = compute_case_disagreements(root, case_id)
        completed.append("disagreements")
        queue = generate_case_review_queue(root, case_id)
        completed.append("review-queue")
        report = generate_case_consensus_report(root, case_id)
        completed.append("report")
        return {
            "case_id": case_id,
            "status": "complete",
            "completed_stages": completed,
            "packet_id": manifest["packet_id"],
            "run_count": len(agreement["run_ids"]),
            "run_ids": agreement["run_ids"],
            "disagreement_count": disagreements["summary"]["total_disagreements"],
            "review_queue_count": queue["summary"]["queue_count"],
            "reported_field_count": report["summary"]["field_count"],
            "warning": None,
        }


def _add_case(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--case", dest="case_id", required=True)


def _add_packet_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--sample", type=Path)
    parser.add_argument("--code-revision")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help=argparse.SUPPRESS,
    )
    commands = parser.add_subparsers(dest="command", required=True)

    packets = commands.add_parser("packets", help="Generate blind packets")
    _add_case(packets)
    _add_packet_options(packets)

    ingest = commands.add_parser("ingest", help="Ingest one manual submission")
    _add_case(ingest)
    source = ingest.add_mutually_exclusive_group(required=True)
    source.add_argument("--json", dest="json_path", type=Path)
    source.add_argument("--metadata-csv", type=Path)
    ingest.add_argument("--items-csv", type=Path)

    for name, help_text in (
        ("compare", "Compute agreement diagnostics"),
        ("disagreements", "Classify disagreements"),
        ("review-queue", "Generate the human review queue"),
        ("report", "Generate the consensus and instability report"),
    ):
        stage = commands.add_parser(name, help=help_text)
        _add_case(stage)

    run = commands.add_parser("run", help="Run packets through reporting")
    _add_case(run)
    _add_packet_options(run)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "packets":
            result = generate_packets(
                root,
                args.case_id,
                sample_path=args.sample,
                revision=args.code_revision,
            )
            print(
                f"{args.case_id}: wrote deterministic packet "
                f"`{result['packet_id']}`"
            )
        elif args.command == "ingest":
            if args.metadata_csv and not args.items_csv:
                parser.error("--items-csv is required with --metadata-csv")
            if args.items_csv and not args.metadata_csv:
                parser.error("--items-csv requires --metadata-csv")
            if args.json_path:
                parsed = parse_json_submission(args.json_path)
            else:
                contract = read_json_object(
                    root
                    / "schemas"
                    / "model-reliability"
                    / "submission-csv-contract.json"
                )
                parsed = parse_csv_submission(
                    args.metadata_csv, args.items_csv, contract
                )
            result = ingest_submission(root, args.case_id, parsed)
            print(
                f"{args.case_id}: {result['registration_id']} is "
                f"{result['status']} with {len(result['errors'])} error(s)"
            )
            return 0 if result["status"] == "valid" else 1
        elif args.command == "compare":
            result = compute_case_agreement(root, args.case_id)
            print(f"{args.case_id}: compared {len(result['run_ids'])} run(s)")
        elif args.command == "disagreements":
            result = compute_case_disagreements(root, args.case_id)
            print(
                f"{args.case_id}: classified "
                f"{result['summary']['total_disagreements']} disagreement(s)"
            )
        elif args.command == "review-queue":
            result = generate_case_review_queue(root, args.case_id)
            print(
                f"{args.case_id}: queued "
                f"{result['summary']['queue_count']} review item(s)"
            )
        elif args.command == "report":
            result = generate_case_consensus_report(root, args.case_id)
            print(
                f"{args.case_id}: reported "
                f"{result['summary']['field_count']} field(s)"
            )
        else:
            result = run_pipeline(
                root,
                args.case_id,
                sample_path=args.sample,
                revision=args.code_revision,
            )
            if result["warning"]:
                print(f"WARNING: {result['warning']}", file=sys.stderr)
            print(
                f"{args.case_id}: reliability pipeline status "
                f"`{result['status']}`; completed "
                f"{', '.join(result['completed_stages'])}"
            )
    except PIPELINE_ERRORS as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
