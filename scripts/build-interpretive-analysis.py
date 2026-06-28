#!/usr/bin/env python3
"""Build critical metaphor, rhetorical, and absence/agency artifacts."""
from __future__ import annotations

import argparse
from typing import Any

from pipeline_common import (
    case_dir,
    case_ids,
    cmt_mappings_path_for,
    document_id,
    documents,
    iter_cmt_mappings,
    now_iso,
    read_json,
    write_json,
)


DOCUMENT_CONTEXT: dict[str, dict[str, Any]] = {
    # ── Lincoln ──────────────────────────────────────────────────────────────
    "lincoln-lyceum-address": {
        "audience": "Young Men's Lyceum of Springfield and a civic public concerned with republican institutions",
        "occasion": "Early public address on mob violence, political inheritance, and the perpetuation of American institutions",
        "genre": "public address",
        "rhetorical_action": "Warns that republican survival depends on civic discipline and reverence for law.",
        "emotional_posture": "warning",
        "agency_structure": {
            "agents": ["we", "nation of freemen", "citizens"],
            "patients": ["nation", "political institutions"],
            "beneficiaries": ["future republic", "American people"],
            "passive_or_absent": ["enslaved people", "women", "Indigenous people"],
            "displacement_mechanism": "National survival is framed as collective self-preservation rather than as conflict among named social groups.",
        },
    },
    "lincoln-gettysburg-address": {
        "audience": "Cemetery dedication audience, Union public, mourners, soldiers, and national readers",
        "occasion": "Dedication of the national cemetery after the Battle of Gettysburg",
        "genre": "ceremonial address",
        "rhetorical_action": "Transforms battlefield death into renewed obligation to preserve democratic government and freedom.",
        "emotional_posture": "mourning, consecration, exhortation",
        "agency_structure": {
            "agents": ["honored dead", "living citizens", "we"],
            "patients": ["dead soldiers", "nation", "government of the people"],
            "beneficiaries": ["nation", "freedom", "democratic government"],
            "passive_or_absent": ["Confederate agency", "enslaved people's own agency", "civilian suffering"],
            "displacement_mechanism": "Deaths are generalized as national offering and obligation; specific agents and material bodies recede behind public dedication.",
        },
    },
    "lincoln-second-inaugural": {
        "audience": "Second inaugural audience, wartime public, Union and returning Confederate publics",
        "occasion": "Second presidential inauguration near the end of the Civil War",
        "genre": "inaugural address",
        "rhetorical_action": "Reframes the war as providential judgment on slavery and redirects victory toward reconciliation.",
        "emotional_posture": "humility, judgment, reconciliation",
        "agency_structure": {
            "agents": ["God", "both parties", "we"],
            "patients": ["bondsman", "nation", "war dead"],
            "beneficiaries": ["reunited nation", "emancipation as moral horizon"],
            "passive_or_absent": ["Black political agency", "specific enslavers", "military perpetrators"],
            "displacement_mechanism": "Human agency is partially displaced into providential judgment and shared national guilt.",
        },
    },
    # ── American Revolution ───────────────────────────────────────────────────
    "am-rev-jefferson-declaration": {
        "audience": "Colonial publics, the Continental Congress, foreign powers, and posterity",
        "occasion": "Declaration of independence from British imperial rule, July 1776",
        "genre": "political declaration",
        "rhetorical_action": "Constitutes the American people as a rights-bearing sovereign by naturalizing separation from Britain.",
        "emotional_posture": "solemn assertion, justified grievance",
        "agency_structure": {
            "agents": ["the people", "we", "United States"],
            "patients": ["political bands", "tyrannical king"],
            "beneficiaries": ["free and independent states", "posterity"],
            "passive_or_absent": ["enslaved people", "Indigenous peoples", "women", "loyalists"],
            "displacement_mechanism": "The rights-bearing 'people' excludes enslaved, Indigenous, and propertyless populations whose absence is structurally required for the sovereign claim.",
        },
    },
    "am-rev-paine-common-sense": {
        "audience": "Broad colonial reading public, undecided colonists, and anti-independence moderates",
        "occasion": "Pre-independence popular pamphlet arguing for immediate separation from Britain, January 1776",
        "genre": "political pamphlet",
        "rhetorical_action": "Delegitimizes monarchy and hereditary rule while constructing the colonial cause as universal natural right.",
        "emotional_posture": "polemical, exhortative, prophetic",
        "agency_structure": {
            "agents": ["the people", "mankind", "Americans"],
            "patients": ["monarchy", "tyranny", "oppression"],
            "beneficiaries": ["free republic", "posterity", "the world"],
            "passive_or_absent": ["enslaved people", "Indigenous peoples", "Loyalists", "women"],
            "displacement_mechanism": "Universal appeals to nature and reason suppress differentiated social interests and racially bounded exclusions.",
        },
    },
    "am-rev-washington-orders-1775-07-04": {
        "audience": "Continental Army troops under Washington's command",
        "occasion": "General orders at Cambridge, July 1775, early stage of the war",
        "genre": "military general orders",
        "rhetorical_action": "Establishes command authority and imposes discipline on newly formed colonial forces.",
        "emotional_posture": "commanding, admonitory",
        "agency_structure": {
            "agents": ["commander", "officers"],
            "patients": ["soldiers", "the cause"],
            "beneficiaries": ["the army", "the country"],
            "passive_or_absent": ["enslaved soldiers", "civilian populations affected by military movements"],
            "displacement_mechanism": "Military necessity suppresses individual and social difference under command hierarchy.",
        },
    },
    "am-rev-washington-orders-1776-02-09": {
        "audience": "Continental Army troops",
        "occasion": "General orders during the winter encampment, February 1776",
        "genre": "military general orders",
        "rhetorical_action": "Maintains order and readiness during a period of military consolidation.",
        "emotional_posture": "firm, administrative",
        "agency_structure": {
            "agents": ["commander", "officers"],
            "patients": ["soldiers"],
            "beneficiaries": ["the army", "the cause"],
            "passive_or_absent": ["civilian populations", "enslaved laborers"],
            "displacement_mechanism": "Command register reduces social complexity to military hierarchy.",
        },
    },
    "am-rev-washington-orders-1776-07-02": {
        "audience": "Continental Army troops at the outset of the New York campaign",
        "occasion": "General orders on the day the Continental Congress voted for independence, July 2, 1776",
        "genre": "military general orders",
        "rhetorical_action": "Frames the independence vote as a call to arms and invokes providence as sanction for the cause.",
        "emotional_posture": "exhortative, solemn",
        "agency_structure": {
            "agents": ["the General", "the brave", "soldiers"],
            "patients": ["the enemy", "the cause"],
            "beneficiaries": ["the country", "posterity", "freedom"],
            "passive_or_absent": ["enslaved people", "civilian non-combatants", "Loyalist families"],
            "displacement_mechanism": "Military sacrifice is universalized as patriotic offering; excluded populations are invisible.",
        },
    },
    "am-rev-washington-orders-1776-08-30": {
        "audience": "Continental Army troops after the Battle of Long Island",
        "occasion": "General orders following the army's retreat from Long Island, August 1776",
        "genre": "military general orders",
        "rhetorical_action": "Sustains morale after a military setback and attributes failure to cowardice and poor discipline.",
        "emotional_posture": "stern, remedial",
        "agency_structure": {
            "agents": ["the General", "brave officers and men"],
            "patients": ["cowards", "the army"],
            "beneficiaries": ["the cause", "the country"],
            "passive_or_absent": ["wounded soldiers", "civilian refugee populations"],
            "displacement_mechanism": "Blame is placed on individual cowardice rather than strategic or structural failures.",
        },
    },
    "am-rev-washington-orders-1776-12-25": {
        "audience": "Continental Army troops on the eve of the Trenton crossing",
        "occasion": "General orders before the surprise attack on Trenton, December 25, 1776",
        "genre": "military general orders",
        "rhetorical_action": "Calls troops to decisive action at a moment of critical crisis with providential framing.",
        "emotional_posture": "urgent, resolute",
        "agency_structure": {
            "agents": ["the General", "the army"],
            "patients": ["the enemy", "the cause"],
            "beneficiaries": ["the country", "freedom"],
            "passive_or_absent": ["Hessian prisoners", "Loyalist and civilian populations", "enslaved people"],
            "displacement_mechanism": "Crisis framing narrows the moral field to combat obligation, suppressing non-combatant and excluded populations.",
        },
    },
    "am-rev-washington-orders-1783-06-08": {
        "audience": "Continental Army officers and soldiers near the end of the war",
        "occasion": "Farewell orders to the army as the Revolutionary War approached its end, June 1783",
        "genre": "military circular letter",
        "rhetorical_action": "Frames the war's conclusion as the founding of a new republican order and calls for civic virtue in peacetime.",
        "emotional_posture": "valedictory, civic, exhortative",
        "agency_structure": {
            "agents": ["the Commander", "citizens-soldiers", "we"],
            "patients": ["the republic", "the world"],
            "beneficiaries": ["posterity", "free citizens", "the nation"],
            "passive_or_absent": ["enslaved people whose status was unchanged", "Indigenous peoples", "women"],
            "displacement_mechanism": "The republican founding narrative erases the social conditions that made the war possible for some and impossible for others.",
        },
    },
    "am-rev-washington-orders-1783-06-17": {
        "audience": "Continental Army troops at demobilization",
        "occasion": "Final general orders dissolving the Continental Army, June 1783",
        "genre": "military general orders",
        "rhetorical_action": "Commends the army and transfers military virtue into civilian republican citizenship.",
        "emotional_posture": "gratitude, valedictory",
        "agency_structure": {
            "agents": ["the Commander", "the army"],
            "patients": ["the republic", "posterity"],
            "beneficiaries": ["free citizens", "the nation"],
            "passive_or_absent": ["enslaved people", "Indigenous peoples", "women"],
            "displacement_mechanism": "Military sacrifice is universalized as civic virtue; structurally excluded populations remain invisible.",
        },
    },
    # ── Napoleon ─────────────────────────────────────────────────────────────
    "napoleon-bulletin-1805-12-03-austerlitz": {
        "audience": "Grande Armée soldiers, French public, and European courts reading official bulletins",
        "occasion": "Battle of Austerlitz, December 2, 1805 — Napoleon's most celebrated victory",
        "genre": "imperial military bulletin",
        "rhetorical_action": "Glorifies the victory as providential destiny and constructs the Emperor as the embodied source of triumph.",
        "emotional_posture": "triumphant, celebratory, imperial",
        "agency_structure": {
            "agents": ["l'Empereur", "la Grande Armée", "soldats"],
            "patients": ["l'ennemi", "les armées coalisées"],
            "beneficiaries": ["la France", "l'Empire", "la gloire"],
            "passive_or_absent": ["enemy dead and wounded", "civilian populations", "non-French subject peoples"],
            "displacement_mechanism": "Enemy suffering is suppressed under glory and destiny; civilian impact is invisible.",
        },
    },
    "napoleon-bulletin-1805-12-04-austerlitz-aftermath": {
        "audience": "Grande Armée and French public",
        "occasion": "Day after Austerlitz — consolidation of victory and armistice negotiations",
        "genre": "imperial military bulletin",
        "rhetorical_action": "Cements the victory narrative and presents Napoleon as magnanimous conqueror.",
        "emotional_posture": "authoritative, magnanimous",
        "agency_structure": {
            "agents": ["l'Empereur", "la Grande Armée"],
            "patients": ["l'ennemi vaincu", "les empereurs vaincus"],
            "beneficiaries": ["la paix", "l'Empire"],
            "passive_or_absent": ["defeated soldiers", "civilian populations of occupied territories"],
            "displacement_mechanism": "Magnanimity narrative suppresses the violence and territorial costs of the victory.",
        },
    },
    "napoleon-bulletin-1806-10-15-jena": {
        "audience": "Grande Armée and French public",
        "occasion": "Battle of Jena, October 14, 1806 — decisive defeat of Prussian forces",
        "genre": "imperial military bulletin",
        "rhetorical_action": "Presents Prussian defeat as the inevitable consequence of their aggression and French military superiority.",
        "emotional_posture": "triumphant, contemptuous of the enemy",
        "agency_structure": {
            "agents": ["l'Empereur", "les soldats français"],
            "patients": ["l'armée prussienne", "la Prusse"],
            "beneficiaries": ["l'Empire", "la gloire française"],
            "passive_or_absent": ["Prussian civilian populations", "war dead", "wounded soldiers"],
            "displacement_mechanism": "Enemy defeat is framed as deserved; material suffering of soldiers and civilians is suppressed.",
        },
    },
    "napoleon-bulletin-1806-10-26-berlin": {
        "audience": "Grande Armée and French public",
        "occasion": "Entry into Berlin, October 1806 — symbolic occupation of the Prussian capital",
        "genre": "imperial military bulletin",
        "rhetorical_action": "Frames the capture of Berlin as the completion of historical destiny and Napoleonic mission.",
        "emotional_posture": "triumphant, imperial",
        "agency_structure": {
            "agents": ["l'Empereur", "la Grande Armée"],
            "patients": ["Berlin", "la Prusse vaincue"],
            "beneficiaries": ["l'Empire", "la France"],
            "passive_or_absent": ["Berlin civilian population", "Prussian non-combatants"],
            "displacement_mechanism": "Occupation is framed as historical destiny; civilian experience of occupation is absent.",
        },
    },
    "napoleon-bulletin-1807-02-08-eylau": {
        "audience": "Grande Armée and French public",
        "occasion": "Battle of Eylau, February 8, 1807 — one of Napoleon's bloodiest engagements",
        "genre": "imperial military bulletin",
        "rhetorical_action": "Transforms a costly and inconclusive battle into a narrative of French courage and sacrificial glory.",
        "emotional_posture": "somber courage, glorification of sacrifice",
        "agency_structure": {
            "agents": ["l'Empereur", "les braves soldats", "la Grande Armée"],
            "patients": ["les morts", "l'ennemi", "les blessés"],
            "beneficiaries": ["la gloire", "la France", "l'Empire"],
            "passive_or_absent": ["mass dead on both sides", "wounded left on the field", "civilian casualties"],
            "displacement_mechanism": "Mass death is converted into glory and sacrificial honor; the scale of suffering is suppressed.",
        },
    },
    "napoleon-bulletin-1807-06-14-friedland": {
        "audience": "Grande Armée and French public",
        "occasion": "Battle of Friedland, June 14, 1807 — decisive victory leading to Treaty of Tilsit",
        "genre": "imperial military bulletin",
        "rhetorical_action": "Presents the victory as the culmination of the campaign and Napoleon's personal genius.",
        "emotional_posture": "triumphant, conclusive",
        "agency_structure": {
            "agents": ["l'Empereur", "les soldats"],
            "patients": ["l'ennemi russe"],
            "beneficiaries": ["la paix", "l'Empire"],
            "passive_or_absent": ["Russian dead and wounded", "civilian populations of East Prussia"],
            "displacement_mechanism": "Enemy defeat suppresses the scale of killing; peace framing displaces material violence.",
        },
    },
    "napoleon-bulletin-1809-07-08-wagram": {
        "audience": "Grande Armée and French public",
        "occasion": "Battle of Wagram, July 1809 — major victory over Austria",
        "genre": "imperial military bulletin",
        "rhetorical_action": "Frames the victory as the decisive blow that compels Austrian submission.",
        "emotional_posture": "commanding, triumphant",
        "agency_structure": {
            "agents": ["l'Empereur", "la Grande Armée"],
            "patients": ["l'armée autrichienne", "l'Autriche"],
            "beneficiaries": ["la paix", "l'Empire"],
            "passive_or_absent": ["battle dead", "wounded soldiers", "civilian populations of the Danube valley"],
            "displacement_mechanism": "Military glory narrative suppresses the costs in lives and material destruction.",
        },
    },
    "napoleon-bulletin-1812-10-23-russia-advance": {
        "audience": "Grande Armée and French public",
        "occasion": "Russian campaign, October 1812 — on the eve of catastrophic retreat",
        "genre": "imperial military bulletin",
        "rhetorical_action": "Maintains a tone of command authority and mission as the campaign deteriorates.",
        "emotional_posture": "controlled, authoritative",
        "agency_structure": {
            "agents": ["l'Empereur", "la Grande Armée"],
            "patients": ["l'ennemi russe", "la campagne"],
            "beneficiaries": ["la France", "l'Empire"],
            "passive_or_absent": ["soldiers dying of cold and starvation", "Russian civilian populations"],
            "displacement_mechanism": "Command register suppresses the scale of human suffering in the retreat.",
        },
    },
    "napoleon-bulletin-1812-12-03-russia-29th": {
        "audience": "Grande Armée survivors and French public",
        "occasion": "The infamous 29th Bulletin, December 1812 — first public acknowledgment of the Russian disaster",
        "genre": "imperial military bulletin",
        "rhetorical_action": "Acknowledges catastrophic losses while attributing them to weather rather than strategic failure.",
        "emotional_posture": "controlled admission, deflection",
        "agency_structure": {
            "agents": ["l'Empereur", "le froid", "le destin"],
            "patients": ["la Grande Armée", "les chevaux", "les soldats"],
            "beneficiaries": ["l'Empire survivant", "la France"],
            "passive_or_absent": ["individual dead soldiers", "their families", "Russian civilian victims of the campaign"],
            "displacement_mechanism": "Agency is displaced onto weather and fate; strategic and command responsibility is suppressed.",
        },
    },
    "napoleon-bulletin-1813-05-24-bautzen": {
        "audience": "Grande Armée and French public",
        "occasion": "Battle of Bautzen, May 1813 — victory in the German campaign after Russian disaster",
        "genre": "imperial military bulletin",
        "rhetorical_action": "Frames the victory as a resumption of Napoleonic military glory after the Russian setback.",
        "emotional_posture": "restored confidence, triumphant",
        "agency_structure": {
            "agents": ["l'Empereur", "la Grande Armée"],
            "patients": ["l'ennemi prussien et russe"],
            "beneficiaries": ["l'Empire", "la gloire française"],
            "passive_or_absent": ["allied dead", "German civilian populations under occupation"],
            "displacement_mechanism": "Victory narrative suppresses the continuing costs of war on populations and on the army itself.",
        },
    },
    # ── Hitler ────────────────────────────────────────────────────────────────
    "hitler-mein-kampf-vol1-ch2-wien": {
        "audience": "German nationalist readers; retrospective autobiography framed as political education",
        "occasion": "Autobiographical chapter on Vienna, the city Hitler constructs as his political and racial awakening",
        "genre": "political autobiography / ideological treatise",
        "rhetorical_action": "Constructs Vienna as the site of racial contamination and ideological discovery, naturalizing antisemitism as self-evident observation.",
        "emotional_posture": "retrospective grievance, awakening, horror",
        "agency_structure": {
            "agents": ["I/Hitler", "the German people", "Aryan race"],
            "patients": ["the Jew", "the German Volk threatened by contamination"],
            "beneficiaries": ["the purified nation", "Aryan civilization"],
            "passive_or_absent": ["Jewish victims of the ideology being constructed", "non-German urban workers"],
            "displacement_mechanism": "Personal resentment is projected outward as objective racial observation; the Jewish population is constructed as agent of harm with no counter-voice.",
        },
    },
    "hitler-mein-kampf-vol1-ch11-race-and-people": {
        "audience": "German nationalist readers seeking ideological foundation",
        "occasion": "Core theoretical chapter on race, national character, and culture in Mein Kampf Vol. 1",
        "genre": "political autobiography / ideological treatise",
        "rhetorical_action": "Establishes racial hierarchy as natural law and designates the Aryan race as the sole creator of civilization.",
        "emotional_posture": "pseudo-scientific, authoritative, prophetic",
        "agency_structure": {
            "agents": ["Nature", "the Aryan race", "Hitler as interpreter of natural law"],
            "patients": ["inferior races", "cultural parasites", "the German Volk threatened by mixing"],
            "beneficiaries": ["Aryan civilization", "the thousand-year Reich"],
            "passive_or_absent": ["Jewish, Roma, Black, and other racialized populations constructed as threats", "women", "disabled people"],
            "displacement_mechanism": "Genocide logic is naturalized as law; its victims are constructed as aggressors requiring removal.",
        },
    },
    "hitler-mein-kampf-vol1-ch12-nsdap": {
        "audience": "German nationalist readers and potential NSDAP recruits",
        "occasion": "Chapter on the early NSDAP and the requirements of political organization",
        "genre": "political autobiography / ideological treatise",
        "rhetorical_action": "Frames the NSDAP as the necessary vehicle for racial salvation and positions Hitler as indispensable leader.",
        "emotional_posture": "prescriptive, visionary, organizational",
        "agency_structure": {
            "agents": ["the movement", "Hitler", "the Volk"],
            "patients": ["Jewish Marxism", "the corrupt state", "enemies of the nation"],
            "beneficiaries": ["the German nation", "Aryan civilization"],
            "passive_or_absent": ["political opponents who will be eliminated", "non-Aryan minorities"],
            "displacement_mechanism": "Organizational necessity suppresses the eliminationist consequences of the movement's program.",
        },
    },
    "hitler-mein-kampf-vol2-ch1-weltanschauung": {
        "audience": "NSDAP members and nationalist readers",
        "occasion": "Opening chapter of Vol. 2, on worldview and political doctrine",
        "genre": "political autobiography / ideological treatise",
        "rhetorical_action": "Establishes racial worldview as scientific truth and the basis for all political action.",
        "emotional_posture": "doctrinal, authoritative",
        "agency_structure": {
            "agents": ["the movement", "Nature", "the Aryan"],
            "patients": ["the Jewish worldview", "Marxism", "international capital"],
            "beneficiaries": ["the national community", "the German state"],
            "passive_or_absent": ["populations targeted by the racial doctrine"],
            "displacement_mechanism": "Ideological framing neutralizes the violence inherent in the program by presenting it as natural and inevitable.",
        },
    },
    "hitler-mein-kampf-vol2-ch2-the-state": {
        "audience": "NSDAP members and nationalist readers",
        "occasion": "Chapter on the racial state as the highest political form",
        "genre": "political autobiography / ideological treatise",
        "rhetorical_action": "Subordinates the state to racial preservation and delegitimizes non-racial political forms.",
        "emotional_posture": "prescriptive, systematic",
        "agency_structure": {
            "agents": ["the racial state", "the movement", "Nature"],
            "patients": ["the Jewish-Marxist state", "degenerate political forms"],
            "beneficiaries": ["the Volk", "Aryan posterity"],
            "passive_or_absent": ["ethnic and political minorities in the state being constructed"],
            "displacement_mechanism": "State theory presents elimination of minorities as maintenance of natural order.",
        },
    },
    "hitler-mein-kampf-vol2-ch14-eastern-europe": {
        "audience": "NSDAP members and nationalist readers",
        "occasion": "Chapter on eastern expansion (Lebensraum) and racial settlement policy",
        "genre": "political autobiography / ideological treatise",
        "rhetorical_action": "Legitimizes eastward territorial conquest as racial destiny and frames Slavic populations as obstacles to Aryan settlement.",
        "emotional_posture": "geopolitical, prophetic, eliminationist",
        "agency_structure": {
            "agents": ["the German nation", "the Aryan settler", "the movement"],
            "patients": ["Slavic populations", "Eastern European peoples designated for displacement"],
            "beneficiaries": ["the Aryan nation", "German Lebensraum"],
            "passive_or_absent": ["Slavic, Jewish, and other populations facing displacement and extermination"],
            "displacement_mechanism": "Territorial destiny naturalizes mass displacement and murder as spatial necessity.",
        },
    },
    "hitler-reichstag-1939-01-30": {
        "audience": "Reichstag deputies, German public, and European audience via radio broadcast",
        "occasion": "Sixth anniversary of the Nazi seizure of power — Hitler's infamous 'prophecy' speech",
        "genre": "parliamentary address / public speech",
        "rhetorical_action": "Issues an explicit threat of annihilation against European Jews if war is provoked, framed as prophetic warning.",
        "emotional_posture": "threatening, prophetic, self-victimizing",
        "agency_structure": {
            "agents": ["Hitler", "the German nation", "international Jewry constructed as aggressor"],
            "patients": ["the Jewish race in Europe"],
            "beneficiaries": ["the German nation", "European civilization"],
            "passive_or_absent": ["Jewish populations whose extermination is being announced", "potential victims of the coming war"],
            "displacement_mechanism": "The annihilation threat is framed as defensive prophecy; victims are constructed as aggressors who force the outcome.",
        },
    },
    "hitler-ussr-proclamation-1941-06-22": {
        "audience": "German public, soldiers, and allies",
        "occasion": "Hitler's proclamation announcing the invasion of the Soviet Union, June 22, 1941",
        "genre": "wartime proclamation",
        "rhetorical_action": "Frames Operation Barbarossa as a preemptive defensive war against Jewish Bolshevism threatening European civilization.",
        "emotional_posture": "martial, prophetic, self-righteous",
        "agency_structure": {
            "agents": ["the German people", "the Axis powers", "Nature"],
            "patients": ["Jewish Bolshevism", "the Soviet threat"],
            "beneficiaries": ["European civilization", "the German nation", "Aryan posterity"],
            "passive_or_absent": ["Soviet civilian populations", "Jewish populations targeted in the invasion", "POWs subject to systematic murder"],
            "displacement_mechanism": "Invasion is framed as defense; the genocide carried out under its cover is absent from the proclamation.",
        },
    },
}

