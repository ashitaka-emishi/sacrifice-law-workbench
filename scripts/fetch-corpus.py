#!/usr/bin/env python3
"""Fetch raw corpus files for all curl-accessible sources.

Handles:
  - Project Gutenberg plain-text downloads (lincoln, am-rev paine/declaration)
  - Gallica texteBrut OCR downloads (napoleon bulletins)
  - Archive.org djvu text downloads (hitler mein kampf chapters)

Does NOT handle:
  - Founders Online (JS-rendered — use corpus-download skill with Playwright)
  - Gallica CAPTCHA fallback (handled by corpus-download skill)
  - Hitler speeches (gitignored, placed manually)

Usage:
  python3 scripts/fetch-corpus.py                        # all curl-accessible docs
  python3 scripts/fetch-corpus.py --case lincoln          # one case
  python3 scripts/fetch-corpus.py --doc lincoln-gettysburg-address
  python3 scripts/fetch-corpus.py --force                 # re-fetch even if present
  python3 scripts/fetch-corpus.py --dry-run               # show plan, fetch nothing
  python3 scripts/fetch-corpus.py --json                  # machine-readable results

After fetching, runs verify-corpus.py automatically for each affected case.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import textwrap
import time
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline_common import (
    ROOT,
    CASES_ROOT,
    case_ids,
    now_iso,
    documents,
    raw_path_for,
    document_id,
    read_json,
    write_json,
)

# ---------------------------------------------------------------------------
# Domain routing
# ---------------------------------------------------------------------------

def classify(case_id: str, doc: dict) -> str:
    """Return the fetch strategy for a document."""
    url = doc.get("source_url") or ""
    citation = doc.get("source_citation") or ""
    doc_id = document_id(doc)
    rights = doc.get("rights_status") or ""

    if case_id == "hitler" and doc_id in MK_CHAPTERS:
        return "archive-org"
    if "gutenberg.org" in url:
        return "gutenberg"
    if "archives.gov/founding-docs" in url:
        return "archives-gov"
    if "gallica.bnf.fr" in url:
        return "gallica"
    if "founders.archives.gov" in url:
        return "founders-playwright"
    if rights == "gitignored-local-fair-use" and case_id == "hitler":
        return "gitignored-manual"
    if "archive.org" in url or "mein-kampf-german" in citation:
        return "archive-org"
    return "unknown"


# ---------------------------------------------------------------------------
# URL maps (curl-only strategies)
# ---------------------------------------------------------------------------

GUTENBERG_URLS: dict[str, str] = {
    "lincoln-lyceum-address":     "https://www.gutenberg.org/cache/epub/3253/pg3253.txt",
    "lincoln-gettysburg-address": "https://www.gutenberg.org/cache/epub/4/pg4.txt",
    "lincoln-second-inaugural":   "https://www.gutenberg.org/cache/epub/8/pg8.txt",
    "am-rev-paine-common-sense":  "https://www.gutenberg.org/cache/epub/147/pg147.txt",
}

ARCHIVES_GOV_URLS: dict[str, str] = {
    "am-rev-jefferson-declaration": "https://www.archives.gov/founding-docs/declaration-transcript",
}

ARCHIVE_ORG_MK_URL = (
    "https://archive.org/download/mein-kampf-german_202412/Mein_Kampf_German_djvu.txt"
)
ARCHIVE_ORG_CACHE = Path("/tmp/mk_german_eher1943.txt")

MK_CHAPTERS: dict[str, dict] = {
    "hitler-mein-kampf-vol1-ch2-wien": {
        "start_marker": "Wiener Lehr- und Leidensjahre",
        "start_min": 85_000,
        "end_marker": "3. Kapitel",
        "end_min_offset": 1000,
        "title": "Band I, Kapitel 2: Wiener Lehr- und Leidensjahre",
    },
    "hitler-mein-kampf-vol1-ch11-race-and-people": {
        "start_marker": "Volk und Rasse",
        "start_min": 650_000,
        "end_marker": "12. Kapitel",
        "end_min_offset": 1000,
        "title": "Band I, Kapitel 11: Volk und Rasse",
    },
    "hitler-mein-kampf-vol1-ch12-nsdap": {
        "start_marker": "Die erste Entwicklungszeit der National-",
        "start_min": 780_000,
        "end_marker": "Zweiter Band",
        "end_min_offset": 1000,
        "title": "Band I, Kapitel 12: Die erste Entwicklungszeit der NSDAP",
    },
    "hitler-mein-kampf-vol2-ch1-weltanschauung": {
        "start_marker": "Weltanschauung und Partei",
        "start_min": 870_000,
        "end_marker": "Der Staat",
        "end_min_offset": 1000,
        "title": "Band II, Kapitel 1: Weltanschauung und Partei",
    },
    "hitler-mein-kampf-vol2-ch2-the-state": {
        "start_marker": "Der Staat",
        "start_min": 910_000,
        "end_marker": "3. Kapitel",
        "end_min_offset": 1000,
        "title": "Band II, Kapitel 2: Der Staat",
    },
    "hitler-mein-kampf-vol2-ch14-eastern-europe": {
        "start_marker": "Ostorientierung oder Ostpolitik",
        "start_min": 1_490_000,
        "end_marker": "15. Kapitel",
        "end_min_offset": 1000,
        "title": "Band II, Kapitel 14: Ostorientierung oder Ostpolitik",
    },
}

_URL_RE = re.compile(r"https?://[^\s)>,;]+")


def planned_fetch_url(strategy: str, doc: dict) -> str:
    """Return the concrete URL this script will download for a strategy."""
    doc_id = document_id(doc)
    if strategy == "gutenberg":
        return GUTENBERG_URLS.get(doc_id, "")
    if strategy == "archives-gov":
        return ARCHIVES_GOV_URLS.get(doc_id) or doc.get("source_url", "")
    if strategy == "archive-org" and doc_id in MK_CHAPTERS:
        return ARCHIVE_ORG_MK_URL
    return ""


def extract_raw_provenance_url(raw_path: Path) -> str:
    """Read the first provenance block and return the first URL-like value."""
    if not raw_path.exists():
        return ""
    try:
        header = raw_path.read_text(encoding="utf-8", errors="replace").splitlines()[:40]
    except OSError:
        return ""
    for line in header:
        match = _URL_RE.search(line)
        if match:
            return match.group(0)
    return ""


def update_manifest_source_url(case_id: str, doc_id: str, actual_url: str) -> bool:
    """Persist the actual downloaded document URL back into the manifest."""
    if not actual_url:
        return False

    manifest_path = CASES_ROOT / case_id / "metadata" / "document-manifest.json"
    manifest = read_json(manifest_path, {}) or {}
    docs = manifest.get("documents")
    if not isinstance(docs, list):
        return False

    for doc in docs:
        if isinstance(doc, dict) and document_id(doc) == doc_id:
            if doc.get("source_url") == actual_url:
                return False
            doc["source_url"] = actual_url
            write_json(manifest_path, manifest)
            return True
    return False

# ---------------------------------------------------------------------------
# curl helper
# ---------------------------------------------------------------------------

def curl_fetch(url: str, dest: Path, timeout: int = 60, retries: int = 2) -> tuple[bool, str]:
    """Download url to dest using urllib. Returns (success, detail_message)."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; koenigsberg-sacrifice-workbench/1.0; "
            "scholarly research; +https://github.com/)"
        )
    }
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return True, f"{len(data):,} bytes"
        except urllib.error.HTTPError as exc:
            if attempt < retries and exc.code in (429, 503):
                time.sleep(3 * (attempt + 1))
                continue
            return False, f"HTTP {exc.code}: {exc.reason}"
        except Exception as exc:
            if attempt < retries:
                time.sleep(2)
                continue
            return False, str(exc)
    return False, "max retries exceeded"


