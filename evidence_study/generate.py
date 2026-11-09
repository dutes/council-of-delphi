from __future__ import annotations

import random
from pathlib import Path

from evidence_study.models import EvidenceFact, EvidenceQuestion


PROVIDERS = ("openai", "anthropic", "mistral")
SYLLABLES = (
    "ba", "cor", "den", "fal", "gis", "hal", "jor", "kel", "lum", "mor",
    "nar", "pel", "quin", "rav", "sol", "tor", "vek", "wyn", "xan", "zir",
)


def token(rng: random.Random, prefix: str, used: set[str]) -> str:
    while True:
        value = prefix + "-" + "".join(rng.choice(SYLLABLES) for _ in range(2)).title() + f"-{rng.randrange(100, 999)}"
        if value not in used:
            used.add(value)
            return value


def generate_question(index: int, seed: int) -> EvidenceQuestion:
    rng = random.Random(f"{seed}:{index}")
    used: set[str] = set()
    artifacts = [token(rng, "Artifact", used) for _ in range(6)]
    vaults = [token(rng, "Vault", used) for _ in range(6)]
    sectors = [token(rng, "Sector", used) for _ in range(6)]
    clearances = [token(rng, "Code", used) for _ in range(6)]

    correct_slot = index % 4
    decoy_codes = clearances[1:4]
    choices = decoy_codes[:]
    choices.insert(correct_slot, clearances[0])
    labels = [chr(ord("A") + i) for i in range(4)]

    raw: list[tuple[str, bool]] = []
    raw.extend([
        (f"{artifacts[0]} is stored in {vaults[0]}.", True),
        (f"{vaults[0]} is administered by {sectors[0]}.", True),
        (f"{sectors[0]} uses clearance {clearances[0]}.", True),
    ])
    for i in range(1, 6):
        raw.extend([
            (f"{artifacts[i]} is stored in {vaults[i]}.", False),
            (f"{vaults[i]} is administered by {sectors[i]}.", False),
            (f"{sectors[i]} uses clearance {clearances[i]}.", False),
        ])

    support = raw[:3]
    distractors = raw[3:]
    rng.shuffle(distractors)
    partitioned: dict[str, list[tuple[str, bool]]] = {
        provider: [support[i]] + distractors[i * 5:(i + 1) * 5]
        for i, provider in enumerate(PROVIDERS)
    }
    facts: list[EvidenceFact] = []
    support_ids: list[str] = []
    evidence_number = 1
    for provider in PROVIDERS:
        rng.shuffle(partitioned[provider])
        for text, is_support in partitioned[provider]:
            evidence_id = f"E{evidence_number:02d}"
            facts.append(EvidenceFact(
                evidence_id=evidence_id, text=text, partition=provider,
                is_support=is_support,
            ))
            if is_support:
                support_ids.append(evidence_id)
            evidence_number += 1

    return EvidenceQuestion(
        id=f"evidence-chain-{index:04d}",
        question=f"Which clearance code applies to {artifacts[0]}?",
        choices=choices,
        correct_label=labels[correct_slot],
        facts=facts,
        support_ids=sorted(support_ids),
        metadata={"generator_seed": seed, "chain_length": 3, "template": "artifact-vault-sector-clearance"},
    )


def generate_dataset(count: int, seed: int, path: Path) -> None:
    questions = [generate_question(i, seed) for i in range(count)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(q.model_dump_json() for q in questions) + "\n", encoding="utf-8")


if __name__ == "__main__":
    generate_dataset(300, 20260925, Path("data/evidence_partitioned_300.jsonl"))
