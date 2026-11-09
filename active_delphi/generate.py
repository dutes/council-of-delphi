from __future__ import annotations

import itertools
import random
from pathlib import Path

from active_delphi.models import ActiveFact, ActiveQuestion
from evidence_study.generate import PROVIDERS, SYLLABLES, token


RELATIONS = ("stored_in", "administered_by", "uses_clearance")
OWNER_ROTATIONS = tuple(itertools.permutations(PROVIDERS))


def generate_question(index: int, seed: int, *, prefix: str = "active") -> ActiveQuestion:
    rng = random.Random(f"{seed}:{index}")
    used: set[str] = set()
    artifacts = [token(rng, "Artifact", used) for _ in range(6)]
    vaults = [token(rng, "Vault", used) for _ in range(6)]
    sectors = [token(rng, "Sector", used) for _ in range(6)]
    clearances = [token(rng, "Code", used) for _ in range(6)]

    correct_slot = index % 4
    choices = clearances[1:4]
    choices.insert(correct_slot, clearances[0])
    labels = [chr(ord("A") + i) for i in range(4)]

    raw: list[tuple[str, str, str, str, bool]] = []
    for i in range(6):
        raw.extend([
            (f"{artifacts[i]} is stored in {vaults[i]}.", "stored_in", artifacts[i], vaults[i], i == 0),
            (f"{vaults[i]} is administered by {sectors[i]}.", "administered_by", vaults[i], sectors[i], i == 0),
            (f"{sectors[i]} uses clearance {clearances[i]}.", "uses_clearance", sectors[i], clearances[i], i == 0),
        ])
    support = [row for row in raw if row[-1]]
    distractors = [row for row in raw if not row[-1]]
    rng.shuffle(distractors)

    owners = OWNER_ROTATIONS[index % len(OWNER_ROTATIONS)]
    partitions: dict[str, list[tuple[str, str, str, str, bool]]] = {
        provider: distractors[i * 5:(i + 1) * 5] for i, provider in enumerate(PROVIDERS)
    }
    for stage_index, row in enumerate(support):
        partitions[owners[stage_index]].append(row)

    facts: list[ActiveFact] = []
    support_ids: list[str] = []
    link_owners = {relation: owners[i] for i, relation in enumerate(RELATIONS)}
    number = 1
    for provider in PROVIDERS:
        rng.shuffle(partitions[provider])
        for text, relation, subject, obj, is_support in partitions[provider]:
            evidence_id = f"E{number:02d}"
            facts.append(ActiveFact(
                evidence_id=evidence_id, text=text, partition=provider,
                relation=relation, subject=subject, object=obj, is_support=is_support,
            ))
            if is_support:
                support_ids.append(evidence_id)
            number += 1

    return ActiveQuestion(
        id=f"{prefix}-chain-{index:04d}",
        question=f"Which clearance code applies to {artifacts[0]}?",
        choices=choices,
        correct_label=labels[correct_slot],
        target_artifact=artifacts[0],
        facts=facts,
        support_ids=sorted(support_ids),
        link_owners=link_owners,
        metadata={"seed": seed, "index": index, "owner_rotation": list(owners)},
    )


def generate_dataset(count: int, seed: int, path: Path, *, start_index: int = 0,
                     prefix: str = "active") -> None:
    questions = [generate_question(start_index + i, seed, prefix=prefix) for i in range(count)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(q.model_dump_json() for q in questions) + "\n", encoding="utf-8")