# ---------------------------------------------------------------------------
# Provenance header helpers
# ---------------------------------------------------------------------------

SEP = "=" * 72


def gutenberg_provenance(doc_id: str, url: str, ebook_num: str) -> str:
    return textwrap.dedent(f"""\
        SOURCE: Project Gutenberg
        EBOOK: {ebook_num}
        URL: {url}
        DOCUMENT_ID: {doc_id}
        RIGHTS: Public domain
        EXTRACTION_TOOL: scripts/fetch-corpus.py
        {SEP}
        """)


def archives_gov_provenance(doc_id: str, url: str) -> str:
    return textwrap.dedent(f"""\
        SOURCE: National Archives and Records Administration
        URL: {url}
        DOCUMENT_ID: {doc_id}
        RIGHTS: Public domain (U.S. Government publication)
        EXTRACTION_TOOL: scripts/fetch-corpus.py
        {SEP}
        """)


def gallica_provenance(doc_id: str, ark: str, tome: int, doc_meta: dict, url: str) -> str:
    return textwrap.dedent(f"""\
        SOURCE: Correspondance de Napoléon Ier, Plon, Paris, 1858–1870
        VOLUME: Tome {tome}
        ARCHIVE: Bibliothèque nationale de France / Gallica
        ARK: {ark}
        URL: {url}
        ITEM_URL: https://gallica.bnf.fr/ark:/12148/{ark}
        DOCUMENT_ID: {doc_id}
        RIGHTS: Public domain (pre-1821 original; pre-1900 Plon edition; BnF open access)
        EXTRACTION_TOOL: scripts/fetch-corpus.py
        {SEP}
        """)


