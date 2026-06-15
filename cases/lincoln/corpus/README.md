# Lincoln / American Civil War Corpus

Raw corpus texts may be committed only after rights/licensing review.

## Scholarly Corpus Status

The Lincoln pilot corpus is treated as a documented scholarly corpus, not just
a folder of texts. The current register is
`cases/lincoln/metadata/corpus-register.csv`; it records text identity, date,
period, genre, register, source edition, source URL, authorship confidence,
editorial status, inclusion rationale, risk flags, corpus layer, rights status,
Git tracking policy, expected local path, and known limitations.

All three current Lincoln texts are public-domain, committed, balanced-core
pilot documents acquired from Project Gutenberg transcriptions with headers and
footers stripped. Canonical manuscript or scholarly-edition cross-check URLs
are preserved in `cases/lincoln/metadata/source-registry.json`.

## Stable Identifier Policy

The segmentation pipeline creates TEI-inspired stable analytical units:

- document IDs from `metadata/document-manifest.json`;
- one body section per current Lincoln text;
- paragraph IDs in the form `<document_id>_s01_pNN`;
- sentence IDs in the form `<document_id>_s01_pNN_sNN`;
- lexical-unit IDs in the form `<sentence_id>_luNNN`.

These identifiers are the expected audit path from claim to lexical unit,
sentence, document metadata, source text, and historical corroboration where
claimed. If text normalization or segmentation changes, regenerate downstream
MIPVU worklists with preservation enabled and review any changed identifiers
before treating prior annotations as stable.
