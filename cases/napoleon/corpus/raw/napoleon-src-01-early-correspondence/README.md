# Napoleon Early Correspondence — Manual PDF Acquisition + OCR

Rise-phase letters from Correspondance de Napoléon Ier, Plon 1858–1870.

## Status

**Browser script approach failed (2026-06-13).** Gallica's bot-detection
serves an HTML security page with a 200 OK via the `.texteBrut` API endpoint.

**Working approach: use Gallica's plain text download directly.**
On any Gallica volume page, use the download button and select
"Texte (TXT)" — this downloads the full OCR text for the volume as a
single `.txt` file with a metadata header. No PDF or OCR step needed.

## Files present

Full-volume source files (kept as reference, gitignored):

- `tome-1.txt` — Correspondance Tome 1 (~1.5MB)
- `tome-2.txt` — Correspondance Tome 2 (~1.2MB)
- `tome-3.txt` — Correspondance Tome 3 (~1.2MB)

Extracted letter files (11 documents, gitignored):

- `napoleon-corr-1793-letter-013.txt` — early Toulon siege
- `napoleon-corr-1793-letter-034.txt` — Toulon mid-phase
- `napoleon-corr-1793-letter-058-joseph.txt` — letter to Joseph Bonaparte
- `napoleon-corr-1794-letter-119.txt` — post-Toulon, Jacobin register
- `napoleon-corr-1795-letter-178.txt` — transition period
- `napoleon-corr-1796-letter-1117-verone.txt` — Italian campaign (Vérone)
- `napoleon-corr-1796-letter-1308.txt` — mid-campaign Directory
- `napoleon-corr-1796-letter-1373.txt` — late Italian campaign (multi-letter span)
- `napoleon-corr-1796-letter-1785.txt` — post-Castiglione
- `napoleon-corr-1797-letter-1997.txt` — post-Rivoli (multi-letter span)
- `napoleon-corr-1797-letter-2215.txt` — Campo Formio era

Note: two files (letter-1373, letter-1997) are larger spans containing multiple
letters — the OCR did not detect all letter delimiters. The full text is present
and correct; the normalize pipeline will segment further.

## Acquisition steps (for reference / future volumes)

1. Navigate to the Gallica volume URL for the tome needed
2. Download button → "Texte (TXT)" → save to this directory as `tome-N.txt`
3. Claude Code will extract the priority letter page ranges from the full tome text
4. Record each letter's volume, letter number, date, recipient, and
   Gallica ARK URL in `cases/napoleon/metadata/document-manifest.json`

## Volume URLs (Correspondance de Napoléon Ier, Plon 1858–1870)

- Tome 1 (1784–1795): <https://gallica.bnf.fr/ark:/12148/bpt6k6296221w>
- Tome 2 (1795–1796): <https://gallica.bnf.fr/ark:/12148/bpt6k6295821n>
- Tome 3 (1796–1797): <https://gallica.bnf.fr/ark:/12148/bpt6k6295853m>

## Priority letters (10 documents)

Covering rise-phase 1784–1797: early schoolboy letters through end of Italian
campaign and Campo Formio. Selection rationale documented per file in the
`SELECTION_NOTE` field of each file's provenance header.

## Notes

- All texts are French originals. Translation methodology must be resolved
  in `OPEN_DECISIONS.md` before annotation begins.
- Page numbers in the script are approximate (Gallica scan pagination differs
  from printed page numbers). Verify each file's OCR output covers the
  intended letter.
- Key CMT terms to flag in translation: *sacrifice*, *gloire*, *patrie*,
  *honneur*, *sang*, *corps*, *devoir*.
- Per source-registry: `git_tracking = gitignored-local`.
