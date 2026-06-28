#!/usr/bin/env python3
"""Extract the approved British WWI / Lloyd George draft corpus from IA OCR."""
from __future__ import annotations

import argparse
import textwrap
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEP = "=" * 72


@dataclass(frozen=True)
class Source:
    source_key: str
    title: str
    source_page: str
    source_url: str
    citation: str


@dataclass(frozen=True)
class Speech:
    document_id: str
    title: str
    source_key: str
    start_marker: str
    end_marker: str
    start_min: int
    required_phrases: tuple[str, ...]
    output_dir: Path
    output_name: str


SOURCES = {
    "wwi-britain-src-01-through-terror-to-triumph": Source(
        source_key="wwi-britain-src-01-through-terror-to-triumph",
        title="Through Terror to Triumph",
        source_page="https://archive.org/details/throughterrortot00lloyuoft",
        source_url="https://archive.org/download/throughterrortot00lloyuoft/throughterrortot00lloyuoft_djvu.txt",
        citation=(
            "Lloyd George, David. Through Terror to Triumph: Speeches and "
            "Pronouncements of the Right Hon. David Lloyd George, M.P., Since "
            "the Beginning of the War. 1915. Internet Archive."
        ),
    ),
    "wwi-britain-src-02-great-crusade": Source(
        source_key="wwi-britain-src-02-great-crusade",
        title="The Great Crusade",
        source_page="https://archive.org/details/greatcrusadeextr00lloy",
        source_url="https://archive.org/download/greatcrusadeextr00lloy/greatcrusadeextr00lloy_djvu.txt",
        citation=(
            "Lloyd George, David. The Great Crusade: Extracts from Speeches "
            "Delivered During the War. 1918. Internet Archive."
        ),
    ),
}

OUT_ROOT = ROOT / "cases" / "wwi-britain" / "corpus" / "raw"

SPEECHES = (
    Speech(
        document_id="wwi-britain-lloyd-george-through-terror-to-triumph",
        title='Through Terror to Triumph!',
        source_key="wwi-britain-src-01-through-terror-to-triumph",
        start_marker='CHAPTER  I \n\n"  THROUGH',
        end_marker="CHAPTER  II",
        start_min=15_000,
        required_phrases=("THROUGH  TERROR", "Belgium", "Sacrifice"),
        output_dir=OUT_ROOT / "wwi-britain-src-01-through-terror-to-triumph",
        output_name="wwi-britain-lloyd-george-through-terror-to-triumph.txt",
    ),
    Speech(
        document_id="wwi-britain-lloyd-george-winning-this-war",
        title="Winning This War",
        source_key="wwi-britain-src-02-great-crusade",
        start_marker="WINNING  THIS  WAR.",
        end_marker="SECRETARY  OF  STATE  FOR  WAR",
        start_min=15_000,
        required_phrases=("WINNING  THIS  WAR", "unity", "munitions"),
        output_dir=OUT_ROOT / "wwi-britain-src-02-great-crusade",
        output_name="wwi-britain-lloyd-george-winning-this-war.txt",
    ),
    Speech(
        document_id="wwi-britain-lloyd-george-entry-america",
        title="Entry of America into the War",
        source_key="wwi-britain-src-02-great-crusade",
        start_marker="ENTRY  OF  AMERICA  INTO  THE  WAR.",
        end_marker="THE  WAR  AND  THE  EMPIRE",
        start_min=160_000,
        required_phrases=("ENTRY  OF  AMERICA", "liberty", "America"),
        output_dir=OUT_ROOT / "wwi-britain-src-02-great-crusade",
        output_name="wwi-britain-lloyd-george-entry-america.txt",
    ),
    Speech(
        document_id="wwi-britain-lloyd-george-causes-aims-war",
        title="Restatement of the Causes and Aims of the War",
        source_key="wwi-britain-src-02-great-crusade",
        start_marker="RESTATEMENT  OF  THE  CAUSES  AND  AIMS  OF",
        end_marker="VICTORY  WILL  COME",
        start_min=190_000,
        required_phrases=("RESTATEMENT  OF", "justice", "Belgium"),
        output_dir=OUT_ROOT / "wwi-britain-src-02-great-crusade",
        output_name="wwi-britain-lloyd-george-causes-aims-war.txt",
    ),
)


def fetch_text(source: Source) -> str:
    request = urllib.request.Request(
        source.source_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; koenigsberg-sacrifice-workbench/1.0; "
                "scholarly research; +https://github.com/)"
            )
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        text = response.read().decode("utf-8-sig", errors="replace")
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
    return "\n".join(line.rstrip() for line in body.splitlines())


def provenance_header(speech: Speech, source: Source) -> str:
    return textwrap.dedent(
        f"""\
        SOURCE: Internet Archive
        ARCHIVE_ITEM: {source.title}
        SOURCE_PAGE: {source.source_page}
        URL: {source.source_url}
        CITATION: {source.citation}
        DOCUMENT_ID: {speech.document_id}
        TITLE: {speech.title}
        RIGHTS: Public domain (pre-1929 edition; OCR from Internet Archive)
        EXTRACTION_TOOL: scripts/extract-wwi-britain-speeches.py
        EXTRACTION_POLICY: English OCR source text extracted from approved Internet Archive source; OCR review still required before publication-grade claims.
        {SEP}
        """
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Validate extraction markers without writing files")
    args = parser.parse_args()

    cache: dict[str, str] = {}
    for speech in SPEECHES:
        source = SOURCES[speech.source_key]
        if source.source_key not in cache:
            cache[source.source_key] = fetch_text(source)
        body = extract(cache[source.source_key], speech)
        word_count = len(body.split())
        out_path = speech.output_dir / speech.output_name
        if not args.dry_run:
            speech.output_dir.mkdir(parents=True, exist_ok=True)
            out_path.write_text(provenance_header(speech, source) + body + "\n", encoding="utf-8")
        rel = out_path.relative_to(ROOT)
        action = "would write" if args.dry_run else "wrote"
        print(f"{action} {rel} ({word_count} words)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
