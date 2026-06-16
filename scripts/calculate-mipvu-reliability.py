#!/usr/bin/env python3
"""Calculate two-coder MIPVU reliability from completed coder CSV packets."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

METAPHOR_RELATED = {
    "mipvu_indirect",
    "mipvu_direct",
    "mipvu_implicit",
    "mipvu_personification",
    "uncertain",
}

VALID_DECISIONS = METAPHOR_RELATED | {"non_metaphor", "excluded_nonlexical"}


def read_coder_csv(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"mipvu_id", "decision_type"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing column(s): {', '.join(sorted(missing))}")
        rows: dict[str, dict[str, str]] = {}
        for index, row in enumerate(reader, start=2):
            mipvu_id = (row.get("mipvu_id") or "").strip()
            decision = (row.get("decision_type") or "").strip()
            if not mipvu_id:
                raise ValueError(f"{path}: row {index} missing mipvu_id")
            if not decision:
                raise ValueError(f"{path}: row {index} missing decision_type")
            if decision not in VALID_DECISIONS:
                raise ValueError(f"{path}: row {index} invalid decision_type `{decision}`")
            rows[mipvu_id] = {key: (value or "").strip() for key, value in row.items()}
        return rows


def binary(decision: str) -> str:
    return "metaphor_related" if decision in METAPHOR_RELATED else "not_metaphor_related"


def cohens_kappa(pairs: list[tuple[str, str]]) -> float | None:
    if not pairs:
        return None
    labels = sorted({label for pair in pairs for label in pair})
    total = len(pairs)
    observed = sum(1 for a, b in pairs if a == b) / total
    expected = 0.0
    for label in labels:
        p_a = sum(1 for a, _ in pairs if a == label) / total
        p_b = sum(1 for _, b in pairs if b == label) / total
        expected += p_a * p_b
    if expected == 1.0:
        return 1.0 if observed == 1.0 else None
    return (observed - expected) / (1 - expected)


def calculate(coder_a: dict[str, dict[str, str]], coder_b: dict[str, dict[str, str]]) -> dict[str, Any]:
    ids_a = set(coder_a)
    ids_b = set(coder_b)
    if ids_a != ids_b:
        missing_a = sorted(ids_b - ids_a)
        missing_b = sorted(ids_a - ids_b)
        raise ValueError(
            "coder files have different mipvu_id sets; "
            f"missing from coder A: {missing_a[:5]}, missing from coder B: {missing_b[:5]}"
        )

    full_pairs: list[tuple[str, str]] = []
    binary_pairs: list[tuple[str, str]] = []
    disagreements: list[dict[str, str]] = []
    for mipvu_id in sorted(ids_a):
        row_a = coder_a[mipvu_id]
        row_b = coder_b[mipvu_id]
        decision_a = row_a["decision_type"]
        decision_b = row_b["decision_type"]
        full_pairs.append((decision_a, decision_b))
        binary_pairs.append((binary(decision_a), binary(decision_b)))
        if decision_a != decision_b:
            disagreements.append(
                {
                    "mipvu_id": mipvu_id,
                    "document_id": row_a.get("document_id", ""),
                    "sentence_id": row_a.get("sentence_id", ""),
                    "lexical_unit": row_a.get("lexical_unit", ""),
                    "coder_a_decision": decision_a,
                    "coder_b_decision": decision_b,
                }
            )

    total = len(full_pairs)
    full_agreement = sum(1 for a, b in full_pairs if a == b) / total if total else None
    binary_agreement = sum(1 for a, b in binary_pairs if a == b) / total if total else None
    return {
        "status": "calculated",
        "coded_units": total,
        "binary_metaphor_related": {
            "percent_agreement": binary_agreement,
            "cohens_kappa": cohens_kappa(binary_pairs),
        },
        "decision_type": {
            "percent_agreement": full_agreement,
            "disagreement_count": len(disagreements),
        },
        "disagreements": disagreements,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coder-a", required=True, type=Path)
    parser.add_argument("--coder-b", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    result = calculate(read_coder_csv(args.coder_a), read_coder_csv(args.coder_b))
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
