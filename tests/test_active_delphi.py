from active_delphi.generate import OWNER_ROTATIONS, PROVIDERS, RELATIONS, generate_question


def test_link_ownership_rotates_and_partitions_are_balanced() -> None:
    seen = []
    for index in range(6):
        question = generate_question(index, 20260929)
        seen.append(tuple(question.link_owners[relation] for relation in RELATIONS))
        assert len(question.facts) == 18
        assert len(question.support_ids) == 3
        for provider in PROVIDERS:
            facts = question.facts_for(provider)
            assert len(facts) == 6
            assert sum(fact.is_support for fact in facts) == 1
    assert tuple(seen) == OWNER_ROTATIONS


def test_active_generator_is_deterministic_and_balanced() -> None:
    assert generate_question(17, 20260929) == generate_question(17, 20260929)
    labels = [generate_question(i, 20260929).correct_label for i in range(300)]
    assert {label: labels.count(label) for label in "ABCD"} == {
        "A": 75, "B": 75, "C": 75, "D": 75,
    }


def test_no_hidden_flags_needed_in_model_facing_projection() -> None:
    question = generate_question(4, 20260929)
    public = [{"evidence_id": fact.evidence_id, "text": fact.text} for fact in question.facts]
    assert "is_support" not in str(public)
    assert "correct_label" not in str(public)

