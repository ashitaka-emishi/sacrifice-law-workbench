---
description: Download a Washington document from Founders Online (founders.archives.gov). Pages are JS-rendered — navigates with Playwright, waits for the document text to appear, extracts it, and writes a provenance-headed file to the corpus.
allowed-tools: mcp__playwright__browser_navigate, mcp__playwright__browser_snapshot, mcp__playwright__browser_evaluate, mcp__playwright__browser_wait_for, mcp__playwright__browser_take_screenshot, Bash, Write, Read
---

Fetch and extract a George Washington document from Founders Online (founders.archives.gov) into the am-rev corpus.

> **Note:** Founders Online is JS-rendered — curl returns a near-empty page. `scripts/fetch-corpus.py` will flag these documents as `needs-playwright` and route here. This skill is the authoritative handler for all Founders Online fetches.

`$ARGUMENTS` format: `<document-spec>`

Where document-spec is one of:
- A slug from the manifest: `washington-orders-1776-07-02-eve-of-declaration`
- A date: `1776-07-02`
- A short label: `trenton` or `trenton-eve` or `farewell`
- `all` — re-download every document flagged `wrong-document-in-file` in the manifest

Example: `/founders-download 1776-07-02`
Example: `/founders-download all`

---

## Known document map (Washington am-rev corpus)

Ground truth from `cases/am-rev/metadata/document-manifest.json`:

| Slug | Date | Founders URL path | Short label |
|------|------|-------------------|-------------|
| washington-orders-1775-07-04-first-independence-day | 1775-07-04 | /documents/Washington/03-01-02-0004 | first-independence-day |
| washington-orders-1776-02-09-winter-encampment | 1776-02-09 | /documents/Washington/03-06-02-0138 | winter-encampment |
| washington-orders-1776-07-02-eve-of-declaration | 1776-07-02 | /documents/Washington/03-07-02-0355 | eve-of-declaration |
| washington-orders-1776-08-30-after-long-island | 1776-08-30 | /documents/Washington/03-09-02-0023 | after-long-island |
| washington-orders-1776-12-25-trenton-eve | 1776-12-25 | /documents/Washington/03-13-02-0177 | trenton-eve |
| washington-orders-1783-06-08-farewell-circular | 1783-06-08 | /documents/Washington/99-01-02-11404 | farewell-circular |
| washington-orders-1783-06-17-wars-end | 1783-06-17 | /documents/Washington/03-26-02-0001 | wars-end |

Output files go in:
`cases/am-rev/corpus/raw/am-rev-src-03-washington-general-orders/{SLUG}.txt`

---

## Step 1: Resolve the target document(s)

Parse `$ARGUMENTS` against the slug, date, and short-label columns above.

- If `all`: build a list of all 7 slugs and process them in order (Steps 2–5 for each).
- If a single match: set `SLUG`, `DATE`, `FOUNDERS_PATH`, and construct:
  ```
  FOUNDERS_URL = https://founders.archives.gov{FOUNDERS_PATH}
  OUT_PATH = cases/am-rev/corpus/raw/am-rev-src-03-washington-general-orders/{SLUG}.txt
  ```
- If ambiguous or unrecognised: tell the user and list the known slugs.

---

## Step 2: Check if the file already has valid content

Run:

```bash
python3 -c "
import os, re
path = 'cases/am-rev/corpus/raw/am-rev-src-03-washington-general-orders/{SLUG}.txt'
if not os.path.exists(path):
    print('MISSING')
else:
    text = open(path).read()
    wc = len(text.split())
    # A real Washington order should be at least 100 words
    if wc < 100:
        print(f'TOO_SHORT: {wc} words')
    elif 'wrong-document' in text.lower() or 'placeholder' in text.lower():
        print(f'PLACEHOLDER: {wc} words')
    else:
        print(f'OK: {wc} words')
        print(text[:300])
"
```

If `OK` and the user did not pass `--force`: report the file is already good and skip to Step 6 (Report). Otherwise continue.

---

## Step 3: Navigate to Founders Online and wait for JS rendering

### 3a. Navigate to the document page

Navigate to `{FOUNDERS_URL}`. Founders Online renders document text with JavaScript — the raw HTML has almost no content until React/Angular hydrates.

After navigating, wait up to 15 seconds for the main document body to appear:

```javascript
() => {
  // Founders Online puts the transcription in .document-content or #document-body or similar
  const selectors = [
    '.document-content',
    '#document-body',
    '[class*="document-content"]',
    '[class*="transcription"]',
    'article',
    'main'
  ];
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && el.innerText && el.innerText.trim().length > 200) {
      return { found: true, selector: sel, length: el.innerText.length, preview: el.innerText.substring(0, 300) };
    }
  }
  const bodyText = document.body.innerText.trim();
  return { found: false, bodyLength: bodyText.length, preview: bodyText.substring(0, 300) };
}
```

If `found` is false and `bodyLength` < 500, the page has not hydrated yet. Wait 3 seconds and try again (up to 3 retries).

If still not found after retries, take a screenshot so you can see the page state:

```
browser_take_screenshot
```

Then try broader extraction (Step 3b) with the full `document.body.innerText`.

### 3b. Extract the document text

Once a content container is found, extract clean text:

```javascript
() => {
  const selectors = [
    '.document-content',
    '#document-body',
    '[class*="document-content"]',
    '[class*="transcription"]',
    'article',
    'main'
  ];
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && el.innerText && el.innerText.trim().length > 200) {
      return { selector: sel, text: el.innerText.trim() };
    }
  }
  return { selector: 'body', text: document.body.innerText.trim() };
}
```

Save `result.text` as `RAW_TEXT`. Verify:
- Length > 200 characters
- Contains recognisable content (Washington's name, date, military vocabulary, or "General Orders")

If the text looks like a nav menu or error page rather than a document, take a screenshot and tell the user.

---

## Step 4: Clean and validate the extracted text

Run this Python cleaning pass on `RAW_TEXT`:

```bash
python3 -c "
import re, sys

raw = open('/tmp/founders_raw_{SLUG}.txt', encoding='utf-8').read()

# Strip obvious nav/footer boilerplate that Founders Online wraps around docs
# These patterns appear before/after the actual transcription
boilerplate_starts = [
    r'^.*?(?=\bGeneral Orders\b|\bCircular\b|\bTo the.*?:)',
]
boilerplate_ends = [
    r'(?:Cite this document|Source:?\s+\[|National Historical Publications|Founders Online)',
]

text = raw

# Try to isolate the transcription body — everything from the first
# meaningful salutation/header to the signature or citation notice
match = re.search(r'((?:General Orders|Circular|To [A-Z]|Head Quarters|Head-Quarters).*)', text, re.S | re.I)
if match:
    text = match.group(1)

# Trim at citation/footer markers
for pat in boilerplate_ends:
    cut = re.search(pat, text, re.I)
    if cut:
        text = text[:cut.start()].rstrip()

# Collapse excessive blank lines
text = re.sub(r'\n{3,}', '\n\n', text).strip()

wc = len(text.split())
print(f'WORDS: {wc}')
print('---PREVIEW---')
print(text[:600])
print('---END---')
open('/tmp/founders_clean_{SLUG}.txt', 'w', encoding='utf-8').write(text)
"
```

Confirm the cleaned text:
- Starts with document header, salutation, or "General Orders" line
- Ends near the signature or closing
- Word count is between 100 and 5000 (Washington's orders range 200–3000 words; the 1783 Circular is ~2000)
- Contains no nav menu text, no "Cite this document" footer

If the word count or content looks wrong, inspect the preview and adjust the extraction logic before proceeding.

---

## Step 5: Write the output file with provenance header

```bash
python3 -c "
text = open('/tmp/founders_clean_{SLUG}.txt', encoding='utf-8').read()
wc = len(text.split())

provenance = '''SOURCE: Founders Online, National Archives
SERIES: Papers of George Washington, Revolutionary War Series
DOCUMENT_PATH: {FOUNDERS_PATH}
SOURCE_URL: {FOUNDERS_URL}
SLUG: {SLUG}
DATE: {DATE}
AUTHORSHIP: George Washington
RIGHTS: Public domain (18th-century document; no copyright on transcription)
EXTRACTION_TOOL: .claude/commands/founders-download.md
''' + '=' * 72

out_path = 'cases/am-rev/corpus/raw/am-rev-src-03-washington-general-orders/{SLUG}.txt'
open(out_path, 'w', encoding='utf-8').write(provenance + '\n\n' + text + '\n')
lines = open(out_path).readlines()
print(f'Wrote {out_path}: {wc} words, {len(lines)} lines')
"
```

---

## Step 6: Clear the risk_flag in the document manifest

Open `cases/am-rev/metadata/document-manifest.json`. Find the entry whose `document_id` ends in the relevant date (e.g. `am-rev-washington-orders-1776-07-02`). Remove the `risk_flags` array entry `"wrong-document-in-file — re-download needed from Founders Online"`. If `risk_flags` becomes empty, remove the key entirely.

Do not modify any other field. Write the file back with 2-space indent.

---

## Step 7: Report

Tell the user:

**If extracted successfully:**
- Slug, date, and Founders URL
- Word count and output file path
- First 3 lines of the extracted text as a preview
- Whether the manifest risk_flag was cleared

**If extraction failed or text looked wrong:**
- What the page returned (nav text, error, short body)
- A screenshot path if one was taken
- What the user should try (manual browser visit, check URL)

**If processing `all`:**
- Table of results: slug | words | status (ok / failed / skipped-already-valid)
- List any failures with error details

---

## Step 8: Verify the downloaded file

After writing the file (and after any pipeline steps), run the corpus verifier for the affected document:

```bash
python3 scripts/verify-corpus.py --case am-rev
```

A PASS on all three checks (file present, word count, required phrases) confirms the correct document was downloaded to the correct location. If any check FAILs, report the failure detail to the user and do not proceed to pipeline steps until it is resolved.
