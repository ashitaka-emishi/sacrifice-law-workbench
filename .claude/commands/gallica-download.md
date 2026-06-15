---
description: Download and extract a specific Grande Armée bulletin from Gallica (gallica.bnf.fr). Searches already-downloaded tomes first, then fetches the correct Gallica tome if needed, solves CAPTCHA interactively, and extracts just the target bulletin to an individual file.
allowed-tools: mcp__playwright__browser_navigate, mcp__playwright__browser_snapshot, mcp__playwright__browser_evaluate, mcp__playwright__browser_tabs, mcp__playwright__browser_wait_for, mcp__playwright__browser_take_screenshot, mcp__playwright__browser_network_requests, Bash, Write, Read
---

Find and extract a specific Grande Armée bulletin from the Correspondance de Napoléon Ier (Plon, 1858–1870) via Gallica.

> **Scripted path:** `scripts/fetch-corpus.py` handles Gallica texteBrut downloads and bulletin extraction automatically (curl + ARK lookup + marker extraction). Run `/corpus-download napoleon` or `python3 scripts/fetch-corpus.py --case napoleon` first. Use this skill when the script reports `needs-playwright` (CAPTCHA), when a tome is not yet in the local cache, or when you need interactive inspection of a bulletin.

`$ARGUMENTS` format: `<bulletin-spec>`

Where bulletin-spec is one of:
- A bulletin number: `34` → 34th Bulletin de la Grande Armée
- A slug: `napoleon-bulletin-1812-12-03-russia-29th`
- A date + campaign: `1806-10-14 jena`
- The special 29th: `29th` or `29e`

Example: `/gallica-download 52` (finds and extracts the 52nd Bulletin — Jena)

---

## Known tome map (Correspondance de Napoléon Ier, Plon 1858–1870)

This is ground truth from actual OCR inspection — use it to route requests:

| Tome | Gallica ARK | Bulletin range | Campaign | Downloaded? |
|------|-------------|----------------|----------|-------------|
| 11 | bpt6k9666763q | 1–37 | Austerlitz 1805 | yes |
| 12 | bpt6k6294040x | none | 1806 admin | yes |
| 13 | bpt6k96429871 | 1–35 (1806 series) | Jena-Auerstedt 1806 | yes |
| 14 | bpt6k6296790v | 36–68 | Jena aftermath, Eylau 1806–1807 | yes |
| 15 | bpt6k6294033s | 69–87 | Friedland/Tilsit 1807 | yes |
| 24 | bpt6k63342473 | 26, 29th | Russia 1812 | yes |

Tomes 10, 12, 21 contain no numbered bulletins — administrative correspondence only.

Bulletins from the Wagram 1809 campaign and Bautzen 1813 campaign are in **separate
bulletin series** (numbered from 1 again). They are NOT in the Correspondance de
Napoléon Ier — they appear in standalone pamphlet collections on Gallica. If asked
for those, skip to Step 7 (Report) and tell the user where to look.

Downloaded tomes are at:
`cases/napoleon/corpus/raw/napoleon-src-02-grande-armee-bulletins/tome-{N}.txt`

---

## Step 1: Identify the target bulletin

Parse `$ARGUMENTS` to determine:
- `BULLETIN_NUM` — the bulletin number in the continuous 1805–1807 series
- `CAMPAIGN` — the campaign name for context
- `TARGET_SLUG` — output filename slug

Use the known tome map to determine which tome should contain it:
- Bulletins 1–37 → tome 11 (downloaded)
- Bulletins 38–51 → tome 13 (NOT downloaded — need to find ARK)
- Bulletins 52–68 → tome 14 (NOT downloaded — need to find ARK)
- Bulletins 69–87 → tome 15 (downloaded)
- Bulletin 26 or 29th → tome 24 (downloaded)

If the bulletin number is outside this range or is from Wagram/Bautzen: skip to Step 7.

---

## Step 2: Check already-downloaded tomes

Run this Bash command to check if the target bulletin is already in a local tome:

```bash
python3 -c "
import re, sys
num = {BULLETIN_NUM}
suffix = 'er' if num == 1 else 'e'
pattern = re.compile(rf'(?:\d+\.\s*—\s*)?{num}{suffix}\s+BULLETIN\s+DE\s+LA\s+GRANDE\s+ARM', re.I)
import glob
tomes = glob.glob('cases/napoleon/corpus/raw/napoleon-src-02-grande-armee-bulletins/tome-*.txt')
for path in sorted(tomes):
    lines = open(path).readlines()
    for i, line in enumerate(lines):
        if pattern.search(line):
            print(f'FOUND: {path} line {i}')
            print('HEADING:', line.strip()[:120])
            print('CONTEXT:', ''.join(lines[i:i+4]).replace('\n',' | ')[:200])
            sys.exit(0)
print('NOT_FOUND_IN_LOCAL_TOMES')
"
```

