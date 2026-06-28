#!/usr/bin/env python3
"""Extract targeted #180 existing-case additions from pinned source editions."""
from __future__ import annotations

import argparse
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEP = "=" * 72


@dataclass(frozen=True)
class ExtractSpec:
    document_id: str
    title: str
    source_name: str
    source_url: str
    source_page: str
    citation: str
    source_kind: str
    start_marker: str
    end_marker: str
    start_min: int
    required_phrases: tuple[str, ...]
    output_path: Path
    language: str = "en"
    rights: str = "Public domain"
    policy_note: str = ""


URL_CACHE = {
    "https://www.gutenberg.org/cache/epub/9/pg9.txt": Path("/tmp/pg9.txt"),
    "https://www.gutenberg.org/cache/epub/2657/pg2657.txt": Path("/tmp/pg2657.txt"),
}


DOCS = (
    ExtractSpec(
        document_id="lincoln-first-inaugural",
        title="First Inaugural Address",
        source_name="Project Gutenberg EBook #9",
        source_url="https://www.gutenberg.org/cache/epub/9/pg9.txt",
        source_page="https://www.gutenberg.org/ebooks/9",
        citation="Lincoln, Abraham. Abraham Lincoln's First Inaugural Address. Project Gutenberg EBook #9.",
        source_kind="url",
        start_marker="Lincoln’s First Inaugural Address\n\nMarch 4, 1861",
        end_marker="*** END",
        start_min=0,
        required_phrases=("Apprehension seems to exist", "Physically speaking, we cannot separate", "mystic chords"),
        output_path=ROOT / "cases" / "lincoln" / "corpus" / "raw" / "lincoln-src-04-first-inaugural.txt",
        policy_note="Standalone public-domain transcription; no modern editorial notes retained.",
    ),
    ExtractSpec(
        document_id="lincoln-special-message-1861-07-04",
        title="Message to Congress in Special Session, July 4, 1861",
        source_name="Project Gutenberg EBook #2657",
        source_url="https://www.gutenberg.org/cache/epub/2657/pg2657.txt",
        source_page="https://www.gutenberg.org/ebooks/2657",
        citation=(
            "Lincoln, Abraham. The Papers and Writings of Abraham Lincoln, Volume 5: "
            "1858-1862. Project Gutenberg EBook #2657."
        ),
        source_kind="url",
        start_marker="MESSAGE TO CONGRESS IN SPECIAL SESSION,\n\nJULY 4, 1861.",
        end_marker="\nBY THE PRESIDENT OF THE UNITED STATES",
        start_min=400_000,
        required_phrases=("FELLOW-CITIZENS OF THE SENATE", "The Union is older than any of the States", "rebellion thus sugar-coated"),
        output_path=ROOT / "cases" / "lincoln" / "corpus" / "raw" / "lincoln-src-05-special-message-1861-07-04.txt",
        policy_note="Extracted from a public-domain Lincoln writings volume; unrelated volume content omitted.",
    ),
    ExtractSpec(
        document_id="napoleon-proclamation-army-of-italy-1796-11-11",
        title="Proclamation to the Army of Italy, 11 November 1796",
        source_name="Correspondance de Napoleon Ier, tome 2",
        source_url="cases/napoleon/corpus/raw/napoleon-src-01-early-correspondence/tome-2.txt",
        source_page="https://gallica.bnf.fr/ark:/12148/bpt6k6295821n",
        citation=(
            "Napoleon Bonaparte. Proclamation, quartier general, San-Massimo, "
            "21 brumaire an V (11 novembre 1796), no. 1180. Correspondance de "
            "Napoleon Ier, tome 2. Paris: H. Plon, 1858-1870. Gallica/BnF."
        ),
        source_kind="local",
        start_marker="1180. - PROCLAMATION.",
        end_marker="Dépôt de la guerre.\n\n1181",
        start_min=200_000,
        required_phrases=("Mantoue est sans pain", "La liberté de l'Italie", "la plus brave et de la plus puissante nation"),
        output_path=ROOT
        / "cases"
        / "napoleon"
        / "corpus"
        / "raw"
        / "napoleon-src-03-army-of-italy-proclamation"
        / "napoleon-proclamation-army-of-italy-1796-11-11.txt",
        language="fr",
        policy_note="French source text from pinned Gallica/Plon public-domain edition; English glosses only.",
    ),
)


def fetch_text(spec: ExtractSpec) -> str:
    if spec.source_kind == "local":
        path = ROOT / spec.source_url
        return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")

    cache = URL_CACHE.get(spec.source_url)
    if cache and cache.exists() and cache.stat().st_size > 1000:
        return cache.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")

    result = subprocess.run(
        [
            "curl",
            "--fail",
            "--location",
            "--max-time",
            "45",
            "--user-agent",
            "Mozilla/5.0 (compatible; koenigsberg-sacrifice-workbench/1.0; scholarly research)",
            spec.source_url,
        ],
        capture_output=True,
        check=True,
    )
    text = result.stdout.decode("utf-8-sig", errors="replace")
    if cache:
        cache.write_text(text, encoding="utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def extract(text: str, spec: ExtractSpec) -> str:
    start = text.find(spec.start_marker, spec.start_min)
    if start < 0:
        raise ValueError(f"{spec.document_id}: missing start marker {spec.start_marker!r}")
    end = text.find(spec.end_marker, start + len(spec.start_marker))
    if end < 0:
        raise ValueError(f"{spec.document_id}: missing end marker {spec.end_marker!r}")
    body = text[start:end].strip()
    if spec.document_id.startswith("napoleon-"):
        body = body + "\n\nDépôt de la guerre."
    missing = [phrase for phrase in spec.required_phrases if phrase not in body]
    if missing:
        raise ValueError(f"{spec.document_id}: missing required phrase(s): {', '.join(missing)}")
    return "\n".join(line.rstrip() for line in body.splitlines())


def provenance_header(spec: ExtractSpec) -> str:
    url = spec.source_page if spec.source_kind == "local" else spec.source_url
    source_file = f"SOURCE_FILE: {spec.source_url}\n" if spec.source_kind == "local" else ""
    return textwrap.dedent(
        f"""\
        SOURCE: {spec.source_name}
        SOURCE_PAGE: {spec.source_page}
        URL: {url}
        {source_file}\
        CITATION: {spec.citation}
        DOCUMENT_ID: {spec.document_id}
        TITLE: {spec.title}
        LANGUAGE: {spec.language}
        RIGHTS: {spec.rights}
        EXTRACTION_TOOL: scripts/extract-targeted-existing-case-docs.py
        EXTRACTION_POLICY: {spec.policy_note}
        {SEP}
        """
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Validate extraction markers without writing files")
    parser.add_argument("--doc", help="Extract a single document_id")
    args = parser.parse_args()

    for spec in DOCS:
        if args.doc and spec.document_id != args.doc:
            continue
        body = extract(fetch_text(spec), spec)
        word_count = len(body.split())
        if not args.dry_run:
            spec.output_path.parent.mkdir(parents=True, exist_ok=True)
            spec.output_path.write_text(provenance_header(spec) + body + "\n", encoding="utf-8")
        action = "would write" if args.dry_run else "wrote"
        print(f"{action} {spec.output_path.relative_to(ROOT)} ({word_count} words)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