CLUSTER_NOTES: dict[str, dict[str, Any]] = {
    # ── Lincoln ──────────────────────────────────────────────────────────────
    "lincoln-01-body-organism": {
        "persuasive_function": "Makes national survival feel like the preservation of a living body rather than an abstract institutional choice.",
        "moral_emotions_activated": ["fear of collective death", "duty", "reverence for survival"],
        "political_actions_authorized": ["civic discipline", "continued preservation of republican government"],
        "negative_cases": ["The current reviewed sample does not yet show a fully medicalized disease or purification logic."],
        "relation_to_koenigsbergian_analysis": "Supports the body-politic corollary more directly than the sacrificial law itself.",
    },
    "lincoln-02-covenant-oath": {
        "persuasive_function": "Frames the civic relationship as a binding oath, converting political affiliation into solemn obligation.",
        "moral_emotions_activated": ["duty", "shame at oath-breaking", "reverence for the civic bond"],
        "political_actions_authorized": ["loyalty to the republic", "fulfilling constitutional obligations", "enduring war costs to honor the founding compact"],
        "negative_cases": ["Covenant language in Lincoln is often implicit; direct invocations of oath are concentrated in the constitutional oath of office rather than the full corpus."],
        "relation_to_koenigsbergian_analysis": "Supports the obligatory-frame dimension: citizens are bound by covenant to preserve the sacred object regardless of personal cost.",
    },
    "lincoln-03-experiment-proposition": {
        "persuasive_function": "Makes the republic's survival feel like an empirical test of democratic self-governance before the world.",
        "moral_emotions_activated": ["national pride", "anxiety about failure", "determination to prove the experiment"],
        "political_actions_authorized": ["completing the war to validate the republican proposition", "preserving government of the people"],
        "negative_cases": ["The experiment frame appears most clearly at Gettysburg; it is less developed in the Second Inaugural, which shifts to providential framing."],
        "relation_to_koenigsbergian_analysis": "Raises the stakes of sacrifice by making soldier death proof that the democratic proposition is viable rather than merely honorable.",
    },
    "lincoln-04-birth-creation": {
        "persuasive_function": "Turns war loss into the possibility of renewed political life.",
        "moral_emotions_activated": ["hope", "obligation", "reverent futurity"],
        "political_actions_authorized": ["continuing the war effort", "renewing democratic commitment"],
        "negative_cases": ["Current evidence is concentrated in the Gettysburg climax and should not be treated as distributed across the full Lincoln corpus yet."],
        "relation_to_koenigsbergian_analysis": "Complicates preservation by adding rebirth: sacrifice does not merely keep the sacred object alive, it makes renewal imaginable.",
    },
    "lincoln-05-fathers-inheritance": {
        "persuasive_function": "Constructs political obligation as inherited from founding fathers, making the republic a bequest that the current generation must not squander.",
        "moral_emotions_activated": ["filial duty", "gratitude for inheritance", "shame at betraying founders"],
        "political_actions_authorized": ["preservation of the founding order", "sacrifice to honor inherited obligation", "constitutional fidelity"],
        "negative_cases": ["The fathers/inheritance frame in Lincoln typically constructs an all-male genealogy that excludes women and the enslaved from founding agency."],
        "relation_to_koenigsbergian_analysis": "Supports the sacred-object and obligatory-frame dimensions: the republic is a patrimony whose preservation obligates the heirs.",
    },
    "lincoln-06-providence-theodicy": {
        "persuasive_function": "Places slavery, bloodshed, guilt, and reconciliation under divine judgment rather than partisan triumph.",
        "moral_emotions_activated": ["guilt", "humility", "reverence", "forbearance"],
        "political_actions_authorized": ["accepting war suffering as moral judgment", "reconciliation without denying slavery's offense"],
        "negative_cases": ["Providence language can be doctrinal quotation or rhetorical convention; it should not be used as evidence of private belief without corroboration."],
        "relation_to_koenigsbergian_analysis": "Supports historical-sacral framing and guilt distribution, while limiting enemy-destruction claims through reconciliation.",
    },
    "lincoln-07-absence-black-agency": {
        "persuasive_function": "Marks a structural gap: the metaphorical systems reviewed raise the question of where Black political and military agency is represented or suppressed.",
        "moral_emotions_activated": ["critical attention to what is missing", "awareness of whose sacrifice is named versus whose is erased"],
        "political_actions_authorized": ["recognition of Black political agency as analytically required by the evidence"],
        "negative_cases": ["This cluster is currently under-evidenced in the MIPVU review; it marks a review question rather than a confirmed finding."],
        "relation_to_koenigsbergian_analysis": "Supports the absence-and-agency dimension: the Koenigsbergian framework requires attention to whose agency is suppressed by the dominant metaphor systems.",
    },
    "lincoln-08-sacrificial-death-gift": {
        "persuasive_function": "Converts soldier death into an offering that obligates the living.",
        "moral_emotions_activated": ["mourning", "gratitude", "debt", "devotion"],
        "political_actions_authorized": ["continued dedication", "completion of unfinished work", "preservation of national life"],
        "negative_cases": ["The current evidence sacralizes Union death but does not make killing an end in itself."],
        "relation_to_koenigsbergian_analysis": "Directly supports the sacrificial-body dimension, especially in Gettysburg's battlefield setting.",
    },
    # ── American Revolution ───────────────────────────────────────────────────
    "am-rev-01-liberty-tyranny": {
        "persuasive_function": "Frames the political choice as an absolute moral binary between freedom and bondage, foreclosing accommodation.",
        "moral_emotions_activated": ["outrage", "fear of enslavement", "hatred of tyranny"],
        "political_actions_authorized": ["revolution", "separation from Britain", "armed resistance"],
        "negative_cases": ["The liberty/tyranny binary suppresses moderate constitutional arguments; not all colonial writers used this frame with equal intensity."],
        "relation_to_koenigsbergian_analysis": "Sets up the enemy-as-bringer-of-death dimension: the tyrannical enemy threatens the sacred object (liberty) and must be resisted or expelled.",
    },
    "am-rev-02-people-republic": {
        "persuasive_function": "Constitutes a sovereign people and a republic as natural political entities that precede and authorize the revolutionary act.",
        "moral_emotions_activated": ["civic pride", "republican virtue", "collective obligation"],
        "political_actions_authorized": ["self-government", "constitution-making", "resistance to tyranny"],
        "negative_cases": ["'The people' in this corpus is structurally exclusive; the claim to universal sovereignty coexists with enslaved, Indigenous, and propertyless exclusion."],
        "relation_to_koenigsbergian_analysis": "The people as sacred political object is the object that sacrifice preserves; it requires the enemy-as-threat framing to motivate action.",
    },
    "am-rev-03-founding-sacrifice": {
        "persuasive_function": "Transforms the costs of revolution into sacred offerings that obligate posterity and legitimate the founding.",
        "moral_emotions_activated": ["debt", "obligation", "reverence for sacrifice", "shame at ingratitude"],
        "political_actions_authorized": ["continued commitment to the republic", "civic honor for veterans", "preservation of the founding order"],
        "negative_cases": ["Founding sacrifice language is concentrated in Washington's valedictory orders; the Declaration and Common Sense use it less directly."],
        "relation_to_koenigsbergian_analysis": "Directly activates the sacrificial-body dimension: the revolutionary dead create the sacred debt that sustains the republic.",
    },
    "am-rev-04-providence-covenant": {
        "persuasive_function": "Sacralizes the revolutionary cause by placing it under divine sanction and framing it as a covenant with providential history.",
        "moral_emotions_activated": ["awe", "duty", "gratitude for divine favor", "fear of moral failure"],
        "political_actions_authorized": ["trust in providential outcome", "moral seriousness in combat", "gratitude as civic obligation"],
        "negative_cases": ["Providence language in Washington's orders is formulaic and military; it should not be treated as evidence of deep theological conviction without further corroboration."],
        "relation_to_koenigsbergian_analysis": "Supports the historical-sacral framing; the cause is not merely political but divinely backed, heightening the stakes of sacrifice.",
    },
    "am-rev-05-virtue-corruption": {
        "persuasive_function": "Frames the revolution as a moral regeneration against the corruption that monarchy and luxury produce.",
        "moral_emotions_activated": ["disgust at corruption", "admiration for virtue", "civic shame"],
        "political_actions_authorized": ["republican simplicity", "rejection of aristocratic excess", "civic vigilance"],
        "negative_cases": ["Virtue/corruption discourse is most prominent in Common Sense and less developed in the military orders or Declaration."],
        "relation_to_koenigsbergian_analysis": "Supports the enemy-as-contamination framing; corruption is a moral and civic disease spread by the monarchical enemy.",
    },
    "am-rev-06-union-founding-memory": {
        "persuasive_function": "Creates an obligation to preserve the founding order by framing it as a sacred legacy held in trust for posterity.",
        "moral_emotions_activated": ["custodial duty", "pride in achievement", "fear of betraying the founders"],
        "political_actions_authorized": ["preservation of the union", "civic memory", "resistance to dissolution"],
        "negative_cases": ["Union/founding-memory framing is concentrated in Washington's 1783 orders; it is prospective and valedictory, not a description of the war's motivations."],
        "relation_to_koenigsbergian_analysis": "Sustains the sacred-object dimension over time; the union becomes the object that must be preserved across generations.",
    },
    # ── Napoleon ─────────────────────────────────────────────────────────────
    "napoleon-01-glory-destiny": {
        "persuasive_function": "Makes military victory feel like historical destiny, converting contingent battle outcomes into inevitable providential unfolding.",
        "moral_emotions_activated": ["awe", "pride", "reverence for greatness", "excitement at historical participation"],
        "political_actions_authorized": ["continued military campaign", "obedience to Napoleon as destiny's instrument", "acceptance of sacrifice"],
        "negative_cases": ["Glory/destiny framing is most intense in the early victories (Austerlitz, Jena); after Eylau and especially after 1812 it becomes strained."],
        "relation_to_koenigsbergian_analysis": "Naturalizes the Emperor as the sacred object's embodiment; destiny suppresses the contingency and human agency behind the wars.",
    },
    "napoleon-02-army-body": {
        "persuasive_function": "Constructs the Grande Armée as a collective organism whose health and discipline embody the Empire's vitality.",
        "moral_emotions_activated": ["solidarity", "martial pride", "duty to the collective body"],
        "political_actions_authorized": ["military discipline", "collective sacrifice", "continued campaigns"],
        "negative_cases": ["Army-as-body language is more prominent in bulletins with high casualty counts (Eylau); it functions to absorb individual loss into collective identity."],
        "relation_to_koenigsbergian_analysis": "Supports the sacrificial-body dimension: the army's suffering is the body whose sacrifice sustains the imperial order.",
    },
    "napoleon-03-emperor-embodiment": {
        "persuasive_function": "Consolidates authority by making Napoleon the personal embodiment of France, history, and destiny.",
        "moral_emotions_activated": ["devotion", "awe", "identification with Napoleon as historical agent"],
        "political_actions_authorized": ["personal loyalty", "obedience to imperial command", "sacrifice on behalf of the Emperor"],
        "negative_cases": ["Emperor-embodiment is an imperial construction; the bulletins do not record dissent, desertion, or the limits of the soldiers' actual devotion."],
        "relation_to_koenigsbergian_analysis": "The Emperor is the sacred object and its guardian simultaneously; sacrifice for Napoleon is sacrifice for the nation made flesh.",
    },
    "napoleon-04-empire-order": {
        "persuasive_function": "Legitimizes conquest by framing French expansion as the restoration of order, law, and civilization against chaos.",
        "moral_emotions_activated": ["satisfaction at order", "contempt for enemies of civilization"],
        "political_actions_authorized": ["occupation of conquered territories", "imposition of French legal and administrative order"],
        "negative_cases": ["Order/civilization language masks the coercive and extractive nature of imperial occupation in Germany, Poland, and Spain."],
        "relation_to_koenigsbergian_analysis": "Positions the enemy as the bringer of disorder (death of civilization), legitimizing elimination of resistance.",
    },
    "napoleon-05-soldier-sacrifice": {
        "persuasive_function": "Converts soldier death into honor, glory, and immortality, making mass casualties rhetorically sustainable.",
        "moral_emotions_activated": ["mourning tempered by pride", "honor", "debt to the fallen"],
        "political_actions_authorized": ["continued military service", "acceptance of death as glorious", "solidarity with fallen comrades"],
        "negative_cases": ["The Eylau bulletin is the clearest case; after the Russian disaster the same framing strains credibility and disappears from the 29th Bulletin."],
        "relation_to_koenigsbergian_analysis": "Directly activates the sacrificial-body dimension: soldier death as meaningful offering sustaining the imperial sacred object.",
    },
    "napoleon-06-enemy-obstacle": {
        "persuasive_function": "Dehumanizes opposing armies as obstacles to historical destiny rather than as legitimate combatants.",
        "moral_emotions_activated": ["contempt", "confidence in French superiority", "righteous aggression"],
        "political_actions_authorized": ["offensive military action", "total defeat of the enemy", "pursuit and annihilation"],
        "negative_cases": ["Enemy-as-obstacle framing is calibrated to context; after 1812 the enemy is no longer so easily dismissed."],
        "relation_to_koenigsbergian_analysis": "Supports the enemy-as-bringer-of-death dimension: the enemy threatens the imperial order and must be removed for France to survive.",
    },
    # ── Hitler ────────────────────────────────────────────────────────────────
    "hitler-01-volk-racial-body": {
        "persuasive_function": "Constructs the German people as a racial organism whose purity must be preserved against contamination and dissolution.",
        "moral_emotions_activated": ["racial pride", "fear of contamination", "obligation to the Volk"],
        "political_actions_authorized": ["racial legislation", "exclusion of racial minorities", "reproductive policy"],
        "negative_cases": ["Volk/racial-body language naturalizes what are political constructions; the biological framing should not be accepted as description."],
        "relation_to_koenigsbergian_analysis": "The Volk is the sacred object; its preservation against contamination is the law that legitimizes sacrifice and elimination.",
    },
    "hitler-02-fuhrer-embodiment": {
        "persuasive_function": "Makes Hitler the personal embodiment of the Volk's destiny, concentrating all agency and authority in his person.",
        "moral_emotions_activated": ["devotion", "surrender of individual will", "awe at historical greatness"],
        "political_actions_authorized": ["absolute obedience", "personal sacrifice for Hitler/the movement", "suppression of dissent"],
        "negative_cases": ["Führer-embodiment is an ideological construction; the corpus does not record resistance, dissent, or the coercive apparatus sustaining it."],
        "relation_to_koenigsbergian_analysis": "The Führer is both the sacred object's guardian and its expression; sacrifice for him is sacrifice for the Volk.",
    },
    "hitler-03-jew-parasite-disease": {
        "persuasive_function": "Dehumanizes Jewish people as a pathological threat requiring removal, making genocide imaginable as hygiene.",
        "moral_emotions_activated": ["disgust", "fear of contamination", "righteous hatred"],
        "political_actions_authorized": ["exclusion", "persecution", "ultimately extermination"],
        "negative_cases": ["This cluster is not an analytic category but a record of genocidal ideology; its 'function' is the construction of the conditions for mass murder."],
        "relation_to_koenigsbergian_analysis": "Activates the enemy-as-bringer-of-death dimension at its most extreme: the enemy is not a rival people but a pathogen requiring elimination.",
    },
    "hitler-04-purification-surgery": {
        "persuasive_function": "Frames the elimination of designated groups as a medical necessity — a surgical procedure that restores the racial body to health.",
        "moral_emotions_activated": ["clinical detachment", "sense of necessity", "relief at 'treatment'"],
        "political_actions_authorized": ["deportation", "forced sterilization", "extermination camps"],
        "negative_cases": ["Purification/surgery language is not widely evidenced in the current MIPVU sample; it requires broader corpus coverage before aggregate claims."],
        "relation_to_koenigsbergian_analysis": "This is the eliminationist logic at the core of the Koenigsbergian sacrifice law in this case: the sacred body is preserved by surgical removal of contamination.",
    },
    "hitler-05-struggle-destiny": {
        "persuasive_function": "Frames all politics as existential struggle between races, naturalizing conflict and making accommodation impossible.",
        "moral_emotions_activated": ["martial resolve", "fatalistic duty", "pride in struggle"],
        "political_actions_authorized": ["war", "conquest", "racial struggle as permanent condition"],
        "negative_cases": ["Struggle/destiny framing is consistent across Mein Kampf but is less prominent in the 1939 and 1941 public speeches in this sample."],
        "relation_to_koenigsbergian_analysis": "Struggle is the mechanism through which the sacred Volk proves and preserves itself; sacrifice in struggle is both obligation and validation.",
    },
    "hitler-06-sacrifice-martyrdom": {
        "persuasive_function": "Converts political violence and death in the Nazi cause into sacred martyrdom, creating a cult of sacrificial obligation.",
        "moral_emotions_activated": ["honor", "debt to the fallen", "obligation to complete their sacrifice"],
        "political_actions_authorized": ["continued violence in the movement's name", "sacrifice of self and others", "elimination of enemies who caused the martyrs' deaths"],
        "negative_cases": ["Martyrdom framing in this corpus is most developed in the Mein Kampf chapters; the public proclamations are more functional and less hagiographic."],
        "relation_to_koenigsbergian_analysis": "Directly activates the sacrificial-body dimension: movement dead become the sacred debt that authorizes further violence.",
    },
    "hitler-07-rebirth-reich": {
        "persuasive_function": "Frames the Nazi project as national resurrection, making the movement's violence appear redemptive rather than destructive.",
        "moral_emotions_activated": ["hope for renewal", "pride in national regeneration", "sense of historic mission"],
        "political_actions_authorized": ["radical political transformation", "elimination of obstacles to national rebirth"],
        "negative_cases": ["Rebirth/Reich framing is not prominently evidenced in the current MIPVU sample and requires additional corpus coverage."],
        "relation_to_koenigsbergian_analysis": "Rebirth logic transforms sacrifice from loss into investment: the Volk dies to be reborn as something purer and stronger.",
    },
    "hitler-08-victim-erasure": {
        "persuasive_function": "Inverts victim and perpetrator roles, making the Nazis and Germans appear as the aggrieved party requiring defensive action.",
        "moral_emotions_activated": ["self-pity", "righteous indignation", "siege mentality"],
        "political_actions_authorized": ["preemptive aggression framed as defense", "persecution framed as self-protection"],
        "negative_cases": ["Victim-erasure is a structural feature of the corpus rather than a single cluster; it underlies most of the other clusters rather than standing alone."],
        "relation_to_koenigsbergian_analysis": "Victim-erasure is the rhetorical prerequisite for all the other Koenigsbergian dimensions: it constructs the enemy as aggressor before any sacrificial logic can operate.",
    },
}

