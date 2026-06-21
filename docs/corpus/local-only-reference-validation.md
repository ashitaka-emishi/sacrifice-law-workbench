# Local-Only Corpus Reference Validation

Some source material is lawful for a qualified researcher to hold locally but
is not distributed through this repository. The Hitler case currently uses
this boundary for source text, normalized text, segmented records, and detailed
MIPVU worklists. Committed CMT and interpretive annotations still require
stable, testable references into those artifacts.

## Decision

The repository commits a public-safe reference index at:

```text
cases/hitler/metadata/local-corpus-reference-index.json
```

The index contains only:

- document, sentence, and MIPVU identifiers;
- document-to-sentence and sentence-to-MIPVU relationships;
- the MIPVU decision type needed to validate downstream eligibility; and
- canonical SHA-256 content hashes for local artifacts and the referenced
  records.

It contains no source text, sentence text, lexical text, lemmas, glosses, or
evidence snippets. Committing the index does not change the source registry's
`gitignored-local-fair-use` decision.

## Validation modes

In a clean checkout, `npm run validate` resolves committed annotation
references through the index and prints a notice that local source-derived
artifacts are unavailable. This verifies referential integrity and controlled
decision types, but not the hidden text itself.

In an authorized local environment, validation also hashes every indexed
segmented document and MIPVU worklist. Artifact hashes exclude only volatile
generation timestamps, pipeline logs, and machine-local raw paths; all
source-derived content remains covered. A changed, stale, or incorrectly
restored artifact fails validation instead of silently using the index.
Unknown or mistyped IDs fail in both modes.

`--strict` continues to require the full MIPVU worklists; the public index is
not a substitute for strict source-level validation.

## Restore and verify authorized artifacts

1. Follow the acquisition instructions in
   `cases/hitler/metadata/source-registry.json`.
2. Place raw files only at the declared gitignored paths.
3. Run normalization, segmentation, and MIPVU generation/review under the
   documented case workflow.
4. Run:

   ```bash
   python3 scripts/validate-json.py --case hitler
   ```

   Validation must report that local artifacts match the committed hashes.

If an authorized source correction intentionally changes sentence boundaries,
lexical units, decisions, or file bytes, review the downstream annotations and
then regenerate the index:

```bash
python3 scripts/generate-local-corpus-reference-index.py --case hitler
```

Review the index diff before committing it. A content-hash update is an audit
event; routine timestamp or local-path churn does not change it.

## Publication boundary

Source text and source-derived records remain local-only unless a separate
rights review explicitly authorizes publication. Evidence snippets already
present in committed higher-level annotations are governed by their existing
review; this index neither expands nor republishes them.

Pipeline status records use repository-relative paths so they remain portable.
They describe expected local locations and generation history; they do not
prove that an artifact exists in another checkout.
