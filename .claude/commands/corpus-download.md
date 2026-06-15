---
description: Master corpus download skill. Routes to the correct domain-specific fetch strategy based on document source, prefers curl over Playwright, installs Playwright if needed, and runs verify-corpus.py after every download. Use this as the single entry point for acquiring any corpus document.
allowed-tools: Bash, Read, Write, mcp__playwright__browser_navigate, mcp__playwright__browser_snapshot, mcp__playwright__browser_evaluate, mcp__playwright__browser_wait_for, mcp__playwright__browser_take_screenshot
---

Download one or more corpus documents into their correct raw paths, verify integrity, and report results. This is the single entry point — it routes to the appropriate fetch strategy per domain and runs `verify-corpus.py` after every acquisition.

Critical invariant: `source_url` in `cases/*/metadata/document-manifest.json` must name the actual document downloaded or transcribed into the raw corpus file. If the workflow switches from a planned source to another source, update `source_url` during acquisition before running `normalize-texts.py`; do not leave a prior candidate, landing page, translation, scholarly edition, or gloss reference in that field.

`$ARGUMENTS` format (one of):

- `<document-id>` — fetch a specific document by its manifest ID (e.g. `lincoln-gettysburg-address`)
- `<case-id>` — fetch all missing documents for a case (e.g. `lincoln`, `napoleon`, `am-rev`, `hitler`)
- `all` — fetch all missing documents across all cases
- `--force <document-id>` — re-download even if the file already passes verification

Examples:
```
/corpus-download lincoln-gettysburg-address
/corpus-download napoleon
/corpus-download all
/corpus-download --force am-rev-washington-orders-1776-07-02
```

---

## Step 1: Run fetch-corpus.py for all curl-accessible documents

`scripts/fetch-corpus.py` handles all curl-based sources (Gutenberg, archives.gov, Gallica texteBrut, Archive.org MK chapters) in one pass. Run it first — it also installs Playwright if needed and runs `verify-corpus.py` automatically.

```bash
# Translate $ARGUMENTS to fetch-corpus.py flags:
#   <doc-id>         → --doc <doc-id>
#   <case-id>        → --case <case-id>
#   all              → (no flag — default is all)
#   --force <...>    → --force --doc <...> or --force --case <...>

python3 scripts/fetch-corpus.py --case lincoln
# or
python3 scripts/fetch-corpus.py --doc lincoln-gettysburg-address
# or
python3 scripts/fetch-corpus.py
# or
python3 scripts/fetch-corpus.py --force --doc am-rev-paine-common-sense
```

The script outputs a summary table showing strategy, word count, and status per document, then runs `verify-corpus.py` automatically. On successful downloads and already-present files, it also updates manifest `source_url` values when it can determine the actual downloaded source URL.

**Documents that `fetch-corpus.py` handles (curl-only path):**

| Source domain / pattern | Strategy |
|-------------------------|----------|
| `gutenberg.org` | curl — plain text, strips PG header/footer |
| `archives.gov` | curl — strips HTML, extracts Declaration text |
| `gallica.bnf.fr` | curl texteBrut + bulletin extraction |
| `archive.org` | curl djvu text + MK chapter extraction by marker |
| Hitler speeches (gitignored) | skip — verify only |

**Documents that `fetch-corpus.py` cannot handle (emit `needs-playwright`):**

| Source | Strategy |
|--------|----------|
| `founders.archives.gov` | JS-rendered — Step 2 below |
| Gallica CAPTCHA | browser needed — Step 3 below |

Read the script output. If any document reports `needs-playwright`, continue to Step 2 (Founders) or Step 3 (Gallica CAPTCHA).

If `fetch-corpus.py` is missing or has a Python error, report it — do not attempt to replicate its fetch logic inline.

---

## Step 2: Founders Online fetch (Playwright — only if needed)

**Applies to:** `am-rev-washington-orders-*` — these are JS-rendered pages with no curl path.

Consult `.claude/commands/founders-download.md` for the full document map, wait logic, text extraction selectors, cleaning pass, and provenance header format. Execute its steps directly.

Key points:
- Check Playwright: `python3 scripts/fetch-corpus.py --playwright-check`
- Navigate to `https://founders.archives.gov{path_from_manifest}`.
- Wait up to 15 seconds for `.document-content` or `article` to hydrate with >200 chars.
- If the page does not hydrate after 3 retries, take a screenshot and report failure.
- Clean boilerplate with the regex pass in `founders-download.md` Step 4.
- Write with provenance header per `founders-download.md` Step 5.
- Update that document's manifest `source_url` to the actual Founders Online document URL if the browser workflow used a different URL than the manifest had before.
- Run `python3 scripts/verify-corpus.py --case am-rev` after writing.

---

## Step 3: Gallica CAPTCHA fallback (Playwright — only if fetch-corpus.py reports captcha)

**Applies to:** `napoleon-bulletin-*` when Gallica returns a security challenge.

If `fetch-corpus.py` reported `needs-playwright` with reason `captcha`, proceed:

1. Consult `.claude/commands/gallica-download.md` for the full tome map and bulletin extraction.
2. Navigate to the texteBrut URL from the script output.
3. Tell the user:
   > Gallica is showing a security challenge. Please solve the CAPTCHA in the browser window, then confirm when the OCR text is visible.
4. Wait for user confirmation. Verify the page loaded correctly:
   ```javascript
   () => ({
     length: document.body.innerText.length,
     isSecurity: document.body.innerText.includes('Vérification de sécurité'),
     preview: document.body.innerText.substring(0, 200)
   })
   ```
5. If `isSecurity` is false and `length > 10000`, extract:
   ```javascript
   () => document.body.innerText
   ```
   Save to `/tmp/gallica_tome_{ARK}.txt` and run the bulletin extraction from `gallica-download.md` Step 4.
   Update each affected manifest `source_url` to the actual `texteBrut` URL used for the extracted text.
6. Run `python3 scripts/verify-corpus.py --case napoleon` after writing.

---

## Step 4: Run verify-corpus.py for all affected cases (if not already done by the script)

`fetch-corpus.py` runs verification automatically. If you ran Playwright steps manually (Steps 2 or 3), run verification explicitly:

```bash
python3 scripts/verify-corpus.py --case am-rev
python3 scripts/verify-corpus.py --case napoleon
```

Failure diagnoses:
- **FAIL file_present**: download did not produce a file at the expected path. Re-run the fetch step.
- **FAIL min_words**: file too short — wrong document, truncated download, or only provenance header written. Re-run.
- **FAIL required_phrases**: right size but wrong content — wrong edition, wrong chapter, or garbled OCR. Inspect first 500 chars.
- **warning (no verification spec)**: no `verification` block in manifest. Add one before accepting the download.

Do not proceed to normalization until all targeted documents PASS.

---

## Step 5: Report

`fetch-corpus.py` prints the summary table. Reproduce or supplement it:

```
document_id                              | strategy      | words  | verify
-----------------------------------------|---------------|--------|-------
lincoln-gettysburg-address               | gutenberg     | 364    | PASS
napoleon-bulletin-1807-02-08-eylau       | gallica       | 1290   | PASS
am-rev-washington-orders-1776-07-02      | founders      | 713    | PASS
hitler-mein-kampf-vol1-ch2-wien          | archive-org   | 15798  | PASS
```

For any FAIL or skip, state which check failed and what the user should do next.

If all targeted documents PASS, confirm the case is ready:
```bash
python3 scripts/normalize-texts.py --case {case_id}
python3 scripts/segment-texts.py --case {case_id}
```