ABSENCE_ROWS_BY_CASE: dict[str, list[dict[str, Any]]] = {
    "lincoln": [
        {
            "absence_id": "lincoln-absence-001",
            "cluster_id": "lincoln-08-sacrificial-death-gift",
            "metaphor_system": "Soldier death as sacrifice / gift",
            "expected_presence": "Actual dead and wounded bodies, families, and material violence implied by battlefield sacrifice.",
            "possible_absence": "Physical suffering and bodily destruction are compressed into solemn offering and devotion.",
            "agents": ["honored dead", "living citizens"],
            "patients": ["dead soldiers", "bereaved families"],
            "beneficiaries": ["nation", "democratic government", "freedom"],
            "sacrificial_subjects": ["Union soldiers"],
            "excluded_agents": ["Confederate soldiers as subjects", "civilian casualties"],
            "displacement_mechanism": "Bodily loss is displaced into national obligation and cemetery consecration.",
            "evidence_mapping_ids": ["lincoln-cmt-012", "lincoln-cmt-013"],
            "claim_boundary": "Systematic absence candidate; requires fuller corpus review before becoming a case-level finding.",
        },
        {
            "absence_id": "lincoln-absence-002",
            "cluster_id": "lincoln-06-providence-theodicy",
            "metaphor_system": "Providential judgment and moral accounting",
            "expected_presence": "Named enslaved people, enslavers, policy mechanisms, military actors, and Black political agency.",
            "possible_absence": "Agency is partly shifted from human institutions into divine judgment and shared national guilt.",
            "agents": ["God", "both parties", "nation"],
            "patients": ["bondsman", "war dead"],
            "beneficiaries": ["reconciled nation", "freedom as moral horizon"],
            "sacrificial_subjects": ["enslaved people", "soldiers"],
            "excluded_agents": ["Black soldiers and activists", "specific enslavers", "military perpetrators"],
            "displacement_mechanism": "Providential grammar can widen guilt but also blur differentiated human agency.",
            "evidence_mapping_ids": ["lincoln-cmt-055", "lincoln-cmt-061"],
            "claim_boundary": "Interpretive caution, not a claim that Lincoln intentionally suppressed agency.",
        },
        {
            "absence_id": "lincoln-absence-003",
            "cluster_id": "lincoln-01-body-organism",
            "metaphor_system": "Nation or government as living organism",
            "expected_presence": "Specific political antagonists, social conflicts, and institutional choices that threaten national life.",
            "possible_absence": "The body-politic frame can make political conflict appear as life/death pressure on the collective body.",
            "agents": ["we", "citizens"],
            "patients": ["nation", "government of the people"],
            "beneficiaries": ["republic", "democratic government"],
            "sacrificial_subjects": ["citizens asked to preserve the polity"],
            "excluded_agents": ["named opponents", "excluded populations outside the citizen 'we'"],
            "displacement_mechanism": "Conflict is condensed into organism survival rather than social plurality.",
            "evidence_mapping_ids": ["lincoln-cmt-003", "lincoln-cmt-004"],
            "claim_boundary": "Useful for rhetorical analysis; not by itself evidence of coercive policy.",
        },
    ],
    "am-rev": [
        {
            "absence_id": "am-rev-absence-001",
            "cluster_id": "am-rev-01-liberty-tyranny",
            "metaphor_system": "Liberty versus tyranny / slavery",
            "expected_presence": "Enslaved people for whom the rhetoric of freedom and bondage was literally applicable.",
            "possible_absence": "The liberty/slavery binary is applied to colonial political status while actual chattel slavery is not addressed.",
            "agents": ["the people", "colonists", "Americans"],
            "patients": ["tyranny", "oppression"],
            "beneficiaries": ["free citizens", "the republic"],
            "sacrificial_subjects": ["colonists resisting tyranny"],
            "excluded_agents": ["enslaved people", "Indigenous peoples", "women"],
            "displacement_mechanism": "Political slavery is foregrounded as metaphor while chattel slavery is structurally absent from the rights claim.",
            "evidence_mapping_ids": ["amrev-cmt-001", "amrev-cmt-005", "amrev-cmt-010"],
            "claim_boundary": "A structural absence in the founding documents; not a peripheral oversight.",
        },
        {
            "absence_id": "am-rev-absence-002",
            "cluster_id": "am-rev-03-founding-sacrifice",
            "metaphor_system": "Founding sacrifice / blood of liberty",
            "expected_presence": "Non-white and non-propertied soldiers, women, and camp followers whose contributions to the war are absent from the founding narrative.",
            "possible_absence": "Sacrifice is attributed to 'the people' and 'brave soldiers' in ways that exclude those who fought but are not included in the republic's beneficiaries.",
            "agents": ["the army", "brave soldiers", "we"],
            "patients": ["the cause", "liberty"],
            "beneficiaries": ["the republic", "posterity", "free citizens"],
            "sacrificial_subjects": ["Continental Army soldiers — implicitly white and male"],
            "excluded_agents": ["Black soldiers (free and enslaved)", "Indigenous allies and opponents", "women in the war effort"],
            "displacement_mechanism": "Universal founding-sacrifice language naturalizes an exclusive beneficiary class.",
            "evidence_mapping_ids": ["amrev-cmt-059", "amrev-cmt-061"],
            "claim_boundary": "Review question for fuller historical corroboration.",
        },
        {
            "absence_id": "am-rev-absence-003",
            "cluster_id": "am-rev-02-people-republic",
            "metaphor_system": "The people / republic as sacred political object",
            "expected_presence": "Named social constituencies — enslaved people, women, propertyless men, Indigenous peoples — who are excluded from the sovereign 'people'.",
            "possible_absence": "The 'people' is invoked as universal but constituted as particular; the gap between the claim and its referent is structurally suppressed.",
            "agents": ["the people", "we", "free citizens"],
            "patients": ["tyranny", "government without consent"],
            "beneficiaries": ["the republic", "posterity"],
            "sacrificial_subjects": ["those who sacrifice to preserve republican government"],
            "excluded_agents": ["enslaved people", "Indigenous peoples", "non-propertied men", "women"],
            "displacement_mechanism": "Universal-people rhetoric suppresses the particularity of its exclusions.",
            "evidence_mapping_ids": ["amrev-cmt-002", "amrev-cmt-003"],
            "claim_boundary": "Structural absence at the founding; well-documented in historical scholarship.",
        },
    ],
    "napoleon": [
        {
            "absence_id": "napoleon-absence-001",
            "cluster_id": "napoleon-05-soldier-sacrifice",
            "metaphor_system": "Soldier sacrifice / honor / immortality",
            "expected_presence": "The scale of death and suffering at Eylau and other engagements; the bodies of the dead and wounded.",
            "possible_absence": "Mass casualties are converted into glory and honor; the material reality of industrial-scale violence is suppressed.",
            "agents": ["l'Empereur", "les braves", "la Grande Armée"],
            "patients": ["les morts", "les blessés"],
            "beneficiaries": ["la gloire", "la France", "l'Empire"],
            "sacrificial_subjects": ["French soldiers killed and wounded in battle"],
            "excluded_agents": ["enemy dead and wounded as subjects", "families of the fallen", "civilians in war zones"],
            "displacement_mechanism": "Glory and destiny convert individual deaths into abstract historical capital.",
            "evidence_mapping_ids": ["napoleon-cmt-004", "napoleon-cmt-011"],
            "claim_boundary": "Most clearly evidenced at Eylau; requires corroboration from non-bulletin sources.",
        },
        {
            "absence_id": "napoleon-absence-002",
            "cluster_id": "napoleon-06-enemy-obstacle",
            "metaphor_system": "Enemy as obstacle to order / destiny",
            "expected_presence": "Enemy populations as subjects — Prussian, Russian, Austrian civilians and soldiers — with their own perspectives and suffering.",
            "possible_absence": "Enemy is constructed as an obstacle to French destiny rather than as a people with their own historical agency.",
            "agents": ["l'ennemi", "les coalisés"],
            "patients": ["l'ordre impérial", "la paix"],
            "beneficiaries": ["la France", "la civilisation"],
            "sacrificial_subjects": ["populations of occupied territories"],
            "excluded_agents": ["enemy civilian populations", "resistance fighters", "populations under French occupation"],
            "displacement_mechanism": "Obstacle framing suppresses enemy agency and civilian experience of conquest.",
            "evidence_mapping_ids": ["napoleon-cmt-019"],
            "claim_boundary": "A structural feature of the bulletin genre; requires non-French sources for the other side.",
        },
        {
            "absence_id": "napoleon-absence-003",
            "cluster_id": "napoleon-03-emperor-embodiment",
            "metaphor_system": "Emperor as embodiment of France / history",
            "expected_presence": "The coercive conditions under which soldiers served; desertion, dissent, and the limits of Napoleonic devotion.",
            "possible_absence": "The bulletins record only devotion and glory; dissent, coercion, and the social costs of perpetual war are absent.",
            "agents": ["l'Empereur", "la Grande Armée"],
            "patients": ["la France", "l'Empire"],
            "beneficiaries": ["la gloire", "l'histoire"],
            "sacrificial_subjects": ["soldiers who died for the imperial cause"],
            "excluded_agents": ["deserters", "conscripts under coercion", "subject peoples of the Empire"],
            "displacement_mechanism": "Embodiment rhetoric naturalizes coercive military service as voluntary devotion.",
            "evidence_mapping_ids": ["napoleon-cmt-002"],
            "claim_boundary": "Requires corroboration from non-official sources (memoirs, administrative records).",
        },
    ],
    "hitler": [
        {
            "absence_id": "hitler-absence-001",
            "cluster_id": "hitler-03-jew-parasite-disease",
            "metaphor_system": "Jew / enemy as parasite / disease / poison",
            "expected_presence": "Jewish people as subjects — their actual lives, agency, communities, and perspectives — not as objects of ideology.",
            "possible_absence": "The dehumanization logic renders Jewish people as categorical threat rather than as persons with agency; their perspective is structurally absent.",
            "agents": ["der Jude", "internationales Judentum"],
            "patients": ["das Volk", "die Kultur", "der arische Träger der Zivilisation"],
            "beneficiaries": ["das gereinigte Reich", "die arische Zivilisation"],
            "sacrificial_subjects": ["Jewish people targeted for elimination"],
            "excluded_agents": ["Jewish political, cultural, and social actors", "targets of Nazi persecution with no counter-voice in this corpus"],
            "displacement_mechanism": "Pathogen framing suppresses Jewish subjectivity entirely; the ideology constructs its own victims as its agents.",
            "evidence_mapping_ids": ["hitler-cmt-016", "hitler-cmt-017"],
            "claim_boundary": "Not an absence in the usual sense — an active erasure that is the ideological goal of the texts under analysis.",
        },
        {
            "absence_id": "hitler-absence-002",
            "cluster_id": "hitler-06-sacrifice-martyrdom",
            "metaphor_system": "Sacrifice / martyrdom / blood witness",
            "expected_presence": "The victims of Nazi violence — Jewish people, political opponents, disabled people — whose deaths are suppressed under the movement's own martyrology.",
            "possible_absence": "Nazi sacrifice rhetoric foregrounds the movement's own dead while the much larger number of victims of Nazi violence are absent from the frame.",
            "agents": ["die Bewegung", "die Märtyrer des Kampfes"],
            "patients": ["die Feinde des Volkes"],
            "beneficiaries": ["das Reich", "das Volk"],
            "sacrificial_subjects": ["Nazi movement dead — Beer Hall Putsch, Horst Wessel, etc."],
            "excluded_agents": ["victims of Nazi political violence", "populations killed by the state the movement created"],
            "displacement_mechanism": "Martyrology concentrates sacrificial meaning on perpetrators while suppressing the deaths it caused.",
            "evidence_mapping_ids": ["hitler-cmt-007", "hitler-cmt-032"],
            "claim_boundary": "Requires historical corroboration for the full scope of victim suppression.",
        },
        {
            "absence_id": "hitler-absence-003",
            "cluster_id": "hitler-01-volk-racial-body",
            "metaphor_system": "Volk / racial body",
            "expected_presence": "The social and political heterogeneity of the German population; dissent, class conflict, religious diversity, and non-Aryan communities.",
            "possible_absence": "The racial-body metaphor constructs the Volk as homogeneous, suppressing internal difference and naturalizing exclusion as hygiene.",
            "agents": ["das Volk", "die Rasse", "der Arier"],
            "patients": ["Verunreinigung", "Entartung", "Zersetzung"],
            "beneficiaries": ["das reine Volk", "die arische Zivilisation"],
            "sacrificial_subjects": ["excluded and eliminated groups whose removal is framed as maintenance of the body"],
            "excluded_agents": ["Jewish, Roma, disabled, homosexual, and other excluded populations", "political opponents within the Volk"],
            "displacement_mechanism": "Racial-body rhetoric naturalizes exclusion and murder as organic necessity.",
            "evidence_mapping_ids": ["hitler-cmt-001", "hitler-cmt-002"],
            "claim_boundary": "The logic of racial-body rhetoric directly authorized genocide; this is not a hypothesis but a historical fact.",
        },
    ],
}


