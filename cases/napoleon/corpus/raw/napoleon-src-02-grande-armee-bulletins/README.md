# Napoleon Grande Armée Bulletins — Manual PDF Acquisition + OCR

Peak-empire bulletins from Correspondance de Napoléon Ier, Plon 1858–1870.

## Status (2026-06-14)

**Working approach confirmed:** navigate to Gallica document page, then
construct the `.texteBrut` URL as `ark:/12148/{ARK}/f9.image/f1n{PAGES}.texteBrut`.
A CAPTCHA fires on first access — solve it once per session; subsequent
pages in the same browser session load without challenge.
Use `/gallica-download` skill (`.claude/commands/gallica-download.md`).

**IMPORTANT:** The `browser_evaluate` filename save writes a JSON-escaped string.
After saving, run the decoder:
```python
import json; open(path,'w').write(json.loads(open(path,'rb').read()))
```
Or use `scripts/extract-napoleon-bulletins.py` which reads directly from the tome files.

## Files present

Source tomes (full-volume OCR, gitignored):

- `tome-11.txt` — Correspondance Tome 11 (bulletins 1–37, Austerlitz campaign 1805)
- `tome-13.txt` — Correspondance Tome 13 (bulletins 1–35, 1806 series, Jena-Auerstedt) — ARK: bpt6k96429871
- `tome-14.txt` — Correspondance Tome 14 (bulletins 36–68, Jena aftermath + Eylau 1807) — ARK: bpt6k6296790v
- `tome-15.txt` — Correspondance Tome 15 (bulletins 69–87, Friedland/Tilsit 1807) — ARK: bpt6k6294033s
- `tome-19.txt` — Correspondance Tome 19 (Bulletins de l'Armée d'Allemagne, Wagram 1809) — ARK: bpt6k6296216k
- `tome-24.txt` — Correspondance Tome 24 (bulletins 26+, Russia 1812 including 29th Bulletin) — ARK: bpt6k63342473
- `tome-25.txt` — Correspondance Tome 25 (Grande Armée bulletins Lützen + Bautzen 1813) — ARK: bpt6k9639050s

Extracted bulletin files (individual documents, gitignored):

- `napoleon-bulletin-1805-12-03-austerlitz.txt` — Bulletin 34 (Austerlitz victory)
- `napoleon-bulletin-1805-12-04-austerlitz-aftermath.txt` — Bulletin 35 (aftermath)
- `napoleon-bulletin-1806-10-15-jena.txt` — Bulletin 5/1806 series (Jena-Auerstedt battle)
- `napoleon-bulletin-1806-10-26-berlin.txt` — Bulletin 18/1806 series (entry into Berlin)
- `napoleon-bulletin-1807-02-08-eylau.txt` — Bulletin 58 (Battle of Eylau)
- `napoleon-bulletin-1807-06-14-friedland.txt` — Bulletin 79 (Friedland/Wehlau)
- `napoleon-bulletin-1809-07-08-wagram.txt` — Bulletin 25/Armée d'Allemagne (Wagram)
- `napoleon-bulletin-1812-10-23-russia-advance.txt` — Bulletin 26 (Borovsk/Moscow)
- `napoleon-bulletin-1812-12-03-russia-29th.txt` — 29th Bulletin (retreat collapse) ★ analytically critical
- `napoleon-bulletin-1813-05-24-bautzen.txt` — Bulletin (Bautzen, 20–21 May 1813)
- `napoleon-bulletin-1813-05-02-lutzen.txt` — Bulletin (Lützen, 2 May 1813) — **extracted but dropped from primary corpus as out-of-scope**; file retained in case needed

## Tome map (verified from OCR inspection)

| Tome | ARK | Content | Campaign | Status |
|------|-----|---------|----------|--------|
| 11 | bpt6k9666763q | bulletins 1–37 | Austerlitz 1805 | ✓ downloaded |
| 13 | bpt6k96429871 | bulletins 1–35 (1806 series) | Jena-Auerstedt 1806 | ✓ downloaded |
| 14 | bpt6k6296790v | bulletins 36–68 | Jena aftermath, Eylau 1807 | ✓ downloaded |
| 15 | bpt6k6294033s | bulletins 69–87 | Friedland, Tilsit 1807 | ✓ downloaded |
| 19 | bpt6k6296216k | Bulletins de l'Armée d'Allemagne | Wagram 1809 | ✓ downloaded |
| 24 | bpt6k63342473 | bulletins 26, 29th | Russia 1812 | ✓ downloaded |
| 25 | bpt6k9639050s | Lützen + Bautzen bulletins | Germany 1813 | ✓ downloaded |

Tomes 10, 12, 21 contain no numbered bulletins (administrative correspondence only).

**Note on bulletin series names:** The 1809 campaign uses "Bulletin de l'Armée d'Allemagne"
not "Bulletin de la Grande Armée". The standard Grande Armée title resumes for 1812–1813.

## All priority bulletins extracted — corpus complete

To re-extract all 11 bulletins from local tomes:
```
python3 scripts/extract-napoleon-bulletins.py
```

## Priority bulletins (11 documents)

| Slug | Date | Campaign |
|------|------|----------|
| napoleon-bulletin-1805-12-03-austerlitz | 1805-12-03 | Austerlitz |
| napoleon-bulletin-1805-12-04-austerlitz-aftermath | 1805-12-04 | Austerlitz |
| napoleon-bulletin-1806-10-14-jena | 1806-10-14 | Jena-Auerstedt |
| napoleon-bulletin-1806-10-27-berlin | 1806-10-27 | Jena-Auerstedt |
| napoleon-bulletin-1807-02-09-eylau | 1807-02-09 | Eylau |
| napoleon-bulletin-1807-06-14-friedland | 1807-06-14 | Friedland |
| napoleon-bulletin-1809-07-06-wagram | 1809-07-06 | Wagram |
| napoleon-bulletin-1809-07-11-wagram-aftermath | 1809-07-11 | Wagram |
| napoleon-bulletin-1812-09-10-russia-advance | 1812-09-10 | Russia |
| napoleon-bulletin-1812-12-03-russia-29th | 1812-12-03 | Russia (retreat) |
| napoleon-bulletin-1813-05-22-bautzen | 1813-05-22 | Germany |

The 29th Bulletin (1812-12-03) is analytically critical — it marks the
collapse of the sacrificial economy as the army dissolves in retreat.

## Notes

- All texts are French originals. Translation methodology must be resolved
  in `OPEN_DECISIONS.md` before annotation begins.
- Page numbers in the script are approximate. Verify OCR output covers the
  correct bulletin heading and full text.
- Key CMT terms to flag: *sacrifice*, *gloire*, *honneur*, *sang*, *patrie*,
  *corps*, *victoire*, *mort*, *devoir*, *immortel*.
- This register (military bulletin/proclamation) is the Napoleon case's
  closest analogue to Washington's general orders and Lincoln's war messages.
  Essential for cross-case register comparison.
- Per source-registry: `git_tracking = gitignored-local`.
