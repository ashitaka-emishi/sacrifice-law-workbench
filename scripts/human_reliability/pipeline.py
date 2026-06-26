#!/usr/bin/env python3
"""Run independent or end-to-end human reliability pipeline stages."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from scripts.human_reliability.boundaries import protect_accepted_artifacts
    from scripts.human_reliability.classify_disagreements import (
        HumanDisagreementError,
        compute_case_disagreements,
    )
    from scripts.human_reliability.compare_references import (
        ReferenceComparisonError,
        compute_case_reference_comparison,
    )
    from scripts.human_reliability.compute_agreement import (
        AgreementError,
        compute_case_agreement,
    )
    from scripts.human_reliability.generate_adjudication_queue import (
        AdjudicationQueueError,
        generate_case_adjudication_queue,
    )
    from scripts.human_reliability.generate_adjudication_results_page import (
        AdjudicationResultsPageError,
        generate_results_page,
    )
    from scripts.human_reliability.generate_codebook_notes import (
        HumanCodebookNotesError,
        generate_case_codebook_notes,
    )
    from scripts.human_reliability.generate_packets import (
        PacketGenerationError,
        generate_packets,
    )
    from scripts.human_reliability.generate_report import (
        HumanReliabilityReportError,
        generate_case_report,
    )
    from scripts.human_reliability.ingest_adjudication import (
        AdjudicationIngestionError,
        ingest_adjudication,
    )
    from scripts.human_reliability.ingest_submission import (
        IngestionError,
        ingest_submission,
        parse_csv_submission,
        parse_json_submission,
        read_json_object,
        refresh_ingestion_status,
    )
except ModuleNotFoundError:  # Direct execution from scripts/human_reliability/.
    from boundaries import protect_accepted_artifacts  # type: ignore
    from classify_disagreements import (  # type: ignore
        HumanDisagreementError,
        compute_case_disagreements,
    )
    from compare_references import (  # type: ignore
        ReferenceComparisonError,
        compute_case_reference_comparison,
    )
    from compute_agreement import AgreementError, compute_case_agreement  # type: ignore
    from generate_adjudication_queue import (  # type: ignore
        AdjudicationQueueError,
        generate_case_adjudication_queue,
    )
    from generate_adjudication_results_page import (  # type: ignore
        AdjudicationResultsPageError,
        generate_results_page,
    )
    from generate_codebook_notes import (  # type: ignore
        HumanCodebookNotesError,
        generate_case_codebook_notes,
    )
    from generate_packets import PacketGenerationError, generate_packets  # type: ignore
    from generate_report import HumanReliabilityReportError, generate_case_report  # type: ignore
    from ingest_adjudication import (  # type: ignore
        AdjudicationIngestionError,
        ingest_adjudication,
    )
    from ingest_submission import (  # type: ignore
        IngestionError,
        ingest_submission,
        parse_csv_submission,
        parse_json_submission,
        read_json_object,
        refresh_ingestion_status,
    )


ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ERRORS = (
    PacketGenerationError,
    IngestionError,
    AgreementError,
    ReferenceComparisonError,
    HumanDisagreementError,
    AdjudicationQueueError,
    AdjudicationIngestionError,
    HumanReliabilityReportError,
    AdjudicationResultsPageError,
    HumanCodebookNotesError,
    OSError,
)


def _cohort_status(
    root: Path,
    case_id: str,
    cohort_id: str,
    cohort_version: str,
) -> Mapping[str, Any] | None:
    status_path = (
        root
        / "cases"
        / case_id
        / "quality"
        / "human-reliability"
        / "ingestion-status.json"
    )
    if not status_path.exists():
        return None
    status = read_json_object(status_path)
    for cohort in status.get("cohorts", []):
        if (
            isinstance(cohort, Mapping)
            and cohort.get("cohort_id") == cohort_id
            and cohort.get("cohort_version") == cohort_version
        ):
            return cohort
    return None


def readiness(
    root: Path,
    case_id: str,
    cohort_id: str,
    cohort_version: str,
) -> dict[str, Any]:
    """Return a nonfailure readiness state for downstream human stages."""

    root = root.resolve()
    status = _cohort_status(root, case_id, cohort_id, cohort_version)
    if status is None or status.get("state") == "absent":
        return {
            "status": "awaiting-submissions",
            "cohort_id": cohort_id,
            "cohort_version": cohort_version,
            "valid_submission_count": 0,
            "valid_primary_coders": [],
            "warning": (
                f"{case_id}: no human submissions are registered for "
                f"`{cohort_id}` `{cohort_version}`; packets are ready, and "
                "comparison/reporting stages were skipped."
            ),
        }
    valid_count = int(status.get("valid_submission_count") or 0)
    valid_coders = sorted(str(coder) for coder in status.get("valid_primary_coders", []))
    if status.get("state") == "partial":
        required = int(status.get("required_primary_coders") or 2)
        return {
            "status": "awaiting-primary-coders",
            "cohort_id": cohort_id,
            "cohort_version": cohort_version,
            "valid_submission_count": valid_count,
            "valid_primary_coders": valid_coders,
            "warning": (
                f"{case_id}: {valid_count} valid human submission(s) are "
                f"registered for `{cohort_id}` `{cohort_version}`, but "
                f"{required} primary coder(s) are required; downstream "
                "comparison/reporting stages were skipped."
            ),
        }
    if status.get("state") == "invalid":
        return {
            "status": "submissions-invalid",
            "cohort_id": cohort_id,
            "cohort_version": cohort_version,
            "valid_submission_count": valid_count,
            "valid_primary_coders": valid_coders,
            "warning": (
                f"{case_id}: invalid human submissions are registered for "
                f"`{cohort_id}` `{cohort_version}`; fix ingestion before "
                "comparison/reporting stages."
            ),
        }
    if status.get("state") != "complete":
        return {
            "status": f"ingestion-{status.get('state')}",
            "cohort_id": cohort_id,
            "cohort_version": cohort_version,
            "valid_submission_count": valid_count,
            "valid_primary_coders": valid_coders,
            "warning": (
                f"{case_id}: human ingestion is `{status.get('state')}` for "
                f"`{cohort_id}` `{cohort_version}`; downstream stages were skipped."
            ),
        }
    return {
        "status": "ready",
        "cohort_id": cohort_id,
        "cohort_version": cohort_version,
        "valid_submission_count": valid_count,
        "valid_primary_coders": valid_coders,
        "warning": None,
    }


def run_comparison_stages(
    root: Path,
    case_id: str,
    cohort_id: str,
    cohort_version: str,
    *,
    adjudicated_path: Path | None = None,
    sample_manifest_path: Path | None = None,
) -> dict[str, Any]:
    agreement = compute_case_agreement(root, case_id, cohort_id, cohort_version)
    reference = compute_case_reference_comparison(
        root,
        case_id,
        cohort_id,
        cohort_version,
        adjudicated_path=adjudicated_path,
    )
    disagreements = compute_case_disagreements(
        root,
        case_id,
        cohort_id,
        cohort_version,
        sample_manifest_path=sample_manifest_path,
    )
    return {
        "agreement": agreement,
        "reference_comparison": reference,
        "disagreements": disagreements,
    }


@protect_accepted_artifacts
def run_pipeline(
    root: Path,
    case_id: str,
    cohort_path: Path,
    *,
    cohort_id: str,
    cohort_version: str,
    sample_path: Path | None = None,
    revision: str | None = None,
    adjudicated_path: Path | None = None,
    sample_manifest_path: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    manifest = generate_packets(
        root,
        case_id,
        sample_path=sample_path,
        revision=revision,
    )
    completed = ["packets"]
    refresh_ingestion_status(root, case_id, cohort_path)
    ready = readiness(root, case_id, cohort_id, cohort_version)
    if ready["status"] != "ready":
        return {
            "case_id": case_id,
            "status": ready["status"],
            "completed_stages": completed,
            "packet_id": manifest["packet_id"],
            "valid_submission_count": ready["valid_submission_count"],
            "valid_primary_coders": ready["valid_primary_coders"],
            "warning": ready["warning"],
        }

    comparison = run_comparison_stages(
        root,
        case_id,
        cohort_id,
        cohort_version,
        adjudicated_path=adjudicated_path,
        sample_manifest_path=sample_manifest_path,
    )
    completed.extend(["agreement", "reference", "disagreements"])
    queue = generate_case_adjudication_queue(root, case_id, cohort_id, cohort_version)
    completed.append("adjudication-queue")
    report = generate_case_report(root, case_id, cohort_id, cohort_version)
    completed.append("report")
    notes = generate_case_codebook_notes(root, case_id)
    completed.append("codebook-notes")
    return {
        "case_id": case_id,
        "status": "complete",
        "completed_stages": completed,
        "packet_id": manifest["packet_id"],
        "valid_submission_count": ready["valid_submission_count"],
        "valid_primary_coders": ready["valid_primary_coders"],
        "agreement_field_count": len(comparison["agreement"]["field_metrics"]),
        "reference_pattern_count": len(
            comparison["reference_comparison"]["pattern_records"]
        ),
        "disagreement_count": comparison["disagreements"]["summary"][
            "total_disagreements"
        ],
        "adjudication_queue_count": queue["summary"]["queue_count"],
        "report_status": "generated",
        "codebook_recommendation_count": notes["summary"]["recommendation_count"],
        "warning": None,
    }


def _add_case(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--case", dest="case_id", required=True)


def _add_cohort_identity(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cohort", dest="cohort_id", required=True)
    parser.add_argument("--cohort-version", required=True)


def _add_packet_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--sample", type=Path)
    parser.add_argument("--code-revision")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    commands = parser.add_subparsers(dest="command", required=True)

    packets = commands.add_parser("packets", help="Generate blind human coding packets")
    _add_case(packets)
    _add_packet_options(packets)

    ingest = commands.add_parser("ingest", help="Ingest one human coder submission")
    _add_case(ingest)
    ingest.add_argument("--cohort-manifest", type=Path, required=True)
    source = ingest.add_mutually_exclusive_group(required=True)
    source.add_argument("--json", dest="json_path", type=Path)
    source.add_argument("--csv", dest="csv_path", type=Path)
    source.add_argument("--status-only", action="store_true")

    status = commands.add_parser("status", help="Refresh and report cohort ingestion status")
    _add_case(status)
    _add_cohort_identity(status)
    status.add_argument("--cohort-manifest", type=Path, required=True)

    for name, help_text in (
        ("agreement", "Compute human inter-annotator agreement"),
        ("reference", "Compare human coder outputs with accepted references"),
        ("disagreements", "Classify human coder disagreements"),
        ("queue", "Generate the adjudication queue"),
        ("report", "Generate the human reliability report"),
    ):
        stage = commands.add_parser(name, help=help_text)
        _add_case(stage)
        _add_cohort_identity(stage)
        if name == "reference":
            stage.add_argument("--adjudicated", type=Path)
        if name == "disagreements":
            stage.add_argument("--sample-manifest", type=Path)

    compare = commands.add_parser(
        "compare",
        help="Run agreement, reference comparison, and disagreement classification",
    )
    _add_case(compare)
    _add_cohort_identity(compare)
    compare.add_argument("--adjudicated", type=Path)
    compare.add_argument("--sample-manifest", type=Path)

    adjudicate = commands.add_parser("adjudicate", help="Ingest adjudication decisions")
    _add_case(adjudicate)
    _add_cohort_identity(adjudicate)
    adjudicate.add_argument("--json", dest="source_path", type=Path, required=True)

    results = commands.add_parser(
        "adjudication-results",
        help="Generate the public-safe adjudication results page",
    )
    results.add_argument("--output", type=Path)

    notes = commands.add_parser(
        "codebook-notes",
        help="Generate human-governed codebook revision notes",
    )
    _add_case(notes)

    run = commands.add_parser("run", help="Run packets through reporting when ready")
    _add_case(run)
    _add_cohort_identity(run)
    run.add_argument("--cohort-manifest", type=Path, required=True)
    _add_packet_options(run)
    run.add_argument("--adjudicated", type=Path)
    run.add_argument("--sample-manifest", type=Path)
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
                f"{args.case_id}: wrote deterministic human packet "
                f"`{result['packet_id']}`"
            )
        elif args.command == "ingest":
            if args.status_only:
                summary = refresh_ingestion_status(
                    root, args.case_id, args.cohort_manifest
                )
                print(
                    f"{args.case_id}: cohort `{summary['cohort_id']}` ingestion "
                    f"is {summary['state']}"
                )
                return 0
            if args.json_path:
                parsed = parse_json_submission(args.json_path)
            else:
                contract = read_json_object(
                    root
                    / "schemas"
                    / "human-reliability"
                    / "submission-csv-contract.json"
                )
                parsed = parse_csv_submission(args.csv_path, contract)
            result = ingest_submission(
                root,
                args.case_id,
                args.cohort_manifest,
                parsed,
            )
            print(
                f"{args.case_id}: {result['registration_id']} is "
                f"{result['status']}; cohort ingestion is "
                f"{result['cohort_ingestion_state']}"
            )
            return 0 if result["status"] == "valid" else 1
        elif args.command == "status":
            refresh_ingestion_status(root, args.case_id, args.cohort_manifest)
            result = readiness(root, args.case_id, args.cohort_id, args.cohort_version)
            if result["warning"]:
                print(f"WARNING: {result['warning']}", file=sys.stderr)
            print(
                f"{args.case_id}: human reliability status "
                f"`{result['status']}` for {args.cohort_id} "
                f"{args.cohort_version}"
            )
        elif args.command == "agreement":
            result = compute_case_agreement(
                root, args.case_id, args.cohort_id, args.cohort_version
            )
            print(
                f"{args.case_id}: compared {len(result['coder_ids'])} "
                f"coder(s) in {result['cohort_id']}"
            )
        elif args.command == "reference":
            result = compute_case_reference_comparison(
                root,
                args.case_id,
                args.cohort_id,
                args.cohort_version,
                adjudicated_path=args.adjudicated,
            )
            print(
                f"{args.case_id}: wrote {len(result['pattern_records'])} "
                f"reference pattern record(s)"
            )
        elif args.command == "compare":
            result = run_comparison_stages(
                root,
                args.case_id,
                args.cohort_id,
                args.cohort_version,
                adjudicated_path=args.adjudicated,
                sample_manifest_path=args.sample_manifest,
            )
            print(
                f"{args.case_id}: compared human runs and classified "
                f"{result['disagreements']['summary']['total_disagreements']} "
                "disagreement(s)"
            )
        elif args.command == "disagreements":
            result = compute_case_disagreements(
                root,
                args.case_id,
                args.cohort_id,
                args.cohort_version,
                sample_manifest_path=args.sample_manifest,
            )
            print(
                f"{args.case_id}: wrote "
                f"{result['summary']['total_disagreements']} disagreement(s)"
            )
        elif args.command == "queue":
            result = generate_case_adjudication_queue(
                root, args.case_id, args.cohort_id, args.cohort_version
            )
            print(
                f"{args.case_id}: queued {result['summary']['queue_count']} "
                "adjudication item(s)"
            )
        elif args.command == "adjudicate":
            result = ingest_adjudication(
                root,
                args.case_id,
                args.cohort_id,
                args.cohort_version,
                args.source_path,
            )
            print(
                f"{args.case_id}: adjudication ingestion is "
                f"{result['status']} with {len(result['errors'])} error(s)"
            )
            return 0 if result["status"] == "valid" else 1
        elif args.command == "report":
            generate_case_report(
                root, args.case_id, args.cohort_id, args.cohort_version
            )
            print(f"{args.case_id}: generated human reliability report")
        elif args.command == "adjudication-results":
            result = generate_results_page(root, output=args.output)
            print(f"wrote adjudication results page to {result}")
        elif args.command == "codebook-notes":
            result = generate_case_codebook_notes(root, args.case_id)
            print(
                f"{args.case_id}: generated "
                f"{result['summary']['recommendation_count']} codebook "
                "recommendation(s)"
            )
        else:
            result = run_pipeline(
                root,
                args.case_id,
                args.cohort_manifest,
                cohort_id=args.cohort_id,
                cohort_version=args.cohort_version,
                sample_path=args.sample,
                revision=args.code_revision,
                adjudicated_path=args.adjudicated,
                sample_manifest_path=args.sample_manifest,
            )
            if result["warning"]:
                print(f"WARNING: {result['warning']}", file=sys.stderr)
            print(
                f"{args.case_id}: human reliability pipeline status "
                f"`{result['status']}`; completed "
                f"{', '.join(result['completed_stages'])}"
            )
    except PIPELINE_ERRORS as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
