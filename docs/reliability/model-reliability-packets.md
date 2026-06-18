# Deterministic Blind Model Packets

`scripts/model_reliability/generate_packets.py` turns an approved case-local
sample manifest into separate identification, CMT, and interpretive JSONL
payloads. It writes only beneath
`cases/<case_id>/quality/model-reliability/packets/`.

The generator builds packet items from explicit allowlists. Model-visible files
contain stable IDs, source-language sentence and lexical-unit text, optional
separate English glosses, offsets, and neutral source-risk flags. They omit
accepted decisions, mappings, interpretive labels, confidence, adjudication,
support scores, and synthesis claims. CMT and interpretive prompts explicitly
describe their items as bounded classification exercises rather than accepted
metaphors.

The approved sample remains the source of selection authority. The generator
requires negative controls, ambiguous items, and claim-relevant items, but does
not expose those item labels or their distribution in the model-visible packet
or manifest. The manifest reports only neutral coverage totals.

## Determinism and provenance

Each JSONL row uses canonical key ordering and compact UTF-8 serialization.
The manifest records hashes for every payload, prompt, source input, and the
generator script; it also records the committed revision that last changed the
generator. `packet_hash` is the SHA-256 hash of the canonical manifest before
the `packet_hash` field is added. No timestamp participates in packet identity.

Running the generator again with unchanged inputs produces byte-identical
payloads, prompts, and manifest. Prompt and source changes alter their hashes;
generator changes alter both the script hash and code revision.

```bash
python3 scripts/model_reliability/generate_packets.py --case lincoln
```

The manifest and item shapes are defined by
`schemas/model-reliability/packet-manifest-schema.json` and
`schemas/model-reliability/packet-item-schema.json`. Source-derived Hitler
packets remain local under the repository's existing ignore policy.
