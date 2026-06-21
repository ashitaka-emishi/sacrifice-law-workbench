# Deterministic Blind Human Coding Packets

`scripts/human_reliability/generate_packets.py` converts one approved,
access-controlled human sample manifest into a coder-safe packet and blank CSV
and JSON response templates. It writes only beneath:

```text
cases/<case_id>/quality/human-reliability/packets/<sample>-<version>-<layer>/
```

Run:

```bash
python3 scripts/human_reliability/generate_packets.py \
  --case <case_id> \
  --sample cases/<case_id>/quality/human-reliability/samples/sample-manifest.json
```

Each sample is scoped to one case, source language, and task layer. The output
contains:

- `<layer>-packet.jsonl`: source-language coding items;
- `<layer>-response-template.csv`: spreadsheet template;
- `<layer>-response-template.json`: equivalent structured template; and
- `packet-manifest.json`: sample, source, generator, payload, and identity
  hashes.

Identification packets include every lexical unit in each selected complete
sentence, preserving ordinary negative controls and multiple lexical units.
CMT and interpretation packets accept a stable annotation/span ID, a stable
MIPVU lexical-unit ID for a negative control, or a bounded sentence context.

## Approval and determinism

Generation requires:

- sample `status: approved`;
- execution `status: approved_to_execute`;
- a canonical `approval.manifest_sha256` computed with that field set to
  `null`;
- a frozen source language, codebook version, seed, rights policy, and stable
  item IDs; and
- locally available segmented and MIPVU source artifacts.

The seed deterministically shuffles packet item order without exposing design
roles. JSONL uses canonical UTF-8 serialization, CSV uses a fixed column order
and LF endings, and no timestamp participates in identity. Re-running with
unchanged inputs and code revision produces byte-identical outputs.

The response template's `packet_hash` remains `null`; issue #80 defines the
submission contract and how a coder binds a completed response to the packet
manifest without introducing a circular payload hash.

## Blindness allowlist

Coder-visible outputs contain only neutral identity, source-language text,
stable offsets, optional separately labeled English glosses, context scope,
and rights instructions. They never serialize coordinator design roles,
accepted MIPVU/CMT/interpretive values, claim impact, model outputs, prior
coder values, agreement results, adjudication, support scores, or synthesis.

The generator recursively rejects prohibited keys in packets and templates.
The role-bearing sample manifest remains access-controlled until both primary
submissions are frozen. `source_inputs` in the packet manifest records paths
and hashes for audit; coders receive only the generated packet directory, not
the coordinator manifest or referenced accepted artifacts.

Hitler packets require the authorized local German artifacts and remain under
the existing gitignored human-reliability boundary. The public-safe reference
index is insufficient to generate source-text packets.
