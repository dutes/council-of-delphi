from __future__ import annotations

import hashlib
from collections import Counter, defaultdict

from arbiter_study.models import Candidate, ModelAnswer, ProviderPosition, Question


PROVIDERS = ("openai", "anthropic", "mistral")


def valid_label(label: str, question: Question) -> bool:
    return label in [chr(ord("A") + index) for index in range(len(question.choices))]


def deterministic_plurality(question: Question, labels: list[str], seed: int, scope: str) -> str:
    if not labels:
        raise ValueError("At least one label is required")
    if any(not valid_label(label, question) for label in labels):
        raise ValueError("Invalid answer label")
    counts = Counter(labels)
    best = max(counts.values())
    tied = [label for label, count in counts.items() if count == best]
    return min(
        tied,
        key=lambda label: hashlib.sha256(
            f"{scope}:{seed}:{question.id}:{label}".encode()
        ).hexdigest(),
    )


def baseline_label(question: Question, positions: list[ProviderPosition], seed: int) -> str:
    """One equal vote per provider; deterministic hash tie-break for 1-1-1."""
    if len(positions) != 3 or {position.provider for position in positions} != set(PROVIDERS):
        raise ValueError("Exactly one position from each provider is required")
    return deterministic_plurality(
        question, [position.answer_label for position in positions], seed, "council"
    )


def aggregate_provider_crowd(
    question: Question,
    provider: str,
    answers: list[ModelAnswer],
    seed: int,
    stage: str = "initial",
) -> ProviderPosition:
    expected = [answer for answer in answers if answer.provider == provider and answer.stage == stage]
    if not expected:
        raise ValueError(f"No {stage} answers for {provider}")
    label = deterministic_plurality(
        question,
        [answer.answer_label for answer in expected],
        seed,
        f"provider:{provider}:{stage}",
    )
    counts = Counter(answer.answer_label for answer in expected)
    return ProviderPosition(
        position_id=f"{provider}-{stage}-position",
        provider=provider,
        stage=stage,
        answer_label=label,
        label_counts=dict(sorted(counts.items())),
        samples=[
            {
                "answer_label": answer.answer_label,
                "confidence": answer.confidence,
                "rationale": answer.rationale,
                "evidence": answer.evidence,
            }
            for answer in sorted(expected, key=lambda item: item.sample_index)
        ],
    )


def candidates(question: Question, positions: list[ProviderPosition], seed: int) -> list[Candidate]:
    """Collapse matching provider positions while removing provider identities."""
    grouped: dict[str, list[ProviderPosition]] = defaultdict(list)
    for position in positions:
        if not valid_label(position.answer_label, question):
            raise ValueError(f"Invalid answer label {position.answer_label!r}")
        grouped[position.answer_label].append(position)
    labels = sorted(
        grouped,
        key=lambda label: hashlib.sha256(
            f"candidate-order:{seed}:{question.id}:{label}".encode()
        ).hexdigest(),
    )
    result: list[Candidate] = []
    for index, label in enumerate(labels, start=1):
        support = [
            {
                "provider_position": position.answer_label,
                "internal_vote_counts": position.label_counts,
                "samples": position.samples,
            }
            for position in grouped[label]
        ]
        result.append(Candidate(
            candidate_id=f"candidate-{index}", answer_label=label, support=support,
        ))
    return result


def public_jev_state(question: Question, options: list[Candidate]) -> dict:
    return {
        "question": question.question,
        "choices": [
            {"label": chr(ord("A") + index), "text": text}
            for index, text in enumerate(question.choices)
        ],
        "candidate_answers": [candidate.model_dump() for candidate in options],
    }


def reconsideration_context(question: Question, positions: list[ProviderPosition], seed: int) -> dict:
    return public_jev_state(question, candidates(question, positions, seed))
