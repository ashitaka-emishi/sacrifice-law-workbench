#!/usr/bin/env python3
"""Extract the approved French Revolution draft corpus from Gutenberg 29887."""
from __future__ import annotations

import argparse
import textwrap
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://www.gutenberg.org/cache/epub/29887/pg29887.txt"
SOURCE_PAGE = "https://www.gutenberg.org/ebooks/29887"
OUT_DIR = ROOT / "cases" / "fr-rev" / "corpus" / "raw" / "fr-rev-src-01-robespierre-discours-pg"
SEP = "=" * 72


@dataclass(frozen=True)
class Speech:
    document_id: str
    title: str
    start_marker: str
    end_marker: str
    start_min: int
    required_phrases: tuple[str, ...]
    output_name: str


SPEECHES = (
    Speech(
        document_id="fr-rev-robespierre-political-morality",
        title="Report on the Principles of Political Morality",
        start_marker="_Rapport sur les principes de morale politique",
        end_marker="_Rapport fait au nom du Comité de salut public, par Maximilien",
        start_min=100_000,
        required_phrases=("morale politique", "ressort du gouvernement populaire", "peuple"),
        output_name="fr-rev-robespierre-political-morality.txt",
    ),
    Speech(
        document_id="fr-rev-robespierre-religious-moral-ideas",
        title="Report on Religious and Moral Ideas and National Festivals",
        start_marker="_Rapport fait au nom du Comité de salut public, par Maximilien",
        end_marker="_Discours du 8 Thermidor",
        start_min=100_000,
        required_phrases=("idées religieuses et morales", "Etre suprême", "fêtes nationales"),
        output_name="fr-rev-robespierre-religious-moral-ideas.txt",
    ),
)


def fetch_text() -> str:
    request = urllib.request.Request(
        SOURCE_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; koenigsberg-sacrifice-workbench/1.0; "
                "scholarly research; +https://github.com/)"
            )
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        text = response.read().decode("utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def extract(text: str, speech: Speech) -> str:
    start = text.find(speech.start_marker, speech.start_min)
    if start < 0:
        raise ValueError(f"{speech.document_id}: missing start marker {speech.start_marker!r}")
    end = text.find(speech.end_marker, start + len(speech.start_marker))
    if end < 0:
        raise ValueError(f"{speech.document_id}: missing end marker {speech.end_marker!r}")
    body = text[start:end].strip()
    missing = [phrase for phrase in speech.required_phrases if phrase not in body]
    if missing:
        raise ValueError(f"{speech.document_id}: missing required phrase(s): {', '.join(missing)}")
    return body


def provenance_header(speech: Speech) -> str:
    return textwrap.dedent(
        f"""\
        SOURCE: Project Gutenberg
        EBOOK: 29887
        SOURCE_PAGE: {SOURCE_PAGE}
        URL: {SOURCE_URL}
        DOCUMENT_ID: {speech.document_id}
        TITLE: {speech.title}
        RIGHTS: Public domain
        EXTRACTION_TOOL: scripts/extract-fr-rev-speeches.py
        EXTRACTION_POLICY: French source text extracted from approved Project Gutenberg source; English glosses only.
        {SEP}
        """
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Validate extraction markers without writing files")
    args = parser.parse_args()

    source = fetch_text()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for speech in SPEECHES:
        body = extract(source, speech)
        word_count = len(body.split())
        out_path = OUT_DIR / speech.output_name
        if not args.dry_run:
            out_path.write_text(provenance_header(speech) + body + "\n", encoding="utf-8")
        rel = out_path.relative_to(ROOT)
        action = "would write" if args.dry_run else "wrote"
        print(f"{action} {rel} ({word_count} words)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
