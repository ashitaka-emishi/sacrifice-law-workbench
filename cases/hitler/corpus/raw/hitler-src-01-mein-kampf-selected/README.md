# Mein Kampf — German Archive.org OCR source text (local only)

Text files in this directory are **gitignored** and must be placed locally before
running the normalize/segment pipeline. They are not committed to the repository.

## Source

Archive.org item `mein-kampf-german_202412`, file
`Mein_Kampf_German_djvu.txt`, OCR of the 1943 Franz Eher Nachfolger German
edition.

Actual downloaded document URL:
`https://archive.org/download/mein-kampf-german_202412/Mein_Kampf_German_djvu.txt`

The IfZ critical edition is the scholarly cross-reference. It is not the
downloaded corpus text.

## Required files

Only the files listed here are manifest-backed corpus inputs. Older English
Murphy slug variants may exist locally as gloss/reference working files; do not
normalize them or use them as `source_url` evidence for the German corpus.

| File | Chapter |
|------|---------|
| `vol1-ch2-wien.txt` | Band I, Kap. 2: Wiener Lehr- und Leidensjahre |
| `vol1-ch11-volk-und-rasse.txt` | Band I, Kap. 11: Volk und Rasse |
| `vol1-ch12-erste-periode-nsdap.txt` | Band I, Kap. 12: Die erste Periode der Entwicklung der NSDAP |
| `vol2-ch1-weltanschauung-und-partei.txt` | Band II, Kap. 1: Weltanschauung und Partei |
| `vol2-ch2-der-staat.txt` | Band II, Kap. 2: Der Staat |
| `vol2-ch14-ostorientierung.txt` | Band II, Kap. 14: Ostorientierung oder Ostpolitik |

## Required provenance header format

Each file must begin with a provenance block followed by a `=====...=====` separator:

```
SOURCE: Mein Kampf, Adolf Hitler. Zentralverlag der NSDAP., Frz. Eher Nachf., G.m.b.H., München.
Edition: 851.–855. Auflage, 1943.
Archive.org identifier: mein-kampf-german_202412 (djvu OCR).
URL: https://archive.org/download/mein-kampf-german_202412/Mein_Kampf_German_djvu.txt
Volume/Chapter: Band I, Kapitel 2
Local use: scholarly fair use — gitignored, not committed, not published.
Rights status: see cases/hitler/metadata/source-registry.json and OPEN_DECISIONS.md.

========================================================================

[German text body here]
```

## Gloss reference

Murphy 1939 English translation (Project Gutenberg Australia) is the working
gloss reference. Do not replace the German corpus text with Murphy.

If a different digital source is used, update both the provenance `URL:` line
and the corresponding `source_url` in `cases/hitler/metadata/document-manifest.json`
before running `scripts/normalize-texts.py`.
