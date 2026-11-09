from __future__ import annotations

import itertools
import random
from pathlib import Path

from conflict_ablation.models import ConflictCandidate, ConflictQuestion, ConflictStage
from evidence_study.generate import SYLLABLES, token


RELATIONS = ("stored_in", "administered_by", "uses_clearance")
QUALITY_PACKETS = (
    (
        "currency",
        "the current controlling master register, signed after its latest audit",
        "an authentic archived master register explicitly marked superseded",
        "a current-looking working draft explicitly marked not ratified",
    ),
    (
        "authority",
        "the authenticated primary ledger maintained and signed by the responsible custodian",
        "a secondary digest that warns it may not reflect the primary ledger",
        "an anonymous recollection with no verifiable source record",
    ),
    (
        "directness",
        "a tamper-evident machine audit log directly recording the event",
        "an analyst inference derived indirectly from an incomplete summary",
        "third-party hearsay that was never checked against the event log",
    ),
    (
        "independence",
        "two independently authenticated records from separate systems that agree",
        "two matching copies that both trace to the same unverified source",
        "a single uncorroborated note whose author is unknown",
    ),
    (
        "correction",
        "the final audited correction explicitly replacing the preliminary entry",
        "the preliminary entry explicitly withdrawn after the final audit",
        "a proposed correction that was reviewed but formally rejected",
    ),
)
CANDIDATE_PERMUTATIONS = tuple(itertools.permutations(range(3)))


def _claim(relation: str, subject: str, obj: str) -> str:
    if relation == "stored_in":
        return f"{subject} is stored in {obj}."
    if relation == "administered_by":
        return f"{subject} is administered by {obj}."
    return f"{subject} uses clearance {obj}."


def generate_question(index: int, seed: int, *, prefix: str) -> ConflictQuestion:
    rng = random.Random(f"{seed}:{index}")
    used: set[str] = set()
    artifact = token(rng, "Artifact", used)
    vaults = [token(rng, "Vault", used) for _ in range(3)]
    sectors = [token(rng, "Sector", used) for _ in range(3)]
    clearances = [token(rng, "Code", used) for _ in range(6)]
    subjects = (artifact, vaults[0], sectors[0])
    objects = (vaults, sectors, clearances[:3])
    stages = []
    for stage_index, (relation, subject, stage_objects) in enumerate(zip(RELATIONS, subjects, objects)):
        quality, good, weak_one, weak_two = QUALITY_PACKETS[(index + stage_index) % len(QUALITY_PACKETS)]
        provenances = [good, weak_one, weak_two]
        base_candidates = [ConflictCandidate(
            candidate_id=f"C{candidate_index + 1}",
            claim=_claim(relation, subject, obj), provenance=provenances[candidate_index],
            relation=relation, subject=subject, object=obj, quality_class=quality,
            is_correct=candidate_index == 0,
        ) for candidate_index, obj in enumerate(stage_objects)]
        order = CANDIDATE_PERMUTATIONS[(index * 3 + stage_index) % len(CANDIDATE_PERMUTATIONS)]
        candidates = [base_candidates[position] for position in order]
        for candidate_index, candidate in enumerate(candidates, start=1):
            candidate.candidate_id = f"C{candidate_index}"
        stages.append(ConflictStage(
            stage_index=stage_index, relation=relation, subject=subject, candidates=candidates,
        ))
    correct_slot = index % 4
    choices = clearances[3:6]
    choices.insert(correct_slot, clearances[0])
    return ConflictQuestion(
        id=f"{prefix}-{index:04d}", question=f"Which clearance code applies to {artifact}?",
        choices=choices, correct_label=chr(ord("A") + correct_slot), stages=stages,
    )


def generate_dataset(count: int, seed: int, path: Path, *, start_index: int, prefix: str) -> None:
    questions = [generate_question(start_index+i, seed, prefix=prefix) for i in range(count)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(question.model_dump_json() for question in questions)+"\n", encoding="utf-8")
