---
description: Extract selected Mein Kampf chapters from the public-domain 1943 Eher German edition (via Archive.org) into the Hitler corpus raw directory. Chapters are gitignored. Run this skill when German source text is needed for the hitler case.
allowed-tools: Bash, Write, Read
---

Extract German-language Mein Kampf chapters from the public-domain 1943 Franz Eher Nachfolger edition, sourced from Archive.org (`mein-kampf-german_202412`). The German original is public domain in the US since 2020 (95 years after 1925 publication). Files are gitignored and must never be committed.

> **Scripted path:** `scripts/fetch-corpus.py` handles all MK chapter downloads automatically (curl + marker extraction + provenance header). Run `/corpus-download hitler` or `python3 scripts/fetch-corpus.py --case hitler` as the first step. Use this skill only if the script fails or you need interactive inspection of a specific chapter.

Critical invariant: `source_url` in `cases/hitler/metadata/document-manifest.json` must point to the actual downloaded document text, not to IfZ, Murphy, a translation, or another candidate source. For these chapters the actual downloaded document is `https://archive.org/download/mein-kampf-german_202412/Mein_Kampf_German_djvu.txt`. If you switch sources, update the provenance `URL:` and the manifest `source_url` together before running normalization.

`$ARGUMENTS`: optional chapter slug to extract just one chapter. If omitted, extract all 6.

Valid slugs: `vol1-ch2-wien`, `vol1-ch11-volk-und-rasse`, `vol1-ch12-erste-periode-nsdap`, `vol2-ch1-weltanschauung-und-partei`, `vol2-ch2-der-staat`, `vol2-ch14-ostorientierung`

---

## Chapter map

| Slug | German title | Band/Kapitel | Approx words |
|------|-------------|--------------|-------------|
| vol1-ch2-wien | Wiener Lehr- und Leidensjahre | Band I, Kap. 2 | ~15700 |
| vol1-ch11-volk-und-rasse | Volk und Rasse | Band I, Kap. 11 | ~15900 |
| vol1-ch12-erste-periode-nsdap | Die erste Entwicklungszeit der NSDAP | Band I, Kap. 12 | ~12850 |
| vol2-ch1-weltanschauung-und-partei | Weltanschauung und Partei | Band II, Kap. 1 | ~6900 |
| vol2-ch2-der-staat | Der Staat | Band II, Kap. 2 | ~18000 |
| vol2-ch14-ostorientierung | Ostorientierung oder Ostpolitik | Band II, Kap. 14 | ~9300 |

Output dir: `cases/hitler/corpus/raw/hitler-src-01-mein-kampf-selected/`

---

## Step 1: Download source text if not cached

```bash
CACHE=/tmp/mk_german_eher1943.txt
if [ ! -f "$CACHE" ] || [ $(wc -c < "$CACHE") -lt 1600000 ]; then
  echo "Downloading German MK text (~1.6MB)..."
  curl -sL "https://archive.org/download/mein-kampf-german_202412/Mein_Kampf_German_djvu.txt" -o "$CACHE"
  echo "Downloaded: $(wc -c < $CACHE) bytes"
else
  echo "Using cached file: $(wc -c < $CACHE) bytes"
fi
```

## Step 2: Extract chapters

Run this Python extraction script:

```bash
python3 - <<'PYEOF'
import sys, re, json
from pathlib import Path

SOURCE_URL = 'https://archive.org/download/mein-kampf-german_202412/Mein_Kampf_German_djvu.txt'
text = open('/tmp/mk_german_eher1943.txt', encoding='utf-8', errors='replace').read()
ROOT = Path('cases/hitler/corpus/raw/hitler-src-01-mein-kampf-selected')
ROOT.mkdir(parents=True, exist_ok=True)

PROVENANCE = """SOURCE: Mein Kampf, Adolf Hitler. Zentralverlag der NSDAP., Frz. Eher Nachf., G.m.b.H., München.
Edition: 851.–855. Auflage, 1943 (same base text as all Eher editions from 1925/1926).
Archive.org identifier: mein-kampf-german_202412 (djvu OCR of 1943 print edition).
URL: https://archive.org/download/mein-kampf-german_202412/Mein_Kampf_German_djvu.txt
Rights: German original copyright (Franz Eher Nachf.) expired in U.S. 2020 (95yr from 1925/1926 publication).
Local use: gitignored — scholarly annotation use only; not committed, not published.
See: cases/hitler/metadata/source-registry.json and OPEN_DECISIONS.md.
Gloss reference: Murphy 1939 English translation (Project Gutenberg Australia) — not corpus text.

========================================================================

"""

CHAPTERS = {
    'vol1-ch2-wien': {
        'start_marker': 'Wiener Lehr- und Leidensjahre',
        'start_min': 85000,
        'end_marker': '3. Kapitel',
        'end_min_offset': 1000,
        'title': 'Band I, Kapitel 2: Wiener Lehr- und Leidensjahre',
    },
    'vol1-ch11-volk-und-rasse': {
        'start_marker': 'Volk und Rasse',
        'start_min': 650000,
        'end_marker': '12. Kapitel',
        'end_min_offset': 1000,
        'title': 'Band I, Kapitel 11: Volk und Rasse',
    },
    'vol1-ch12-erste-periode-nsdap': {
        'start_marker': 'Die erste Entwicklungszeit der National-',
        'start_min': 780000,
        'end_marker': 'Zweiter Band',
        'end_min_offset': 1000,
        'title': 'Band I, Kapitel 12: Die erste Entwicklungszeit der Nationalsozialistischen Deutschen Arbeiterpartei',
    },
    'vol2-ch1-weltanschauung-und-partei': {
        'start_marker': 'Weltanschauung und Partei',
        'start_min': 870000,
        'end_marker': 'Der Staat',
        'end_min_offset': 1000,
        'title': 'Band II, Kapitel 1: Weltanschauung und Partei',
    },
    'vol2-ch2-der-staat': {
        'start_marker': 'Der Staat',
        'start_min': 910000,
        'end_marker': '3. Kapitel',
        'end_min_offset': 1000,
        'title': 'Band II, Kapitel 2: Der Staat',
    },
    'vol2-ch14-ostorientierung': {
        'start_marker': 'Ostorientierung oder Ostpolitik',
        'start_min': 1490000,
        'end_marker': '15. Kapitel',
        'end_min_offset': 1000,
        'title': 'Band II, Kapitel 14: Ostorientierung oder Ostpolitik',
    },
}

DOC_IDS = {
    'vol1-ch2-wien': 'hitler-mein-kampf-vol1-ch2-wien',
    'vol1-ch11-volk-und-rasse': 'hitler-mein-kampf-vol1-ch11-race-and-people',
    'vol1-ch12-erste-periode-nsdap': 'hitler-mein-kampf-vol1-ch12-nsdap',
    'vol2-ch1-weltanschauung-und-partei': 'hitler-mein-kampf-vol2-ch1-weltanschauung',
    'vol2-ch2-der-staat': 'hitler-mein-kampf-vol2-ch2-the-state',
    'vol2-ch14-ostorientierung': 'hitler-mein-kampf-vol2-ch14-eastern-europe',
}

target = sys.argv[1] if len(sys.argv) > 1 else 'all'
slugs = [target] if target != 'all' else list(CHAPTERS.keys())
written_doc_ids = set()

for slug in slugs:
    if slug not in CHAPTERS:
        print(f'ERROR: unknown slug {slug!r}')
        continue
    ch = CHAPTERS[slug]
    start_idx = text.find(ch['start_marker'], ch['start_min'])
    if start_idx < 0:
        print(f'ERROR: {slug}: start marker not found')
        continue
    end_idx = text.find(ch['end_marker'], start_idx + ch['end_min_offset'])
    if end_idx < 0:
        print(f'ERROR: {slug}: end marker not found')
        continue
    body = text[start_idx:end_idx].strip()
    out = ROOT / f'{slug}.txt'
    out.write_text(PROVENANCE + body + '\n', encoding='utf-8')
    words = len(body.split())
    written_doc_ids.add(DOC_IDS[slug])
    print(f'  wrote {slug}.txt  ({words} words, {len(body)} chars)')

manifest_path = Path('cases/hitler/metadata/document-manifest.json')
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
changed = False
for doc in manifest.get('documents', []):
    if doc.get('document_id') in written_doc_ids and doc.get('source_url') != SOURCE_URL:
        doc['source_url'] = SOURCE_URL
        changed = True
if changed:
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'  updated manifest source_url for {len(written_doc_ids)} document(s)')

PYEOF
```

If a slug argument was provided by `$ARGUMENTS`, pass it to the Python script:
```bash
python3 - "$ARGUMENTS" <<'PYEOF'
... (same script)
PYEOF
```

## Step 3: Verify output

```bash
for f in cases/hitler/corpus/raw/hitler-src-01-mein-kampf-selected/vol*.txt; do
  words=$(wc -w < "$f")
  echo "  $f: $words words"
done
```

All 6 files should be present with word counts roughly matching the chapter map above.

## Step 4: Re-run pipeline for hitler case

After all files are in place:

```bash
python3 scripts/normalize-texts.py --case hitler
python3 scripts/segment-texts.py --case hitler
```

Confirm output:
```bash
echo "normalized:" && ls cases/hitler/corpus/text/
echo "segmented:" && ls cases/hitler/corpus/segmented/
```

## Step 5: Verify the downloaded files

After placing the chapter files, run the corpus verifier:

```bash
python3 scripts/verify-corpus.py --case hitler
```

A PASS on all three checks (file present, word count, required phrases) confirms the correct chapter was extracted to the correct location. If any check FAILs, report the failure detail to the user and do not proceed to the pipeline steps until it is resolved.