def mk_provenance(doc_id: str, title: str) -> str:
    return textwrap.dedent(f"""\
        SOURCE: Mein Kampf, Adolf Hitler. Zentralverlag der NSDAP., Frz. Eher Nachf., G.m.b.H., München.
        EDITION: 851.–855. Auflage, 1943
        ARCHIVE: Archive.org
        ITEM: mein-kampf-german_202412 (djvu OCR)
        URL: https://archive.org/download/mein-kampf-german_202412/Mein_Kampf_German_djvu.txt
        DOCUMENT_ID: {doc_id}
        CHAPTER: {title}
        RIGHTS: U.S. copyright expired 2020 (95yr from 1925/1926). Public domain.
        LOCAL_USE: gitignored — scholarly annotation only; not committed, not published.
        EXTRACTION_TOOL: scripts/fetch-corpus.py
        {SEP}
        """)


# ---------------------------------------------------------------------------
# Cleaning passes
# ---------------------------------------------------------------------------

def clean_gutenberg(raw: str) -> str:
    """Strip Gutenberg header/footer boilerplate."""
    # Strip everything up to and including the START line
    match = re.search(r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", raw, re.I)
    if match:
        raw = raw[match.end():].lstrip()

    # Strip from END line onward
    match = re.search(r"\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG", raw, re.I)
    if match:
        raw = raw[: match.start()].rstrip()

    return re.sub(r"\n{3,}", "\n\n", raw).strip()


def clean_archives_gov(raw: str) -> str:
    """Extract Declaration text from NARA transcript page HTML."""
    # NARA serves HTML — extract the text body between the transcript markers
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&#\d+;", "", text)

    # Find the declaration text — starts with "IN CONGRESS" or "The unanimous Declaration"
    match = re.search(r"(IN CONGRESS|The unanimous Declaration)", text, re.I)
    if match:
        text = text[match.start():]

    # Trim at common footer markers
    for marker in ["Transcription", "Note:", "Source:", "This page was last"]:
        cut = text.find(marker)
        if cut > 500:
            text = text[:cut]

    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]{2,}", " ", text)).strip()


def extract_gallica_ark(source_url: str) -> str:
    """Pull the ARK identifier from a Gallica URL."""
    match = re.search(r"ark:/12148/([^/?\s]+)", source_url)
    return match.group(1) if match else ""


def get_gallica_page_count(ark: str) -> int | None:
    """Fetch Gallica item page and extract page count."""
    url = f"https://gallica.bnf.fr/ark:/12148/{ark}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "research-bot/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        match = re.search(r"(\d+)\s*page", html, re.I)
        return int(match.group(1)) if match else None
    except Exception:
        return None


def fetch_gallica_textebrut(ark: str) -> tuple[bool, str, str, str]:
    """Try to fetch the full texteBrut for a Gallica item.
    Returns (success, text_or_error, detail, actual_url).
    """
    page_count = get_gallica_page_count(ark)
    if not page_count:
        # Fall back to a large page range that works for most tomes
        page_count = 800

    url = f"https://gallica.bnf.fr/ark:/12148/{ark}/f9.image/f1n{page_count}.texteBrut"
    tmp = Path(f"/tmp/gallica_{ark}.txt")
    ok, detail = curl_fetch(url, tmp, timeout=90)
    if not ok:
        return False, "", f"curl failed: {detail}", url

    raw = tmp.read_text(encoding="utf-8", errors="replace")

    # Detect CAPTCHA page
    if "Vérification de sécurité" in raw or len(raw) < 10_000:
        return False, raw, "captcha-or-empty", url

    return True, raw, f"{len(raw):,} chars from {url}", url


