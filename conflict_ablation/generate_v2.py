from __future__ import annotations

import itertools
import random
from pathlib import Path

from conflict_ablation.models import ConflictCandidate, ConflictQuestion, ConflictStage
from evidence_study.generate import SYLLABLES, token


RELATIONS = ("stored_in", "administered_by", "uses_clearance")
PERMUTATIONS = tuple(itertools.permutations(range(3)))
HARD_PACKETS = (
    ("currency_scope",
     "The header mentions 'superseded' only because a replacement was proposed; the final signed audit rejected that proposal and confirms this remains the current controlling register.",
     "This is labelled the current controlling register and bears an authentic signature, but a later ratified notice explicitly supersedes it.",
     "A working draft is described as current in an email, but its approval block says not ratified and no controlling authority adopted it."),
    ("authority_scope",
     "An anonymous tip prompted the check, but the claim itself is copied from the authenticated primary ledger and the responsible custodian signed the exact entry.",
     "The document calls itself an authenticated primary ledger maintained by the responsible custodian, but the custodian formally disavowed it after the signature was found to be forged.",
     "A secondary digest quotes what it says is a primary entry, yet the primary ledger cannot be produced and the digest warns that it may not reflect the source."),
    ("directness_scope",
     "A hearsay allegation was discarded; the retained finding comes from a tamper-evident machine audit log directly recording this event, with its hash verified.",
     "The exhibit is described as a tamper-evident machine log that directly records the event, but the audit shows it was a simulated training output rather than an event record.",
     "An analyst inferred the mapping from an incomplete dashboard summary; no underlying event log was checked."),
    ("independence_scope",
     "Although the records use the same format, separate audits show they were independently authenticated and collected by separate systems before comparison.",
     "Two reports are labelled independently authenticated and appear to agree, but lineage analysis shows both are copies of the same unverified source.",
     "Several matching notes exist, yet every copy traces to one unknown author and no independent record corroborates it."),
    ("correction_scope",
     "A preliminary correction was first rejected and withdrawn; a revised version was later ratified, and the final audited correction explicitly replaces the old entry.",
     "This text is headed 'final audited correction' and says it replaces the preliminary entry, but a subsequent signed decision rescinded the correction and restored the old entry.",
     "A proposed correction passed an informal review but was formally rejected and never entered into the controlling record."),
)


def _claim(relation: str, subject: str, obj: str) -> str:
    if relation == "stored_in": return f"{subject} is stored in {obj}."
    if relation == "administered_by": return f"{subject} is administered by {obj}."
    return f"{subject} uses clearance {obj}."


def generate_question(index: int, seed: int, *, prefix: str) -> ConflictQuestion:
    rng = random.Random(f"{seed}:{index}"); used: set[str] = set()
    artifact = token(rng,"Artifact",used)
    vaults = [token(rng,"Vault",used) for _ in range(3)]
    sectors = [token(rng,"Sector",used) for _ in range(3)]
    clearances = [token(rng,"Code",used) for _ in range(6)]
    subjects = (artifact,vaults[0],sectors[0]); objects = (vaults,sectors,clearances[:3])
    stages = []
    for stage_index,(relation,subject,stage_objects) in enumerate(zip(RELATIONS,subjects,objects)):
        quality,good,bad1,bad2 = HARD_PACKETS[(index+stage_index)%len(HARD_PACKETS)]
        base = [ConflictCandidate(candidate_id="",claim=_claim(relation,subject,obj),provenance=prov,
                                  relation=relation,subject=subject,object=obj,quality_class=quality,
                                  is_correct=i==0)
                for i,(obj,prov) in enumerate(zip(stage_objects,(good,bad1,bad2)))]
        order = PERMUTATIONS[(index*3+stage_index)%6]
        candidates = [base[position] for position in order]
        for i,candidate in enumerate(candidates,start=1): candidate.candidate_id=f"C{i}"
        stages.append(ConflictStage(stage_index=stage_index,relation=relation,subject=subject,candidates=candidates))
    slot=index%4; choices=clearances[3:6]; choices.insert(slot,clearances[0])
    return ConflictQuestion(id=f"{prefix}-{index:04d}",question=f"Which clearance code applies to {artifact}?",
                            choices=choices,correct_label=chr(ord('A')+slot),stages=stages)


def generate_dataset(count:int,seed:int,path:Path,*,start_index:int,prefix:str)->None:
    questions=[generate_question(start_index+i,seed,prefix=prefix) for i in range(count)]
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text("\n".join(q.model_dump_json() for q in questions)+"\n",encoding="utf-8")