If `FOUND` → skip to Step 4 (extract from local file).
If `NOT_FOUND_IN_LOCAL_TOMES` → continue to Step 3.

---

## Step 3: Find and download the correct Gallica tome

### 3a. Find the ARK for the missing tome

Navigate to Gallica and search for the correct tome number. Use this search URL pattern:

```
https://gallica.bnf.fr/services/engine/search/sru?operation=searchRetrieve&version=1.2&query=dc.title%20all%20%22Correspondance%20Napol%C3%A9on%20Tome%20{TOME_NUM}%22&suggest=0&keywords=
```

Or navigate directly to Gallica and search for: `Correspondance Napoléon Ier Tome 13`

Look for the result titled "Correspondance de Napoléon Ier. Tome {N} / publiée par ordre de l'Empereur Napoléon III" and extract its ARK identifier (format: `bpt6k{...}`).

### 3b. Get the page count

Navigate to `https://gallica.bnf.fr/ark:/12148/{ARK_ID}` and extract the page count from the text matching `(\d+) page(s)`.

Construct the texteBrut URL:
```
https://gallica.bnf.fr/ark:/12148/{ARK_ID}/f9.image/f1n{TOTAL_PAGES}.texteBrut
```

### 3c. Navigate and handle CAPTCHA

Navigate to the texteBrut URL. Tell the user:

> **The browser will show a Gallica security challenge (CAPTCHA). Please solve it in the browser window. Once the page shows OCR text (not a security page), come back and confirm.**

Wait for user confirmation, then verify the page loaded correctly:

```javascript
() => {
  const text = document.body.innerText;
  return {
    length: text.length,
    isSecurity: text.includes('Vérification de sécurité'),
    preview: text.substring(0, 200)
  };
}
```

If `isSecurity` is true or length < 10000, tell the user and wait for them to try again.

### 3d. Extract the full tome text and decode it

Save `document.body.innerText` to a temp path, then immediately decode the JSON-escaped string:

```bash
TOME_PATH="cases/napoleon/corpus/raw/napoleon-src-02-grande-armee-bulletins/tome-{TOME_NUM}.txt"
python3 -c "
import json
data = open('$TOME_PATH', 'rb').read()
open('$TOME_PATH', 'w', encoding='utf-8').write(json.loads(data))
lines = open('$TOME_PATH').readlines()
print(f'Decoded: {len(lines)} lines')
"
```

---

## Step 4: Extract the target bulletin from the tome file

Run this extraction script to pull just the target bulletin:

```bash
python3 -c "
import re

num = {BULLETIN_NUM}
suffix = 'er' if num == 1 else 'e'
heading_pattern = re.compile(
    rf'(?:\d+\.\s*—\s*)?{num}{suffix}\s+BULLETIN\s+DE\s+LA\s+GRANDE\s+ARM', re.I
)
next_pattern = re.compile(r'BULLETIN\s+DE\s+LA\s+GRANDE\s+ARM|\d{{4,5}}\s*\.\s*—', re.I)

tome_path = 'cases/napoleon/corpus/raw/napoleon-src-02-grande-armee-bulletins/tome-{TOME_NUM}.txt'
lines = open(tome_path).readlines()

# Find start
start = None
for i, line in enumerate(lines):
    if heading_pattern.search(line.strip()):
        start = i
        break

if start is None:
    print('ERROR: bulletin not found')
    exit(1)

# Find end (next bulletin heading or next numbered Correspondance entry)
end = len(lines)
for i in range(start + 5, len(lines)):
    line = lines[i].strip()
    if not line:
        continue
    if heading_pattern.search(line):
        end = i
        break
    if re.match(r'^\d{{4,5}}\s*\.\s*—', line) and i > start + 20:
        end = i
        break

# Strip trailing blanks
while end > start and not lines[end-1].strip():
    end -= 1

body = ''.join(lines[start:end]).strip()
heading = lines[start].strip()
word_count = len(body.split())
print(f'START: {start}')
print(f'END: {end}')
print(f'HEADING: {heading[:120]}')
print(f'WORDS: {word_count}')
print('---BODY---')
print(body[:500])
"
```

Confirm the extracted body:
- Starts with the correct bulletin heading and date
- Contains recognizable French military text
- Is between 500 and 8000 words (bulletins are typically 1000–4000 words)

If the extraction looks wrong (too short, wrong heading, cuts off early), inspect the surrounding lines and adjust the end-detection logic.

---

## Step 5: Write the individual bulletin file

Write the extracted bulletin with a provenance header:

```bash
python3 -c "
import re

num = {BULLETIN_NUM}
suffix = 'er' if num == 1 else 'e'
heading_pattern = re.compile(
    rf'(?:\d+\.\s*—\s*)?{num}{suffix}\s+BULLETIN\s+DE\s+LA\s+GRANDE\s+ARM', re.I
)
next_pattern = re.compile(r'BULLETIN\s+DE\s+LA\s+GRANDE\s+ARM|\d{{4,5}}\s*\.\s*—', re.I)

tome_path = 'cases/napoleon/corpus/raw/napoleon-src-02-grande-armee-bulletins/tome-{TOME_NUM}.txt'
out_path = 'cases/napoleon/corpus/raw/napoleon-src-02-grande-armee-bulletins/{SLUG}.txt'
lines = open(tome_path).readlines()

start = next(i for i, l in enumerate(lines) if heading_pattern.search(l.strip()))
end = len(lines)
for i in range(start + 5, len(lines)):
    line = lines[i].strip()
    if not line:
        continue
    if heading_pattern.search(line) or (re.match(r'^\d{{4,5}}\s*\.\s*—', line) and i > start + 20):
        end = i
        break
while end > start and not lines[end-1].strip():
    end -= 1

body = ''.join(lines[start:end]).strip()
heading = lines[start].strip()

provenance = '''SOURCE: Correspondance de Napoléon Ier, Plon, Paris, 1858–1870
VOLUME: Tome {TOME_NUM}
ARCHIVE: Bibliothèque nationale de France / Gallica
ARK: {ARK_ID}
SLUG: {SLUG}
DATE: {DATE}
CAMPAIGN: {CAMPAIGN}
RIGHTS: Public domain (original pre-1821; Plon edition pre-1900; BnF open access)
EXTRACTION_TOOL: .claude/commands/gallica-download.md
BULLETIN_HEADING: ''' + heading + '''
''' + '=' * 72

open(out_path, 'w', encoding='utf-8').write(provenance + '\n\n' + body + '\n')
lines_written = open(out_path).readlines()
print(f'Wrote {out_path}: {len(body.split())} words, {len(lines_written)} lines')
"
```

---

## Step 6: Update the document manifest

Open `cases/napoleon/metadata/document-manifest.json` and add an entry for the new bulletin under `documents`. Follow the schema of existing entries:

```json
{
  "document_id": "{SLUG}",
  "title": "{N}th Bulletin of the Grande Armée ({CAMPAIGN})",
  "short_title": "Bulletin {N}: {CAMPAIGN}",
  "date": "{DATE}",
  "date_precision": "day",
  "register": "military-bulletin-proclamation",
  "authorship": "Napoleon Bonaparte / imperial military voice",
  "source_url": "https://gallica.bnf.fr/ark:/12148/{ARK_ID}",
  "source_citation": "Correspondance de Napoléon Ier, Tome {TOME_NUM}. Paris: Plon, 1858–1870. Via Gallica / BnF.",
  "rights_status": "public-domain",
  "expected_raw_path": "corpus/raw/napoleon-src-02-grande-armee-bulletins/{SLUG}.txt",
  "analytical_priority": "primary",
  "phase": "peak-empire",
  "campaign": "{CAMPAIGN}",
  "bulletin_number": {BULLETIN_NUM},
  "correspondance_volume": {TOME_NUM},
  "extraction_tool": ".claude/commands/gallica-download.md"
}
```

Also remove the matching entry from `_missing_documents` if it exists there.

---

## Step 7: Report

Tell the user the result:

**If extracted successfully:**
- Bulletin number, slug, and campaign
- Source tome, ARK, and Gallica URL
- Word count and file path
- First 3 lines of the bulletin text as a preview

**If the bulletin is NOT in the Correspondance de Napoléon Ier series** (Wagram 1809, Bautzen 1813, or any bulletin after #87 in the 1805–1807 series):

Tell the user:

> Bulletin {N} is not in the Correspondance de Napoléon Ier (Plon 1858–1870) series held by Gallica.
>
> **Wagram 1809 bulletins:** Search Gallica for "Bulletins de la Grande Armée 1809" or look in the collection `Victoires, conquêtes, désastres` (Panckoucke). ARK search: `gallica.bnf.fr` → search "bulletin grande armée 1809".
>
> **Bautzen / 1813 Germany bulletins:** Search Gallica for "Bulletins de la Grande Armée 1813". These were published as separate pamphlets and may also appear in contemporary newspapers (Le Moniteur universel).
>
> **Other sources:** The Napoleonica.org database at https://www.napoleonica.org/ indexes individual bulletins with Gallica ARKs.

**If the ARK for a needed tome is unknown:** Search Gallica directly and report the ARK you find (or that you cannot find it) before proceeding.

---

## Step 8: Verify the downloaded file

After writing the individual bulletin file (Step 5), run the corpus verifier:

```bash
python3 scripts/verify-corpus.py --case napoleon
```

A PASS on all three checks (file present, word count, required phrases) confirms the correct bulletin was extracted to the correct location. If any check FAILs, report the failure detail to the user and do not proceed to pipeline steps until it is resolved.

Note: if the bulletin is newly added, its `verification` block must first be added to `cases/napoleon/metadata/document-manifest.json` under the document entry before the verifier can check phrases and word count. Add it as part of Step 6 (manifest update).
