# Human Coder Launch Bundles

`scripts/human_reliability/generate_launch_bundle.py` creates a coder-facing
handoff directory for one approved human reliability cohort. It wraps an
already generated blind packet with task overview, training copy, calibration
instructions, declarations, allowed-reference rules, return instructions, and a
bundle manifest.

Run:

```bash
python3 scripts/human_reliability/generate_launch_bundle.py \
  --case <case_id> \
  --cohort cases/<case_id>/quality/human-reliability/cohorts/<cohort>.json
```

The output is written beneath:

```text
cases/<case_id>/quality/human-reliability/launch-bundles/<cohort-id>-<version>/
```

## Bundle Contents

Each generated bundle contains:

- `README.md`: task overview, time estimate, included files, rights/storage
  note, and packet hash;
- `packet/`: blind packet payload, blank CSV/JSON response templates, and
  packet manifest;
- `training/human-coder-training-guide.md`: required training guide copy;
- `references/`: coder-facing method and submission-contract references;
- `calibration-instructions.md`: source-language calibration requirements;
- `coder-declarations.md`: conflict-of-interest, independence, AI-assistance,
  and source-language competence declarations;
- `allowed-references.md`: allowed references and prohibited materials; and
- `return-instructions.md`: return, contact, and escalation procedure.

The bundle manifest records hashes for generated and copied files so the
distributed handoff can be audited.

## Safety Rules

Generation requires:

- an approved cohort manifest with a current approval hash;
- a current packet manifest and payload hashes;
- matching cohort and packet identity;
- `storage_policy: repository_allowed`; and
- `ai_assistance_allowed: false`.

The generator refuses path members that point at internal answer keys,
adjudication, model-reliability, normalized submissions, or accepted-artifact
subtrees. It copies packet payloads from the packet manifest and verifies their
hashes before writing the launch bundle.
