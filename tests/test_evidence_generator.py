from evidence_study.generate import PROVIDERS, generate_question


def test_generator_partitions_every_required_link() -> None:
    question = generate_question(7, 20260925)
    assert len(question.facts) == 18
    assert len(question.support_ids) == 3
    for provider in PROVIDERS:
        facts = question.facts_for(provider)
        assert len(facts) == 6
        assert sum(fact.is_support for fact in facts) == 1


def test_generator_is_deterministic_and_balances_labels() -> None:
    first = generate_question(11, 20260925)
    assert first == generate_question(11, 20260925)
    labels = [generate_question(i, 20260925).correct_label for i in range(300)]
    assert {label: labels.count(label) for label in "ABCD"} == {
        "A": 75, "B": 75, "C": 75, "D": 75,
    }


def test_novel_question_has_no_ground_truth_leak_in_public_fields() -> None:
    question = generate_question(3, 20260925)
    public = {
        "question": question.question,
        "choices": question.choices,
        "facts": [{"evidence_id": f.evidence_id, "text": f.text} for f in question.facts],
    }
    serialized = str(public)
    assert "correct_label" not in serialized
    assert "is_support" not in serialized
