from arbiter_study.core import (
    aggregate_provider_crowd, baseline_label, candidates, public_jev_state,
)
from arbiter_study.models import ModelAnswer, Question


def answer(provider: str, index: int, label: str, rationale: str = "") -> ModelAnswer:
    return ModelAnswer(
        member_id=f"{provider}-initial-{index}", provider=provider,
        stage="initial", sample_index=index, requested_model="test",
        answer_label=label, confidence=0.9, rationale=rationale,
        latency_ms=1, raw_response={},
    )


def test_provider_crowds_get_one_equal_vote_and_internal_plurality() -> None:
    question = Question(id="q", question="?", choices=["a", "b", "c"], correct_label="A")
    raw = [
        answer("openai", 1, "A"), answer("openai", 2, "A"), answer("openai", 3, "B"),
        answer("anthropic", 1, "B"), answer("anthropic", 2, "B"), answer("anthropic", 3, "B"),
        answer("mistral", 1, "A"), answer("mistral", 2, "A"), answer("mistral", 3, "A"),
    ]
    positions = [aggregate_provider_crowd(question, provider, raw, 7)
                 for provider in ("openai", "anthropic", "mistral")]
    assert [position.answer_label for position in positions] == ["A", "B", "A"]
    assert baseline_label(question, positions, 11) == "A"
    assert positions[0].label_counts == {"A": 2, "B": 1}


def test_candidates_collapse_positions_and_remove_provider_identity() -> None:
    question = Question(id="q", question="2+2?", choices=["3", "4", "5"], correct_label="B")
    raw = [
        answer("openai", 1, "B", "one"),
        answer("anthropic", 1, "A", "two"),
        answer("mistral", 1, "B", "three"),
    ]
    positions = [aggregate_provider_crowd(question, provider, raw, 7)
                 for provider in ("openai", "anthropic", "mistral")]
    options = candidates(question, positions, seed=7)
    assert len(options) == 2
    serialized = str(public_jev_state(question, options))
    assert "openai" not in serialized
    assert "anthropic" not in serialized
    assert "mistral" not in serialized
    assert "correct_label" not in serialized
    assert sum(len(candidate.support) for candidate in options) == 3


def test_complete_ties_are_deterministic() -> None:
    question = Question(id="q", question="?", choices=["a", "b", "c"], correct_label="A")
    raw = [answer("openai", 1, "A"), answer("anthropic", 1, "B"), answer("mistral", 1, "C")]
    positions = [aggregate_provider_crowd(question, provider, raw, 7)
                 for provider in ("openai", "anthropic", "mistral")]
    assert baseline_label(question, positions, 11) == baseline_label(question, positions, 11)
