#!/usr/bin/env python3
"""Extract priority Grande Armée bulletins from full-volume Gallica OCR tomes.

Reads cases/napoleon/corpus/raw/napoleon-src-02-grande-armee-bulletins/tome-N.txt
and writes individual bulletin files to the same directory.

Each extracted file gets a provenance header block.

Run: python3 scripts/extract-napoleon-bulletins.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BULLETINS_DIR = ROOT / "cases/napoleon/corpus/raw/napoleon-src-02-grande-armee-bulletins"

# ---------------------------------------------------------------------------
# Target bulletins: what we want to extract.
# Each entry: (slug, bulletin_number_or_pattern, tome_file, campaign, date_iso)
# bulletin_number_or_pattern: int for numbered series, or regex str for special cases.
# ---------------------------------------------------------------------------
TARGETS = [
    # Tome 11 — Austerlitz campaign (bulletins 1–37)
    {
        "slug": "napoleon-bulletin-1805-12-03-austerlitz",
        "tome": "tome-11.txt",
        "bulletin_num": 34,
        "date": "1805-12-03",
        "campaign": "Austerlitz",
        "correspondance_vol": 11,
        "selection_note": (
            "34th Bulletin, Grande Armée. Austerlitz, 10 December 1805. "
            "Post-battle dispatch announcing the victory at Austerlitz (2 Dec 1805). "
            "Key for sacrifice-economy analysis: army as sacred body, glory-death exchange."
        ),
    },
    {
        "slug": "napoleon-bulletin-1805-12-04-austerlitz-aftermath",
        "tome": "tome-11.txt",
        "bulletin_num": 35,
        "date": "1805-12-11",
        "campaign": "Austerlitz",
        "correspondance_vol": 11,
        "selection_note": (
            "35th Bulletin, Grande Armée. Brünn, 11 December 1805. "
            "Aftermath dispatch: Russian army retreat, prisoner lists, imperial magnanimity. "
            "Sacrificial economy at peak: death rendered meaningful by total victory."
        ),
    },
    # Tome 13 — Jena campaign 1806 (bulletins 1–35 in 1806 series)
    {
        "slug": "napoleon-bulletin-1806-10-15-jena",
        "tome": "tome-13.txt",
        "bulletin_num": 5,
        "date": "1806-10-15",
        "campaign": "Jena-Auerstedt",
        "correspondance_vol": 13,
        "selection_note": (
            "5th Bulletin, Grande Armée (1806 series). Gera, 15 October 1806. "
            "Battle of Jena-Auerstedt (14 Oct 1806): crushing Prussian defeat. "
            "Sacrificial economy at peak: Prussian army annihilated, gloire proclaimed."
        ),
    },
    {
        "slug": "napoleon-bulletin-1806-10-26-berlin",
        "tome": "tome-13.txt",
        "bulletin_num": 18,
        "date": "1806-10-26",
        "campaign": "Jena-Auerstedt",
        "correspondance_vol": 13,
        "selection_note": (
            "18th Bulletin, Grande Armée (1806 series). Berlin, 26 October 1806. "
            "Entry into Berlin after Jena. Aftermath of Prussian collapse. "
            "Imperial triumphalism at height — enemy capital occupied."
        ),
    },
    # Tome 14 — Eylau/winter 1807 (bulletins 36–68)
    {
        "slug": "napoleon-bulletin-1807-02-08-eylau",
        "tome": "tome-14.txt",
        "bulletin_num": 58,
        "date": "1807-02-09",
        "campaign": "Eylau",
        "correspondance_vol": 14,
        "selection_note": (
            "58th Bulletin, Grande Armée. Preussich-Eylau, 9 February 1807. "
            "Battle of Eylau (8 Feb 1807): brutal winter battle. "
            "Sacrifice language under stress: heavy French losses acknowledged, "
            "victory claimed but at obvious cost. Key transition document."
        ),
    },
    # Tome 15 — Friedland/Tilsit phase (bulletins 69–87)
    {
        "slug": "napoleon-bulletin-1807-06-14-friedland",
        "tome": "tome-15.txt",
        "bulletin_num": 79,
        "date": "1807-06-17",
        "campaign": "Friedland",
        "correspondance_vol": 15,
        "selection_note": (
            "79th Bulletin, Grande Armée. Wehlau, 17 June 1807. "
            "Battle of Friedland (14 June 1807): decisive victory ending War of the Fourth Coalition. "
            "Glory-sacrifice-patrie language at height of imperial power."
        ),
    },
    # Tome 24 — Russia 1812 (bulletins 26, 29th)
    {
        "slug": "napoleon-bulletin-1812-10-23-russia-advance",
        "tome": "tome-24.txt",
        "bulletin_num": 26,
        "date": "1812-10-23",
        "campaign": "Russia",
        "correspondance_vol": 24,
        "selection_note": (
            "26th Bulletin, Grande Armée. Borovsk, 23 October 1812. "
            "Covers post-Moskova movements and French occupation of Moscow. "
            "Sacrificial economy under strain: victory proclaimed but retreat imminent."
        ),
    },
    {
        "slug": "napoleon-bulletin-1812-12-03-russia-29th",
        "tome": "tome-24.txt",
        "bulletin_num_pattern": r"2ge\s*BULLETIN DE LA GRANDE ARM|29e\s*BULLETIN DE LA GRANDE ARM",
        "date": "1812-12-03",
        "campaign": "Russia (retreat)",
        "correspondance_vol": 24,
        "selection_note": (
            "29th Bulletin, Grande Armée. Molodetchna, 3 December 1812. "
            "Analytically critical: the collapse of the sacrificial economy. "
            "Army dissolved in retreat, cold, and starvation. Napoleon admits catastrophic losses. "
            "Core document for Koenigsberg sacrifice-law analysis."
        ),
    },
    # Tome 19 — Armée d'Allemagne 1809 (Wagram campaign; different bulletin title)
    {
        "slug": "napoleon-bulletin-1809-07-08-wagram",
        "tome": "tome-19.txt",
        "bulletin_num_pattern": r"15505\.",
        "date": "1809-07-08",
        "campaign": "Wagram",
        "correspondance_vol": 19,
        "selection_note": (
            "25th Bulletin de l'Armée d'Allemagne. Wolkersdorf, 8 July 1809. "
            "Battles of Enzersdorf and Wagram (5–6 July 1809): decisive victory over Austria. "
            "Note: titled 'Armée d'Allemagne' not 'Grande Armée' — 1809 campaign designation."
        ),
    },
    # Tome 25 — Grande Armée 1813 (Germany campaign)
    # Note: Lützen bulletin (no. 19951) is in the same tome but dropped as out-of-scope.
    {
        "slug": "napoleon-bulletin-1813-05-24-bautzen",
        "tome": "tome-25.txt",
        "bulletin_num_pattern": r"20042\.\s*[—-]\s*BULLETIN\s+DE\s+LA\s+GRANDE\s+ARM",
        "date": "1813-05-24",
        "campaign": "Bautzen 1813",
        "correspondance_vol": 25,
        "selection_note": (
            "Bulletin de la Grande Armée. Görlitz, 24 May 1813. "
            "Battle of Bautzen (20–21 May 1813): victory but enemy army escapes intact. "
            "Sacrifice language under late-empire strain — the exchange is visibly failing."
        ),
    },
]

# All known bulletins are now extracted
MISSING_BULLETINS = []


def build_provenance_header(target: dict, bulletin_heading: str, tome_path: Path) -> str:
    slug = target["slug"]
    return (
        f"SOURCE: Correspondance de Napoléon Ier, Plon, Paris, 1858–1870\n"
        f"VOLUME: Tome {target['correspondance_vol']}\n"
        f"ARCHIVE: Bibliothèque nationale de France / Gallica\n"
        f"TOME_FILE: {tome_path.name}\n"
        f"SLUG: {slug}\n"
        f"DATE: {target['date']}\n"
        f"CAMPAIGN: {target['campaign']}\n"
        f"RIGHTS: Public domain (original pre-1821; Plon edition pre-1900; BnF open access)\n"
        f"EXTRACTION_TOOL: scripts/extract-napoleon-bulletins.py\n"
        f"SELECTION_NOTE: {target['selection_note']}\n"
        f"BULLETIN_HEADING: {bulletin_heading.strip()}\n"
        f"{'=' * 72}\n"
    )


def find_bulletin_by_number(lines: list[str], num: int) -> int | None:
    """Return line index of the heading for bulletin number `num`."""
    # Match e.g. "34e BULLETIN DE LA GRANDE ARMÉE." or "1er BULLETIN..."
    suffix = "er" if num == 1 else "e"
    pattern = re.compile(
        rf"(?:^\d+\.\s*—\s*)?{num}{suffix}\s+BULLETIN\s+DE\s+LA\s+GRANDE\s+ARM",
        re.IGNORECASE,
    )
    for i, line in enumerate(lines):
        if pattern.search(line.strip()):
            return i
    return None


def find_bulletin_by_pattern(lines: list[str], pattern_str: str) -> int | None:
    pattern = re.compile(pattern_str, re.IGNORECASE)
    for i, line in enumerate(lines):
        if pattern.search(line.strip()):
            return i
    return None


def find_next_bulletin_or_section(lines: list[str], start: int) -> int:
    """Find where the next bulletin or major section begins after `start`."""
    # A new bulletin heading or a clear section break (line with only digits/roman)
    heading_pattern = re.compile(
        r"BULLETIN\s+DE\s+LA\s+GRANDE\s+ARM|\d+e?\s+BULLETIN\s+DE",
        re.IGNORECASE,
    )
    # Also stop at long sequences of digits (table of contents / index entries)
    for i in range(start + 5, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
        if heading_pattern.search(line):
            return i
        # Stop at index/table entries that look like "12345. — TITRE" (new numbered item)
        if re.match(r"^\d{4,5}\s*\.\s*—", line) and i > start + 20:
            return i
    return len(lines)


def extract_bulletin(target: dict) -> tuple[bool, str]:
    tome_path = BULLETINS_DIR / target["tome"]
    if not tome_path.exists():
        return False, f"Tome file not found: {tome_path}"

    lines = tome_path.read_text(encoding="utf-8").splitlines(keepends=True)

    # Find the bulletin heading
    if "bulletin_num" in target:
        start = find_bulletin_by_number(lines, target["bulletin_num"])
    else:
        start = find_bulletin_by_pattern(lines, target["bulletin_num_pattern"])

    if start is None:
        return False, f"Bulletin not found in {target['tome']}"

    heading = lines[start].strip()
    end = find_next_bulletin_or_section(lines, start)

    body_lines = lines[start:end]
    # Strip trailing blank lines
    while body_lines and not body_lines[-1].strip():
        body_lines.pop()

    body = "".join(body_lines).strip()

    provenance = build_provenance_header(target, heading, tome_path)
    full_text = provenance + "\n" + body + "\n"

    out_path = BULLETINS_DIR / f"{target['slug']}.txt"
    out_path.write_text(full_text, encoding="utf-8")

    word_count = len(body.split())
    return True, f"Wrote {out_path.name} ({word_count} words, lines {start}–{end})"


def main() -> int:
    print("=== Napoleon Grande Armée Bulletin Extraction ===\n")

    ok_count = 0
    fail_count = 0

    for target in TARGETS:
        slug = target["slug"]
        success, msg = extract_bulletin(target)
        if success:
            print(f"  [OK]      {slug}")
            print(f"            {msg}")
            ok_count += 1
        else:
            print(f"  [MISSING] {slug}")
            print(f"            {msg}")
            fail_count += 1

    if MISSING_BULLETINS:
        print(f"\n--- Bulletins requiring additional Gallica downloads ---")
        for m in MISSING_BULLETINS:
            print(f"  [NEEDS DL] {m['slug']} ({m['date']})")
            print(f"             {m.get('needs_tome', 'unknown tome')}")

    print(f"\nResult: {ok_count} extracted, {fail_count} failed, {len(MISSING_BULLETINS)} need additional downloads")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
