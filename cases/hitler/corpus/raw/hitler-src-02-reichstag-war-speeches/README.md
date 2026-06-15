# Hitler speeches — German source text (local only)

Text files in this directory are **gitignored** and must be placed locally before
running the normalize/segment pipeline. They are not committed to the repository.

## Source

These local raw files use German text from the actual digital sources named in
each provenance header:

- `reichstag-prophecy-1939-01-30.txt`: Reichstagsprotokolle full-text
  database, `https://www.reichstag-abgeordnetendatenbank.de/volltext.html`,
  cross-checked against BSB digitized volume `bsb00000613`.
- `proclamation-invasion-soviet-union-1941-06-22.txt`: Archive.org item
  `ProklamationDesFhrersAnDasDeutscheVolkUndNoteDesAuswrtigenAmtes`, with
  digital transcription notes in the raw file.

Max Domarus (ed.), *Hitler: Reden und Proklamationen 1932–1945*, Bd. 2, is the
scholarly cross-reference, not the downloaded corpus text. Do NOT use the
Domarus English edition (Bolchazy-Carducci, 1990–2004), which is under U.S.
copyright.

## Required files

| File | Speech | Actual digital source |
|------|--------|-------------|
| `reichstag-prophecy-1939-01-30.txt` | Rede vor dem Deutschen Reichstag, 30. Januar 1939 | Reichstagsprotokolle full-text database |
| `proclamation-invasion-soviet-union-1941-06-22.txt` | Proklamation an das deutsche Volk, 22. Juni 1941 | Archive.org/Metapedia transcription of official pamphlet |

## Required provenance header format

```
SOURCE: Verhandlungen des Deutschen Reichstags. Stenographische Berichte. 460. Band. 1939.
Document: Rede vor dem Deutschen Reichstag, 30. Januar 1939
Digital source: Reichstagsprotokolle full-text database.
URL: https://www.reichstag-abgeordnetendatenbank.de/volltext.html
Scholarly cross-reference: Domarus Bd. 2, S. 1047–1067
Local use: scholarly fair use — gitignored, not committed, not published.
Rights status: see cases/hitler/metadata/source-registry.json and OPEN_DECISIONS.md.

========================================================================

[German text body here]
```

## Gloss reference

German Propaganda Archive (Calvin University) English translations are the working
gloss reference. Do not replace the German corpus text with GPA translations.

If a speech source changes, update both the provenance `URL:` line and that
document's `source_url` in `cases/hitler/metadata/document-manifest.json`
before running `scripts/normalize-texts.py`.
