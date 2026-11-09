from collections import Counter

from conflict_ablation.arbiters import keyword_rule
from conflict_ablation.generate import QUALITY_PACKETS, generate_question


def test_generator_balances_labels_and_quality_classes() -> None:
    questions = [generate_question(i, 20261010, prefix="test") for i in range(300)]
    assert Counter(q.correct_label for q in questions) == {label: 75 for label in "ABCD"}
    qualities = Counter(c.quality_class for q in questions for s in q.stages for c in s.candidates if c.is_correct)
    assert qualities == {packet[0]: 180 for packet in QUALITY_PACKETS}


def test_each_stage_has_one_policy_correct_candidate_and_shuffled_positions() -> None:
    positions = Counter()
    for index in range(300):
        question = generate_question(index, 20261010, prefix="test")
        for stage in question.stages:
            correct = [c for c in stage.candidates if c.is_correct]
            assert len(correct) == 1
            positions[correct[0].candidate_id] += 1
    assert positions == {"C1": 300, "C2": 300, "C3": 300}


def test_keyword_rule_is_frozen_and_selects_policy_winner_on_templates() -> None:
    for index in range(30):
        question = generate_question(index, 20261010, prefix="test")
        for stage in question.stages:
            decision = keyword_rule(stage)
            selected = next(c for c in stage.candidates if c.candidate_id == decision.selected_candidate_id)
            assert selected.is_correct


def test_public_projection_omits_ground_truth() -> None:
    question = generate_question(4, 20261010, prefix="test")
    public = [{"id": c.candidate_id, "text": c.public_text} for s in question.stages for c in s.candidates]
    assert "is_correct" not in str(public)
    assert "quality_class" not in str(public)