def extract_bulletin(tome_text: str, doc_id: str, doc_meta: dict) -> str | None:
    """Extract a single bulletin from a full Gallica tome text."""
    # Use extraction_script hint from manifest if present; otherwise use the
    # bulletin number from the document notes/title to locate the heading.
    # Strategy: locate the bulletin heading by number in the text.
    num = doc_meta.get("bulletin_number")
    if num is None:
        # Try to parse from document_id date pattern — not reliable; just search broadly
        return None

    suffix = "er" if num == 1 else "e"
    # Gallica OCR varies: "34e BULLETIN", "34. - BULLETIN", "XXXIV. BULLETIN", etc.
    patterns = [
        re.compile(
            rf"(?:\d+\.\s*[—\-]\s*)?{num}{suffix}\s+BULLETIN\s+DE\s+LA\s+GRANDE\s+ARM",
            re.I,
        ),
        re.compile(
            rf"\b{num}\s*[—\-\.]\s*BULLETIN\s+DE\s+(?:LA|L[''])\s*(?:GRANDE\s+ARM|ARM[ÉE]E)",
            re.I,
        ),
    ]

    lines = tome_text.split("\n")
    start = None
    for i, line in enumerate(lines):
        for pat in patterns:
            if pat.search(line.strip()):
                start = i
                break
        if start is not None:
            break

    if start is None:
        return None

    # Find end: next bulletin heading or next Correspondance entry number
    next_bulletin = re.compile(r"BULLETIN\s+DE\s+(?:LA|L['’])\s*GRANDE\s+ARM", re.I)
    next_entry = re.compile(r"^\d{4,5}\s*\.\s*—")
    end = len(lines)
    for i in range(start + 5, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
        if next_bulletin.search(line) and i > start + 10:
            end = i
            break
        if next_entry.match(line) and i > start + 20:
            end = i
            break

    while end > start and not lines[end - 1].strip():
        end -= 1

    return "\n".join(lines[start:end]).strip()


# ---------------------------------------------------------------------------
# Per-strategy fetch functions
# ---------------------------------------------------------------------------

def fetch_gutenberg(case_id: str, doc: dict, out_path: Path, dry_run: bool) -> dict:
    doc_id = document_id(doc)
    url = GUTENBERG_URLS.get(doc_id)
    if not url:
        return {"status": "skip", "reason": "no gutenberg URL mapped for this doc_id"}

    if dry_run:
        return {"status": "dry-run", "url": url, "out": str(out_path)}

    tmp = Path(f"/tmp/gutenberg_{doc_id}.txt")
    ok, detail = curl_fetch(url, tmp)
    if not ok:
        return {"status": "fail", "reason": detail, "url": url}

    raw = tmp.read_text(encoding="utf-8", errors="replace")
    body = clean_gutenberg(raw)
    if len(body.split()) < 100:
        return {"status": "fail", "reason": f"body too short after cleaning ({len(body.split())} words)", "url": url}

    ebook_num = re.search(r"epub/(\d+)/", url)
    prov = gutenberg_provenance(doc_id, url, ebook_num.group(1) if ebook_num else "?")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(prov + "\n" + body + "\n", encoding="utf-8")
    return {"status": "ok", "words": len(body.split()), "url": url, "out": str(out_path)}


def fetch_archives_gov(case_id: str, doc: dict, out_path: Path, dry_run: bool) -> dict:
    doc_id = document_id(doc)
    url = ARCHIVES_GOV_URLS.get(doc_id) or doc.get("source_url", "")
    if not url:
        return {"status": "skip", "reason": "no URL"}

    if dry_run:
        return {"status": "dry-run", "url": url, "out": str(out_path)}

    tmp = Path(f"/tmp/archives_gov_{doc_id}.html")
    ok, detail = curl_fetch(url, tmp)
    if not ok:
        return {"status": "fail", "reason": detail, "url": url}

    raw = tmp.read_text(encoding="utf-8", errors="replace")
    body = clean_archives_gov(raw)
    if len(body.split()) < 100:
        return {"status": "fail", "reason": f"body too short ({len(body.split())} words) — may need HTML parse update", "url": url}

    prov = archives_gov_provenance(doc_id, url)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(prov + "\n" + body + "\n", encoding="utf-8")
    return {"status": "ok", "words": len(body.split()), "url": url, "out": str(out_path)}


# Per-case Gallica tome cache so we only download each tome once per run
_gallica_tome_cache: dict[str, str] = {}
_gallica_tome_url_cache: dict[str, str] = {}
_gallica_captcha_arks: set[str] = set()


def fetch_gallica(case_id: str, doc: dict, out_path: Path, dry_run: bool) -> dict:
    doc_id = document_id(doc)
    source_url = doc.get("source_url", "")
    ark = extract_gallica_ark(source_url)
    if not ark:
        return {"status": "fail", "reason": "could not extract ARK from source_url"}

    tome_num = doc.get("correspondance_volume") or doc.get("tome")

    if dry_run:
        return {"status": "dry-run", "ark": ark, "tome": tome_num, "out": str(out_path)}

    # Check if this ARK previously returned CAPTCHA in this run
    if ark in _gallica_captcha_arks:
        return {
            "status": "needs-playwright",
            "reason": "Gallica CAPTCHA on previous attempt for this ARK",
            "ark": ark,
            "url": source_url,
        }

    # Fetch or use cached tome text
    if ark not in _gallica_tome_cache:
        ok, text, detail, actual_url = fetch_gallica_textebrut(ark)
        if not ok:
            if "captcha" in detail:
                _gallica_captcha_arks.add(ark)
                return {
                    "status": "needs-playwright",
                    "reason": "Gallica served CAPTCHA — use corpus-download skill to solve in browser",
                    "ark": ark,
                    "textebrut_url": actual_url,
                }
            return {"status": "fail", "reason": detail, "ark": ark, "url": actual_url}
        _gallica_tome_cache[ark] = text
        _gallica_tome_url_cache[ark] = actual_url

    tome_text = _gallica_tome_cache[ark]
    actual_url = _gallica_tome_url_cache.get(ark) or source_url

    # Extract the individual bulletin
    body = extract_bulletin(tome_text, doc_id, doc)
    if body is None:
        return {
            "status": "fail",
            "reason": f"bulletin {doc.get('bulletin_number')} not found in tome text — "
                      "check bulletin_number in manifest or run gallica-download skill",
            "ark": ark,
        }

    prov = gallica_provenance(doc_id, ark, tome_num or "?", doc, actual_url)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(prov + "\n" + body + "\n", encoding="utf-8")
    return {"status": "ok", "words": len(body.split()), "ark": ark, "url": actual_url, "out": str(out_path)}


def fetch_archive_org_mk(case_id: str, doc: dict, out_path: Path, dry_run: bool) -> dict:
    doc_id = document_id(doc)
    ch = MK_CHAPTERS.get(doc_id)
    if not ch:
        return {"status": "skip", "reason": "no chapter map entry — speech file (gitignored, place manually)"}

    if dry_run:
        return {"status": "dry-run", "url": ARCHIVE_ORG_MK_URL, "out": str(out_path)}

    # Download full text if not cached
    if not ARCHIVE_ORG_CACHE.exists() or ARCHIVE_ORG_CACHE.stat().st_size < 1_600_000:
        print(f"  Downloading Archive.org MK text (~1.6MB)...", flush=True)
        ok, detail = curl_fetch(ARCHIVE_ORG_MK_URL, ARCHIVE_ORG_CACHE, timeout=120)
        if not ok:
            return {"status": "fail", "reason": f"Archive.org download failed: {detail}"}
        print(f"  Downloaded: {ARCHIVE_ORG_CACHE.stat().st_size:,} bytes", flush=True)
    else:
        print(f"  Using cached MK text: {ARCHIVE_ORG_CACHE.stat().st_size:,} bytes", flush=True)

    text = ARCHIVE_ORG_CACHE.read_text(encoding="utf-8", errors="replace")

    start_idx = text.find(ch["start_marker"], ch["start_min"])
    if start_idx < 0:
        return {"status": "fail", "reason": f"start marker {ch['start_marker']!r} not found after pos {ch['start_min']}"}

    end_idx = text.find(ch["end_marker"], start_idx + ch["end_min_offset"])
    if end_idx < 0:
        return {"status": "fail", "reason": f"end marker {ch['end_marker']!r} not found after start"}

    body = text[start_idx:end_idx].strip()
    prov = mk_provenance(doc_id, ch["title"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(prov + "\n" + body + "\n", encoding="utf-8")
    return {"status": "ok", "words": len(body.split()), "url": ARCHIVE_ORG_MK_URL, "out": str(out_path)}


# ---------------------------------------------------------------------------
# Playwright check / install
# ---------------------------------------------------------------------------

def ensure_playwright() -> tuple[bool, str]:
    """Check if playwright is importable; install if not. Returns (available, message)."""
    try:
        import playwright  # noqa: F401
        return True, "already installed"
    except ImportError:
        pass

    print("  Playwright not found — installing...", flush=True)
    r1 = subprocess.run(
        [sys.executable, "-m", "pip", "install", "playwright", "--quiet"],
        capture_output=True, text=True,
    )
    if r1.returncode != 0:
        return False, f"pip install failed: {r1.stderr.strip()}"

    r2 = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True, text=True,
    )
    if r2.returncode != 0:
        return False, f"playwright install chromium failed: {r2.stderr.strip()}"

    return True, "installed successfully"


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

STRATEGY_FN = {
    "gutenberg": fetch_gutenberg,
    "archives-gov": fetch_archives_gov,
    "gallica": fetch_gallica,
    "archive-org": fetch_archive_org_mk,
}

CURL_STRATEGIES = set(STRATEGY_FN.keys())


def run_verify(affected_cases: set[str]) -> dict[str, bool]:
    results = {}
    for cid in sorted(affected_cases):
        r = subprocess.run(
            [sys.executable, "scripts/verify-corpus.py", "--case", cid],
            capture_output=True, text=True,
        )
        passed = "RESULT: PASS" in r.stdout
        results[cid] = passed
        print(r.stdout, end="")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", default=None, help="Limit to one case")
    parser.add_argument("--doc", dest="doc_id", default=None, help="Fetch a single document by ID")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if file already present")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without fetching")
    parser.add_argument("--json", dest="output_json", action="store_true")
    parser.add_argument("--no-verify", action="store_true", help="Skip post-fetch verification")
    parser.add_argument("--playwright-check", action="store_true",
                        help="Check/install Playwright and exit")
    args = parser.parse_args()

    if args.playwright_check:
        ok, msg = ensure_playwright()
        print(f"Playwright: {'OK' if ok else 'FAIL'} — {msg}")
        return 0 if ok else 1

    ids = case_ids(args.case_id)
    ids = [c for c in ids if c != "x-case"]

    # Build target list
    targets: list[tuple[str, dict, str, Path]] = []
    for cid in ids:
        for doc in documents(cid):
            doc_id = document_id(doc)
            if args.doc_id and doc_id != args.doc_id:
                continue
            strategy = classify(cid, doc)
            out = raw_path_for(cid, doc)
            already_present = out.exists() and out.stat().st_size > 100

            if strategy not in CURL_STRATEGIES:
                targets.append((cid, doc, strategy, out))
                continue  # include for reporting but skip fetch

            if already_present and not args.force:
                targets.append((cid, doc, f"{strategy}:skip-present", out))
                continue

            targets.append((cid, doc, strategy, out))

    if not targets:
        print("No matching documents found.", file=sys.stderr)
        return 1

    # Check playwright only if founders-playwright targets exist and we're not dry-running
    needs_playwright = any(s == "founders-playwright" for _, _, s, _ in targets)
    playwright_ok = False
    if needs_playwright and not args.dry_run:
        playwright_ok, pw_msg = ensure_playwright()
        if not playwright_ok:
            print(f"WARNING: Playwright unavailable ({pw_msg}). Founders Online docs will be skipped.", file=sys.stderr)

    # Execute fetches
    results: list[dict] = []
    affected_cases: set[str] = set()

    for cid, doc, strategy, out_path in targets:
        doc_id = document_id(doc)

        if "skip-present" in strategy:
            base_strategy = strategy.split(":")[0]
            actual_url = planned_fetch_url(base_strategy, doc) or extract_raw_provenance_url(out_path)
            updated = False
            if actual_url and not args.dry_run:
                updated = update_manifest_source_url(cid, doc_id, actual_url)
            result = {
                "case": cid,
                "document_id": doc_id,
                "strategy": base_strategy,
                "status": "skipped",
                "reason": "already present (use --force to re-fetch)",
            }
            if actual_url:
                result["source_url"] = actual_url
                result["manifest_source_url_updated"] = updated
            results.append(result)
            affected_cases.add(cid)
            continue

        if strategy == "founders-playwright":
            results.append({
                "case": cid, "document_id": doc_id, "strategy": "founders-playwright",
                "status": "needs-playwright",
                "reason": "JS-rendered — run /corpus-download skill with Playwright",
                "url": doc.get("source_url", ""),
            })
            continue

        if strategy == "gitignored-manual":
            actual_url = extract_raw_provenance_url(out_path) or doc.get("source_url", "")
            updated = False
            if actual_url and not args.dry_run:
                updated = update_manifest_source_url(cid, doc_id, actual_url)
            result = {
                "case": cid, "document_id": doc_id, "strategy": "gitignored-manual",
                "status": "skipped",
                "reason": "gitignored file — place manually per README in raw directory",
            }
            if actual_url:
                result["source_url"] = actual_url
                result["manifest_source_url_updated"] = updated
            results.append(result)
            affected_cases.add(cid)
            continue

        if strategy == "unknown":
            results.append({
                "case": cid, "document_id": doc_id, "strategy": "unknown",
                "status": "skipped",
                "reason": "no recognised source domain — check manifest source_url",
            })
            continue

        fn = STRATEGY_FN[strategy]
        print(f"  [{strategy}] {doc_id} ...", flush=True)
        result = fn(cid, doc, out_path, args.dry_run)
        result["case"] = cid
        result["document_id"] = doc_id
        result["strategy"] = strategy
        results.append(result)

        if result.get("status") == "ok":
            actual_url = result.get("url") or result.get("textebrut_url")
            if actual_url and not args.dry_run:
                result["manifest_source_url_updated"] = update_manifest_source_url(cid, doc_id, actual_url)
            affected_cases.add(cid)

    # Verification
    verify_results: dict[str, bool] = {}
    if not args.dry_run and not args.no_verify and affected_cases:
        print("\nRunning verify-corpus.py...\n", flush=True)
        verify_results = run_verify(affected_cases)

    # Output
    if args.output_json:
        print(json.dumps({
            "generated_at": now_iso(),
            "results": results,
            "verify": verify_results,
        }, indent=2, ensure_ascii=False))
        return 0

    # Human-readable summary table
    print(f"\n{'document_id':55s} {'strategy':22s} {'words':>6}  status")
    print("-" * 100)
    needs_playwright_docs = []
    for r in results:
        status = r.get("status", "?")
        words = str(r.get("words", "—"))
        strategy = r.get("strategy", "?")
        doc_id = r.get("document_id", "?")
        reason = r.get("reason", "")
        marker = "OK" if status == "ok" else ("--" if status in ("skipped", "dry-run") else "!!")
        print(f"  [{marker}] {doc_id:51s} {strategy:22s} {words:>6}  {status}")
        if reason and status not in ("ok", "skipped", "dry-run"):
            print(f"        {reason}")
        if status == "needs-playwright":
            needs_playwright_docs.append(r)

    if needs_playwright_docs:
        print(f"\n  {len(needs_playwright_docs)} document(s) require Playwright (Founders Online or Gallica CAPTCHA):")
        for r in needs_playwright_docs:
            print(f"    /corpus-download {r['document_id']}")

    if verify_results:
        print()
        all_passed = all(verify_results.values())
        for cid, passed in sorted(verify_results.items()):
            print(f"  verify {cid}: {'PASS' if passed else 'FAIL'}")
        if not all_passed:
            print("\n  FAIL: one or more cases did not pass verification. Do not run normalize-texts.py until resolved.")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