def load_mappings(case_id: str) -> list[dict[str, Any]]:
    data = read_json(cmt_mappings_path_for(case_id), {}) or {}
    return list(iter_cmt_mappings(data))


def doc_lookup(case_id: str) -> dict[str, dict[str, Any]]:
    return {document_id(doc): doc for doc in documents(case_id)}


def grouped_by_cluster(mappings: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for mapping in mappings:
        cluster_id = str(mapping.get("cluster_id") or "")
        if cluster_id:
            grouped.setdefault(cluster_id, []).append(mapping)
    return grouped


def unique_values(items: list[dict[str, Any]], key: str) -> list[str]:
    values: set[str] = set()
    for item in items:
        value = item.get(key)
        if isinstance(value, list):
            values.update(str(entry) for entry in value if entry not in (None, ""))
        elif value not in (None, ""):
            values.add(str(value))
    return sorted(values)


def build_critical(case_id: str, generated_at: str, mappings: list[dict[str, Any]]) -> dict[str, Any]:
    clusters = grouped_by_cluster(mappings)
    profiles = []
    for cluster_id, items in sorted(clusters.items()):
        notes = CLUSTER_NOTES.get(cluster_id, {})
        profiles.append(
            {
                "cluster_id": cluster_id,
                "mapping_ids": unique_values(items, "mapping_id"),
                "source_domains": sorted(
                    set(unique_values(items, "source_domain_primary"))
                    | set(unique_values(items, "source_domain_secondary"))
                ),
                "target_domains": unique_values(items, "target_domain"),
                "major_expressions": unique_values(items, "expression"),
                "corpus_distribution": {
                    "mapping_count": len(items),
                    "documents": unique_values(items, "document_id"),
                    "periods": unique_values(items, "diachronic_stage"),
                    "rhetorical_salience": unique_values(items, "rhetorical_salience"),
                },
                "rhetorical_contexts": unique_values(items, "rhetorical_functions"),
                "persuasive_function": notes.get("persuasive_function", "Pending fuller interpretive review."),
                "moral_emotions_activated": notes.get("moral_emotions_activated", []),
                "political_actions_authorized": notes.get("political_actions_authorized", []),
                "rival_readings": unique_values(items, "rival_reading"),
                "negative_cases": notes.get("negative_cases", []),
                "relation_to_koenigsbergian_analysis": notes.get(
                    "relation_to_koenigsbergian_analysis", "Pending support synthesis."
                ),
                "evidence_status": "provisional-cmt-backed",
            }
        )
    return {
        "version": "1.0",
        "case_id": case_id,
        "generated_at": generated_at,
        "status": "draft" if profiles else "stub",
        "source": str(cmt_mappings_path_for(case_id).relative_to(case_dir(case_id))),
        "cluster_profiles": profiles,
    }


def build_rhetorical(case_id: str, generated_at: str, mappings: list[dict[str, Any]]) -> dict[str, Any]:
    docs = doc_lookup(case_id)
    contexts = []
    for mapping in mappings:
        doc_id = str(mapping.get("document_id") or "")
        doc = docs.get(doc_id, {})
        context = DOCUMENT_CONTEXT.get(doc_id, {})
        contexts.append(
            {
                "mapping_id": mapping.get("mapping_id"),
                "document_id": doc_id,
                "sentence_id": mapping.get("sentence_id"),
                "date": doc.get("date"),
                "period": doc.get("period"),
                "audience": context.get("audience"),
                "occasion": context.get("occasion"),
                "genre": context.get("genre") or doc.get("genre") or doc.get("register"),
                "rhetorical_action": context.get("rhetorical_action"),
                "emotional_posture": context.get("emotional_posture"),
                "agency_structure": context.get("agency_structure", {}),
                "rhetorical_salience": mapping.get("rhetorical_salience"),
                "rhetorical_functions": mapping.get("rhetorical_functions", []),
                "evidence_span": mapping.get("evidence_span"),
                "claim_boundary": "Genre-sensitive interpretation; do not aggregate as frequency without document/register context.",
            }
        )
    return {
        "version": "1.0",
        "case_id": case_id,
        "generated_at": generated_at,
        "status": "draft" if contexts else "stub",
        "contexts": contexts,
    }


def build_absence(case_id: str, generated_at: str) -> dict[str, Any]:
    rows = ABSENCE_ROWS_BY_CASE.get(case_id, [])
    return {
        "version": "1.0",
        "case_id": case_id,
        "generated_at": generated_at,
        "status": "draft" if rows else "stub",
        "method_note": "Absence rows state what would count as presence, what appears muted, and which CMT evidence motivates the review question.",
        "matrix": rows,
    }


def md_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    if not rows:
        return "_No rows._"
    lines = [
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(lines)


def write_markdown(case_id: str, critical: dict[str, Any], rhetorical: dict[str, Any], absence: dict[str, Any]) -> None:
    analysis_dir = case_dir(case_id) / "analysis"
    profiles = critical["cluster_profiles"]
    critical_lines = [
        f"# Critical Metaphor Analysis: {case_id}",
        "",
        "Status: draft, CMT-backed interpretive layer.",
        "",
    ]
    for profile in profiles:
        critical_lines.extend(
            [
                f"## {profile['cluster_id']}",
                "",
                f"Mapping IDs: {', '.join(profile['mapping_ids'])}",
                "",
                f"Persuasive function: {profile['persuasive_function']}",
                "",
                f"Relation to Koenigsbergian analysis: {profile['relation_to_koenigsbergian_analysis']}",
                "",
                "Rival readings:",
                "",
                *[f"- {item}" for item in profile["rival_readings"]],
                "",
                "Negative cases:",
                "",
                *[f"- {item}" for item in profile["negative_cases"]],
                "",
            ]
        )
    (analysis_dir / "critical-metaphor-analysis.md").write_text("\n".join(critical_lines), encoding="utf-8")

    contexts = rhetorical["contexts"]
    rhetorical_md = f"""# Rhetorical Genre Analysis: {case_id}

Status: draft, CMT-backed rhetorical context layer.

{md_table(contexts, ["mapping_id", "document_id", "genre", "rhetorical_salience", "emotional_posture", "rhetorical_action"])}

These rows keep public address, ceremonial address, and inaugural address
claims separate. Genre-sensitive claims should cite mapping IDs and document
contexts rather than treating every mapping as interchangeable evidence.
"""
    (analysis_dir / "rhetorical-genre-analysis.md").write_text(rhetorical_md, encoding="utf-8")

    absence_md = f"""# Absence And Agency Analysis: {case_id}

Status: draft, systematic absence matrix.

{md_table(absence["matrix"], ["absence_id", "cluster_id", "expected_presence", "possible_absence", "displacement_mechanism", "claim_boundary"])}

Absence claims are review questions until fuller annotation and historical
corroboration show that an expected presence is systematically muted rather
than merely outside the current sample.
"""
    (analysis_dir / "absence-agency-analysis.md").write_text(absence_md, encoding="utf-8")


def build_case(case_id: str) -> dict[str, Any]:
    generated_at = now_iso()
    mappings = load_mappings(case_id)
    critical = build_critical(case_id, generated_at, mappings)
    rhetorical = build_rhetorical(case_id, generated_at, mappings)
    absence = build_absence(case_id, generated_at)
    analysis_dir = case_dir(case_id) / "analysis"
    write_json(analysis_dir / "critical-metaphor-analysis.json", critical)
    write_json(analysis_dir / "rhetorical-genre-analysis.json", rhetorical)
    write_json(analysis_dir / "absence-agency-analysis.json", absence)
    write_markdown(case_id, critical, rhetorical, absence)
    return {
        "case_id": case_id,
        "critical_profiles": len(critical["cluster_profiles"]),
        "rhetorical_contexts": len(rhetorical["contexts"]),
        "absence_rows": len(absence["matrix"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", default=None, help="Optional case id")
    args = parser.parse_args()

    for case_id in case_ids(args.case_id):
        result = build_case(case_id)
        print(
            f"{case_id}: built {result['critical_profiles']} cluster profile(s), "
            f"{result['rhetorical_contexts']} rhetorical context(s), "
            f"and {result['absence_rows']} absence row(s)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
