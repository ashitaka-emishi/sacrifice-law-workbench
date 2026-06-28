#!/usr/bin/env python3
"""Generate CMT and Koenigsbergian annotation layer from MIPVU decisions.

For each reviewed MIPVU document, this script:
  1. Groups metaphorical and uncertain LUs by sentence + curated_rule_id.
  2. Derives a CMT mapping per group using candidate domain fields.
  3. Writes per-document annotated JSON to corpus/annotated/.
  4. Writes a per-case CMT mapping file to corpus/cmt/cmt-mappings.json.

Only LUs with decision_type in MIPVU_METAPHOR_OR_UNCERTAIN_DECISIONS are processed.
No annotation is created from purely theoretical interest without MIPVU evidence.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline_common import (
    MIPVU_METAPHOR_OR_UNCERTAIN_DECISIONS,
    annotated_path_for,
    case_dir,
    case_ids,
    cluster_config,
    cmt_mappings_path_for,
    documents,
    document_id,
    mipvu_path_for,
    now_iso,
    read_json,
    segmented_path_for,
    write_json,
)

TODAY = datetime.now().strftime("%Y-%m-%d")

# Maps MIPVU candidate_source_domain values → controlled-vocabulary source_domain IDs.
SOURCE_DOMAIN_MAP: dict[str, str] = {
    "body": "body",
    "body_blood": "body",
    "disease": "disease",
    "wound_injury": "wound_injury",
    "medicine_healing": "medicine_healing",
    "birth_generation": "birth_generation",
    "family_inheritance": "family_inheritance",
    "architecture_building": "architecture_building",
    "building_structure": "architecture_building",
    "law_contract": "law_contract",
    "debt_accounting": "debt_accounting",
    "religion_providence": "religion_providence",
    "ritual_religion": "ritual_religion",
    "sacrifice": "sacrifice",
    "journey_motion": "journey_motion",
    "experiment_science": "experiment_science",
    "trial_testing": "experiment_science",
    "agriculture": "agriculture",
    "mechanics": "mechanics",
    "war_combat": "war_combat",
    "light_darkness": "light_darkness",
    "slavery_bondage": "slavery_bondage",
    "nature_organism": "nature_organism",
    "nature_growth": "nature_organism",
    "earth_nature": "nature_organism",
    "plant_nature": "nature_organism",
    "object_material": "object_material",
    "object_attachment": "object_material",
    "object_covering": "object_material",
    "object_transfer": "object_material",
    "physical_destruction": "physical_destruction",
    "person_agency": "person_agency",
    "person_virtue": "person_agency",
    "person_inner_life": "person_agency",
    "person_reputation": "person_agency",
    "creation_making": "birth_generation",
    "life_death": "life_death",
    "theater_stage": "theater_stage",
    "mind_intellect": "person_agency",
}

# Maps MIPVU candidate_target_domain values → controlled-vocabulary target_domain IDs.
TARGET_DOMAIN_MAP: dict[str, str] = {
    "nation": "nation",
    "union": "union",
    "constitution": "constitution",
    "republic": "republic",
    "democracy": "democracy",
    "freedom": "freedom",
    "liberty": "freedom",
    "slavery": "slavery",
    "civil_war": "civil_war",
    "emancipation": "emancipation",
    "sacrifice": "sacrifice",
    "founding": "founding",
    "founding_sacrifice": "sacrifice",
    "providence": "providence",
    "reconciliation": "reconciliation",
    "citizenship": "citizenship",
    "obligation": "citizenship",
    "enemy": "enemy",
    "foreign_threat": "enemy",
    "enemy_as_bringer_of_death": "enemy",
    "monarchy": "government",
    "people": "people",
    "law": "law",
    "history": "history",
    "historical_memory": "history",
    "imperial_memory": "history",
    "government": "government",
    "political_institutions": "government",
    "political_ambition": "political_order",
    "political_security": "political_order",
    "political_danger": "political_order",
    "political_relation": "political_order",
    "political_inheritance": "political_order",
    "political_emotion": "political_identity",
    "political_identity": "political_identity",
    "self_government": "republic",
    "independence": "independence",
    "rights": "freedom",
    "civic_reason": "citizenship",
    "civil_order": "political_order",
    "racial_identity": "racial_identity",
    "racial_ideological_dominance": "racial_order",
    "group_elimination": "purification",
    "social_elimination": "purification",
    "military_virtue": "military_virtue",
    "military_sacrifice": "sacrifice",
    "war_death": "war_death",
    "war": "war_death",
    "battle": "war_death",
    "campaign_outcome": "war_death",
    "army": "army",
    "artillery": "army",
    "victory": "military_virtue",
    "imperial_authority": "imperial_authority",
    "patrie": "nation",
    "society": "social_body",
    "reason": "social_body",
    "mob_violence": "political_order",
    "civilizational_agency": "racial_order",
    "collective_psychology": "social_body",
    "national_standing": "nation",
    "national_destruction": "nation",
    "life_circumstances": "social_body",
    "life_death": "war_death",
    "territorial_ideology": "racial_order",
    "exploitation": "political_order",
    "death": "war_death",
    "peace": "reconciliation",
    "self_denial": "sacrifice",
    "struggle": "struggle",
    "rebirth": "rebirth",
}


# ---------------------------------------------------------------------------
# Koenigsbergian classification term-sets (module-level constants)
# ---------------------------------------------------------------------------

_SACRIFICIAL_TERMS: frozenset[str] = frozenset({
    "sacrifice", "martyr", "death", "gift", "offering", "blood", "dying", "die", "gave",
})
_VIOLENCE_TERMS: frozenset[str] = frozenset({
    "war", "combat", "parasite", "disease", "purif", "surg", "enemy", "destroy", "kill", "exterminate",
})
_OBLIGATORY_TERMS: frozenset[str] = frozenset({
    "obligat", "duty", "must", "covenant", "oath", "dedicate", "consecrat",
})
_SUPPRESSED_GROUPS: frozenset[str] = frozenset({
    "soldier", "worker", "subject", "people", "enslaved", "colonized",
})


# ---------------------------------------------------------------------------
# Cluster matching
# ---------------------------------------------------------------------------

def _best_cluster(
    source: str,
    target: str,
    conceptual_metaphor: str,
    clusters: list[dict],
) -> str:
    if not clusters:
        return "unknown-cluster"
    combined = (source + "_" + target + "_" + conceptual_metaphor).lower()
    tokens = set(combined.split("_"))
    for cluster in clusters:
        cid = cluster.get("id")
        if not cid:
            continue
        for kw in cluster.get("keywords", []):
            if kw in tokens or kw in combined:
                return str(cid)
    return str(clusters[0].get("id", "unknown-cluster"))


# ---------------------------------------------------------------------------
# Sentence text lookup
# ---------------------------------------------------------------------------

def _build_sentence_index(case_id: str, doc: dict) -> dict[str, str]:
    """Return sentence_id -> text mapping from segmented document."""
    path = segmented_path_for(case_id, doc)
    data = read_json(path, {}) or {}
    index: dict[str, str] = {}
    for section in data.get("sections", []) or []:
        for para in section.get("paragraphs", []) or []:
            for sent in para.get("sentences", []) or []:
                if isinstance(sent, dict) and sent.get("sentence_id"):
                    index[sent["sentence_id"]] = sent.get("text", "")
    return index


# ---------------------------------------------------------------------------
# CMT + Koenigsbergian derivation
# ---------------------------------------------------------------------------

def _koenigsberg_for(
    cluster_id: str,
    source: str,
    target: str,
    conceptual_metaphor: str,
    lus: list[dict],
) -> dict[str, Any]:
    """Derive Koenigsbergian annotation from cluster and domain signals."""
    src = (source or "").lower()
    tgt = (target or "").lower()
    cm = (conceptual_metaphor or "").lower()
    cid = (cluster_id or "").lower()

    # Detect sacrificial economy
    has_sacrificial = bool(_SACRIFICIAL_TERMS & set(src.split("_") + tgt.split("_") + cm.split()))

    # Detect violence logic
    has_violence = any(vt in src or vt in tgt or vt in cm for vt in _VIOLENCE_TERMS)

    # Detect obligatory frame
    has_obligatory = any(ot in cm for ot in _OBLIGATORY_TERMS)

    # Fantasy type
    fantasy_type: str | None = None
    if "nation" in tgt and ("organism" in src or "body" in src or "birth" in src or "life" in src):
        fantasy_type = "national_body"
    elif "sacrifice" in src or "sacrifice" in tgt or "martyr" in cid:
        fantasy_type = "redemptive_sacrifice"
    elif "parasite" in src or "disease" in src or "purif" in cid:
        fantasy_type = "purity_contamination"
    elif "destiny" in tgt or "destiny" in src or "struggle" in cid:
        fantasy_type = "destiny_struggle"
    elif "covenant" in src or "covenant" in tgt or "providenc" in src:
        fantasy_type = "providential_covenant"
    elif "rebirth" in tgt or "rebirth" in cid or "resurrection" in tgt:
        fantasy_type = "rebirth_redemption"

    # Absence flag — note suppressed or absent agency
    absence_flags: list[str] = []
    for lu in lus:
        notes = (lu.get("review_notes") or "").lower()
        if any(sg in notes for sg in _SUPPRESSED_GROUPS):
            absence_flags.append("possible-suppressed-agent")
            break

    result: dict[str, Any] = {}
    if fantasy_type:
        result["fantasy_type"] = fantasy_type
    if has_violence:
        result["violence_logic"] = True
    if has_obligatory:
        result["obligatory_frame"] = True
    if has_sacrificial:
        result["sacrificial_economy"] = True
    if absence_flags:
        result["absence_flags"] = absence_flags

    return result


def _cmt_for_group(
    group_lus: list[dict],
    sentence_text: str,
    cluster_id: str,
    case_prefix: str,
    mapping_counter: int,
    source: str = "",
    target: str = "",
) -> dict[str, Any]:
    """Build one CMT annotation instance from a group of same-sentence/same-rule LUs."""
    first = group_lus[0]
    doc_id: str = str(first.get("document_id", ""))
    sentence_id: str = str(first.get("sentence_id", ""))

    # Use caller-supplied mapped domains if provided; fall back to raw LU fields.
    if not source:
        source = SOURCE_DOMAIN_MAP.get(first.get("candidate_source_domain") or "", first.get("candidate_source_domain") or "")
    if not target:
        target = TARGET_DOMAIN_MAP.get(first.get("candidate_target_domain") or "", first.get("candidate_target_domain") or "")
    confidence_vals = [lu.get("confidence") for lu in group_lus if lu.get("confidence") is not None]
    confidence = round(sum(confidence_vals) / len(confidence_vals), 3) if confidence_vals else 0.7

    # Build expression from LU tokens
    lu_texts = [lu.get("span_text") or lu.get("lexical_unit") or "" for lu in group_lus]
    expression = " / ".join(t for t in lu_texts if t)

    # Derive conceptual metaphor label from domains
    src_label = re.sub(r"[_]+", " ", source).upper() if source else "SOURCE"
    tgt_label = re.sub(r"[_]+", " ", target).upper() if target else "TARGET"
    conceptual_metaphor = f"{tgt_label} IS {src_label}"

    # Build entailments from contextual meanings
    seen_entailments: set[str] = set()
    entailments: list[str] = []
    for lu in group_lus:
        ctx = (lu.get("contextual_meaning") or "").strip()
        if ctx and ctx not in seen_entailments:
            seen_entailments.add(ctx)
            entailments.append(ctx)
    comparison = (first.get("comparison_basis") or "").strip()
    if comparison and comparison not in seen_entailments:
        entailments.append(comparison)
    if not entailments:
        entailments = [f"{tgt_label.title()} is understood through {src_label.lower()}."]

    # Rival reading
    rival_reading = (first.get("contrast_explanation") or "").strip()
    if not rival_reading:
        rival_reading = f"Conventional usage may reduce the force of the {src_label.lower()} mapping."

    # Justification
    rule_id = str(first.get("curated_rule_id") or "")
    mipvu_ids = [str(lu.get("mipvu_id")) for lu in group_lus if lu.get("mipvu_id")]
    justification = (
        f"MIPVU review rule '{rule_id}' marked {len(mipvu_ids)} unit(s) as metaphor-related "
        f"or uncertain in this sentence."
    )

    # Rhetorical + ideological function inference
    src_l = source.lower()
    tgt_l = target.lower()
    rhetorical_functions: list[str] = []
    ideological_functions: list[str] = []
    if "sacrifice" in src_l or "martyr" in cluster_id:
        rhetorical_functions.append("commemoration")
        ideological_functions.append("sacrifice")
    if "war" in src_l or "combat" in src_l:
        rhetorical_functions.append("glorification")
        ideological_functions.append("violence_legitimation")
    if "nation" in tgt_l or "republic" in tgt_l or "people" in tgt_l:
        rhetorical_functions.append("national_self_definition")
        ideological_functions.append("obligation")
    if "disease" in src_l or "parasite" in src_l or "purif" in cluster_id:
        ideological_functions.append("dehumanization")
        rhetorical_functions.append("threat_construction")
    if "providenc" in src_l or "covenant" in src_l:
        rhetorical_functions.append("sacralization")
        ideological_functions.append("guilt_distribution")
    if not rhetorical_functions:
        rhetorical_functions = ["argument"]
    if not ideological_functions:
        ideological_functions = ["legitimation"]

    mapping_id = f"{case_prefix}-cmt-{mapping_counter:03d}"

    return {
        "mapping_id": mapping_id,
        "case_id": str(first.get("case_id", "")),
        "document_id": doc_id,
        "sentence_id": sentence_id,
        "mipvu_ids": mipvu_ids,
        "expression": expression,
        "evidence_span": sentence_text,
        "source_domain_primary": source or "unspecified",
        "source_domain_secondary": [],
        "target_domain": target or "unspecified",
        "conceptual_metaphor": conceptual_metaphor,
        "entailments": entailments[:4],
        "cluster_id": cluster_id,
        "confidence": confidence,
        "rival_reading": rival_reading,
        "justification": justification,
        "mapping_status": "provisional",
        "rhetorical_salience": "medium" if confidence < 0.8 else "high",
        "rhetorical_functions": rhetorical_functions[:3],
        "ideological_functions": ideological_functions[:3],
    }


# ---------------------------------------------------------------------------
# Per-document annotated file
# ---------------------------------------------------------------------------

def _make_instance(
    cmt_mapping: dict[str, Any],
    group_lus: list[dict],
    clusters: list[dict],
) -> dict[str, Any]:
    """Build a single annotation instance in the annotated JSON format."""
    first = group_lus[0]
    source = cmt_mapping["source_domain_primary"]
    target = cmt_mapping["target_domain"]
    cm = cmt_mapping["conceptual_metaphor"]
    cluster_id = cmt_mapping["cluster_id"]

    koenigsberg = _koenigsberg_for(cluster_id, source, target, cm, group_lus)

    # gloss fields for non-English cases
    instance: dict[str, Any] = {
        "instance_id": cmt_mapping["mapping_id"].replace("-cmt-", "-ann-"),
        "case_id": cmt_mapping["case_id"],
        "document_id": cmt_mapping["document_id"],
        "sentence_id": cmt_mapping["sentence_id"],
        "span_text": cmt_mapping["expression"],
        "mipvu_ids": cmt_mapping["mipvu_ids"],
        "cmt": {
            "mapping_id": cmt_mapping["mapping_id"],
            "cluster_id": cluster_id,
            "source_domain_primary": source,
            "source_domain_secondary": cmt_mapping.get("source_domain_secondary", []),
            "target_domain": target,
            "conceptual_metaphor": cm,
            "entailments": cmt_mapping["entailments"],
            "confidence": cmt_mapping["confidence"],
            "rival_reading": cmt_mapping["rival_reading"],
            "justification": cmt_mapping["justification"],
        },
        "koenigsberg": koenigsberg,
        "meta": {
            "confidence": cmt_mapping["confidence"],
            "ambiguity_flag": any(lu.get("decision_type") == "uncertain" for lu in group_lus),
            "suppression_flag": bool(koenigsberg.get("absence_flags")),
        },
    }

    # Include gloss fields for non-English LUs
    gloss_en = first.get("gloss_en")
    gloss_notes = first.get("gloss_notes")
    if gloss_en:
        instance["gloss_en"] = gloss_en
    if gloss_notes:
        instance["gloss_notes"] = gloss_notes

    return instance


def process_document(
    case_id: str,
    doc: dict,
    clusters: list[dict],
    cmt_counter_start: int,
    dry_run: bool = False,
) -> tuple[list[dict], list[dict], int]:
    """Process one document; return (instances, cmt_mappings, next_counter)."""
    doc_id = document_id(doc)
    mipvu_path = mipvu_path_for(case_id, doc)
    mipvu_data = read_json(mipvu_path, {}) or {}

    lus = [
        lu for lu in (mipvu_data.get("lexical_units") or [])
        if lu.get("decision_type") in MIPVU_METAPHOR_OR_UNCERTAIN_DECISIONS
    ]
    if not lus:
        return [], [], cmt_counter_start

    sentence_index = _build_sentence_index(case_id, doc)
    case_prefix = re.sub(r"[^a-z0-9]", "", case_id.lower())

    # Group LUs by (sentence_id, curated_rule_id)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for lu in lus:
        sid = str(lu.get("sentence_id", ""))
        rule = str(lu.get("curated_rule_id", "no-rule"))
        groups[(sid, rule)].append(lu)

    instances: list[dict] = []
    cmt_mappings: list[dict] = []
    counter = cmt_counter_start

    for (sid, rule), group_lus in sorted(groups.items()):
        sentence_text = sentence_index.get(sid, "")
        raw_source = group_lus[0].get("candidate_source_domain") or ""
        raw_target = group_lus[0].get("candidate_target_domain") or ""
        source = SOURCE_DOMAIN_MAP.get(raw_source, raw_source)
        target = TARGET_DOMAIN_MAP.get(raw_target, raw_target)
        cm_label = f"{re.sub(r'[_]+', ' ', target).upper()} IS {re.sub(r'[_]+', ' ', source).upper()}"
        cluster_id = _best_cluster(source, target, cm_label, clusters)

        counter += 1
        cmt_mapping = _cmt_for_group(
            group_lus, sentence_text, cluster_id, case_prefix, counter,
            source=source, target=target,
        )
        instances.append(_make_instance(cmt_mapping, group_lus, clusters))
        cmt_mappings.append(cmt_mapping)

    return instances, cmt_mappings, counter


def write_annotated_file(
    case_id: str,
    doc: dict,
    instances: list[dict],
    dry_run: bool = False,
) -> Path:
    doc_id = document_id(doc)
    out_path = annotated_path_for(case_id, doc)
    payload: dict[str, Any] = {
        "version": "1.0",
        "case_id": case_id,
        "document_id": doc_id,
        "generated_at": now_iso(),
        "generator": "scripts/generate-annotation-layer.py",
        "annotation_policy": (
            "CMT and Koenigsbergian annotations derived from MIPVU-reviewed metaphorical "
            "and uncertain lexical units. Each instance cites at least one MIPVU ID with "
            "decision_type in MIPVU_METAPHOR_OR_UNCERTAIN_DECISIONS."
        ),
        "instances": instances,
    }
    if not dry_run:
        write_json(out_path, payload)
    return out_path


def write_cmt_mappings_file(
    case_id: str,
    all_mappings: list[dict],
    dry_run: bool = False,
) -> Path:
    out_path = cmt_mappings_path_for(case_id)

    # Preserve existing hand-crafted mappings that are not superseded by a
    # generated mapping for the same (sentence_id, cluster_id) pair.
    # Exclude previously generated mappings (identified by mapping_id pattern) to
    # prevent duplicates on re-runs.
    existing_data = read_json(out_path, {}) or {}
    existing_mappings: list[dict] = [
        m for m in (existing_data.get("mappings") or []) if isinstance(m, dict)
    ]
    case_prefix = re.sub(r"[^a-z0-9]", "", case_id)
    generated_id_prefix = f"{case_prefix}-cmt-"
    generated_keys: set[tuple[str, str]] = {
        (str(m.get("sentence_id", "")), str(m.get("cluster_id", "")))
        for m in all_mappings
    }
    preserved: list[dict] = []
    for m in existing_mappings:
        mid = str(m.get("mapping_id", ""))
        key = (str(m.get("sentence_id", "")), str(m.get("cluster_id", "")))
        if mid.startswith(generated_id_prefix):
            continue
        if key in generated_keys:
            print(
                f"WARNING: hand-crafted mapping {mid!r} discarded — "
                f"superseded by generated mapping for {key}",
                file=sys.stderr,
            )
            continue
        preserved.append(m)
    merged = preserved + all_mappings

    payload: dict[str, Any] = {
        "version": "1.0",
        "case_id": case_id,
        "status": "draft",
        "updated": TODAY,
        "mapping_policy": (
            "CMT mappings are downstream of MIPVU. Every non-exploratory mapping must "
            "cite metaphor-related or uncertain MIPVU lexical units from the same sentence."
        ),
        "mappings": merged,
    }
    if not dry_run:
        write_json(out_path, payload)
    return out_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process_case(case_id: str, dry_run: bool = False) -> dict[str, Any]:
    docs = documents(case_id)
    clusters = cluster_config(case_id)
    all_mappings: list[dict] = []
    written_files: list[str] = []
    total_instances = 0
    counter = 0

    for doc in docs:
        doc_id = document_id(doc)
        instances, cmt_mappings, counter = process_document(
            case_id, doc, clusters, counter, dry_run=dry_run
        )
        total_instances += len(instances)
        all_mappings.extend(cmt_mappings)
        if instances:
            path = write_annotated_file(case_id, doc, instances, dry_run=dry_run)
            written_files.append(str(path.relative_to(Path.cwd())))
        else:
            written_files.append(f"(skipped — no metaphorical LUs: {doc_id})")

    if all_mappings:
        cmt_path = write_cmt_mappings_file(case_id, all_mappings, dry_run=dry_run)
        written_files.append(str(cmt_path.relative_to(Path.cwd())))

    return {
        "case_id": case_id,
        "documents_processed": len(docs),
        "total_instances": total_instances,
        "total_cmt_mappings": len(all_mappings),
        "files": written_files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", default=None, help="Limit to one case")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and derive but do not write files",
    )
    args = parser.parse_args()

    results = [
        process_case(cid, dry_run=args.dry_run)
        for cid in case_ids(args.case_id)
    ]
    print(json.dumps({"script": Path(__file__).name, "results": results}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
