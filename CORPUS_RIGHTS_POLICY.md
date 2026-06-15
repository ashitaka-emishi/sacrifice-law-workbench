# Corpus Rights Policy

V1 is restricted to public-domain and open-access corpora that can be legally cited, downloaded, mirrored when permitted, or referenced through stable source metadata.

## Rights review gate

No source may be copied into `corpus/raw/` until it passes a rights/licensing review gate, even if it appears public-domain or open-access.

Acquisition helpers do not replace this gate. Before using `scripts/fetch-corpus.py`
or a corpus download skill, the relevant source and document records should
identify the source URL or citation, rights status, storage decision, and
expected local path.

## Storage policy

When rights permit, raw corpus texts should be stored directly in the Git repository.

When licensing, archive terms, translation status, or rights uncertainty prevent committing raw texts, those files should be stored locally in expected project paths but excluded from Git via `.gitignore`.

The source registry must preserve:

- source URL;
- archive;
- bibliographic citation;
- rights/licensing review status;
- acquisition instructions;
- expected local path;
- rights rationale;
- Git tracking status: `committed`, `gitignored-local`, `metadata-only`, or `unavailable`.

## Acquisition workflow

Use the source status reporter to check what is present, missing, or blocked:

```bash
python3 scripts/acquire-sources.py --case <case-id>
```

For curl-accessible sources, use:

```bash
python3 scripts/fetch-corpus.py --case <case-id>
python3 scripts/fetch-corpus.py --doc <document-id>
```

`fetch-corpus.py` handles supported public/open direct-fetch sources and runs
post-acquisition verification by default. It reports sources that require the
interactive `/corpus-download` skill, such as Founders Online pages,
Gallica CAPTCHA/browser fallback, and local-only fair-use materials.

The source-specific downloader skills are part of the controlled acquisition
workflow. They should preserve provenance, write files to manifest-declared
paths, and run verification before downstream pipeline stages proceed.

## Post-acquisition verification

After a raw file is placed, run:

```bash
python3 scripts/verify-corpus.py --case <case-id>
```

This checks three things against the `verification` block in each document's manifest entry:

1. **File present** — `expected_raw_path` exists and is non-empty.
2. **Word count** — body text (after stripping the provenance header) meets `min_words`.
3. **Required phrases** — 2–3 anchor strings that uniquely identify the correct document are present.

A PASS on all three is required before the document may proceed to normalization and segmentation. Add a `verification` block to the manifest entry when adding a new document. See existing entries in any `document-manifest.json` for the format.

## OCR

Avoid OCR unless no clean public-domain/open-access text source exists and the source is analytically important enough to justify quality-control burden.
