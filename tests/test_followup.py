"""Follow-up study: the pipeline and the locked analysis, run end to end on fake models."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import followup_study.pipeline as pipeline
from analyze_followup import analyse
from arbiter_study.core import candidates
from arbiter_study.models import Arbitration, DelphiAssessment, ModelAnswer, ProviderPosition, Question
from followup_study.seat import seat_position
from followup_study.spec import (
    IMPLEMENTATION_FILES, arm_config, implementation_hash, load_spec, require_frozen, sha256_file,
)
from followup_study.store import FollowupStore
from run_followup_calibration import choose

ROOT = Path(__file__).resolve().parents[1]
CHOICES = ["w", "x", "y", "z"]


def make_spec(tmp: Path, questions: list[Question]) -> tuple[dict, str]:
    spec = json.loads((ROOT / "config/followup_v1.json").read_text())
    data = tmp / "followup.jsonl"
    data.write_text("".join(q.model_dump_json() + "\n" for q in questions), encoding="utf-8")
    spec.update(dataset_path=str(data), dataset_sha256=sha256_file(data), question_count=len(questions),
                bootstrap_draws=200, max_recorded_cost_usd=10.0)
    spec["arms"]["matched"] = {"openai": "big-o", "anthropic": "big-a", "mistral": "big-m"}
    path = tmp / "config.json"
    path.write_text(json.dumps(spec))
    return load_spec(path)


class FakeWorld:
    """Scripted models. Truth is known only here; every call checks the model saw a masked label."""

    def __init__(self, truth: dict[str, str], fail: set[str] = frozenset()):
        self.truth, self.fail, self.calls = truth, set(fail), []

    def wrong(self, qid: str) -> str:
        return next(label for label in "ABCD" if label != self.truth[qid])

    async def ask_provider(self, provider, question, config, *, member_id, stage, sample_index, context=None):
        assert question.correct_label == "A"  # ground truth never reaches a model
        self.calls.append((question.id, config.model(provider), stage))
        if config.model(provider) in self.fail:
            raise RuntimeError("scripted failure")
        big = config.model(provider).startswith("big")
        # Small models are always wrong; big models right except Mistral's first sample.
        label = self.truth[question.id] if big and not (provider == "mistral" and sample_index == 1) \
            else self.wrong(question.id)
        return ModelAnswer(member_id=member_id, provider=provider, stage=stage, sample_index=sample_index,
                           requested_model=config.model(provider), answer_label=label, confidence=.6,
                           rationale="r", latency_ms=1, raw_response={}, estimated_cost_usd=.001)

    async def answer_alone(self, question, config):
        assert question.correct_label == "A"
        label = self.truth[question.id]
        return Arbitration(selected_candidate_id=label, selected_answer_label=label, confidence=.9,
                           probabilities={label: .9}, latency_ms=1, raw_response={}, estimated_cost_usd=.0005)

    async def assess_delphi(self, question, positions, config):
        options = candidates(question, positions, config.arbitration_seed)
        pick = options[0]
        action = "reconsider" if len(options) > 1 else "stop"
        return DelphiAssessment(action=action, selected_candidate_id=pick.candidate_id,
                                selected_answer_label=pick.answer_label, answer_confidence=.5,
                                answer_probabilities={}, action_confidence=.5, action_probabilities={},
                                latency_ms=1, raw_response={}, estimated_cost_usd=.0005)

    async def arbitrate(self, question, positions, config):
        options = candidates(question, positions, config.arbitration_seed)
        # Prefer the most-supported candidate, like a judge leaning on the council.
        pick = max(options, key=lambda o: (len(o.support), o.candidate_id))
        return Arbitration(selected_candidate_id=pick.candidate_id, selected_answer_label=pick.answer_label,
                           confidence=.5, probabilities={}, latency_ms=1, raw_response={},
                           estimated_cost_usd=.0005)


@pytest.fixture
def world(monkeypatch):
    def install(truth, fail=frozenset()):
        fake = FakeWorld(truth, fail)
        for name in ("ask_provider", "answer_alone", "assess_delphi", "arbitrate"):
            monkeypatch.setattr(pipeline, name, getattr(fake, name))
        return fake
    return install


def questions(n: int) -> list[Question]:
    return [Question(id=f"q{i}", question=f"Question {i}?", choices=CHOICES, correct_label="ABCD"[i % 4])
            for i in range(n)]


async def run_all(spec, freeze_hash, qs, db) -> None:
    configs = {arm: arm_config(spec, arm) for arm in ("small", "matched")}
    with FollowupStore(db, freeze_hash, qs) as store:
        for q in qs:
            await pipeline.run_question(q, configs, store, spec["max_attempts_per_stage"])


async def test_every_condition_finishes_and_the_analysis_reads_it(tmp_path, world):
    qs = questions(8)
    spec, freeze_hash = make_spec(tmp_path, qs)
    fake = world({q.id: q.correct_label for q in qs})
    db = tmp_path / "run.sqlite3"
    await run_all(spec, freeze_hash, qs, db)

    with FollowupStore(db, freeze_hash, qs) as store:
        for stage in pipeline.FINAL_STAGES.values():
            assert store.complete_count(stage) == 8
    # Both councils were asked, and the seat's reconsideration went to the matched models.
    models = {model for _, model, _ in fake.calls}
    assert {"gpt-4.1-mini-2025-04-14", "big-o", "big-a", "big-m"} <= models

    report = analyse(spec, freeze_hash, str(db))
    assert "D  JEV alone: 100.00% (n=8)" in report
    assert "F  Delphi, original small council: 0.00% (n=8)" in report
    assert "F  Delphi, strength-matched council: 100.00% (n=8)" in report
    assert "JEV alone minus small-council Delphi (replication): +100.00 pp" in report
    assert "Primary evaluable: YES" in report


async def test_resuming_makes_no_new_calls(tmp_path, world):
    qs = questions(3)
    spec, freeze_hash = make_spec(tmp_path, qs)
    fake = world({q.id: q.correct_label for q in qs})
    db = tmp_path / "run.sqlite3"
    await run_all(spec, freeze_hash, qs, db)
    before = len(fake.calls)
    await run_all(spec, freeze_hash, qs, db)
    assert len(fake.calls) == before


async def test_analysis_is_locked_while_the_run_is_unfinished(tmp_path, world):
    qs = questions(4)
    spec, freeze_hash = make_spec(tmp_path, qs)
    world({q.id: q.correct_label for q in qs})
    db = tmp_path / "run.sqlite3"
    await run_all(spec, freeze_hash, qs[:3], db)  # the database knows all 4; only 3 are run
    with FollowupStore(db, freeze_hash, qs):
        pass
    with pytest.raises(RuntimeError, match="still in progress"):
        analyse(spec, freeze_hash, str(db))


async def test_a_model_that_keeps_failing_ends_its_conditions_and_is_counted_missing(tmp_path, world):
    qs = questions(4)
    spec, freeze_hash = make_spec(tmp_path, qs)
    world({q.id: q.correct_label for q in qs}, fail={"big-a"})
    db = tmp_path / "run.sqlite3"
    await run_all(spec, freeze_hash, qs, db)
    with pytest.raises(RuntimeError, match="still in progress"):
        analyse(spec, freeze_hash, str(db))  # one failure each: a second attempt is still owed
    await run_all(spec, freeze_hash, qs, db)  # the resumed run uses the second attempt
    report = analyse(spec, freeze_hash, str(db))
    assert "Primary evaluable: NO (4 questions missing)" in report
    assert "D  JEV alone: 100.00% (n=4)" in report


def test_the_seat_is_anonymous_and_joins_a_matching_candidate():
    q = Question(id="q", question="?", choices=CHOICES, correct_label="A")
    direct = Arbitration(selected_candidate_id="B", selected_answer_label="B", confidence=.9,
                         probabilities={}, latency_ms=1, raw_response={})
    council = [ProviderPosition(position_id=f"{p}-initial-position", provider=p, stage="initial",
                                answer_label=label, label_counts={label: 3}, samples=[])
               for p, label in (("openai", "B"), ("anthropic", "C"), ("mistral", "C"))]
    options = candidates(q, council + [seat_position(direct)], 1)
    assert sorted(o.answer_label for o in options) == ["B", "C"]
    support_b = next(o for o in options if o.answer_label == "B").support
    assert len(support_b) == 2
    assert "jev" not in json.dumps([o.model_dump() for o in options]).lower()
    assert "seat" not in json.dumps([o.model_dump() for o in options]).lower()


def test_the_draft_config_cannot_run():
    spec, _ = load_spec(ROOT / "config/followup_v1.json")
    with pytest.raises(RuntimeError, match="isn't frozen"):
        require_frozen(spec, ROOT)
    assert tuple(spec["implementation_files"]) == IMPLEMENTATION_FILES


def test_hashes_ignore_windows_line_endings(tmp_path):
    for name in IMPLEMENTATION_FILES:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes().replace(b"\n", b"\r\n"))
    assert implementation_hash(tmp_path) == implementation_hash(ROOT)


def test_calibration_picks_the_cheapest_close_model_or_falls_back_to_the_best():
    spec = {"match_tolerance_pp": 3}
    table = {
        "openai|a": {"provider": "openai", "model": "a", "candidate": True, "accuracy": .86, "cost_per_question": .02},
        "openai|b": {"provider": "openai", "model": "b", "candidate": True, "accuracy": .90, "cost_per_question": .05},
        "anthropic|c": {"provider": "anthropic", "model": "c", "candidate": True, "accuracy": .70, "cost_per_question": .01},
        "anthropic|d": {"provider": "anthropic", "model": "d", "candidate": True, "accuracy": .75, "cost_per_question": .09},
        "mistral|e": {"provider": "mistral", "model": "e", "candidate": True, "accuracy": .87, "cost_per_question": .01},
        "mistral|small": {"provider": "mistral", "model": "small", "candidate": False, "accuracy": .99, "cost_per_question": .0},
    }
    table["openai|f"] = {"provider": "openai", "model": "f", "candidate": True, "accuracy": .97, "cost_per_question": .001}
    chosen = choose(spec, table, jev_accuracy=.88)
    assert chosen["openai"]["model"] == "a"          # within 3 points and cheapest; f is far too strong
    assert chosen["anthropic"]["model"] == "d"       # none within 3 points: closest to JEV
    assert chosen["anthropic"]["gap_to_jev_pp"] == 13.0
    assert chosen["mistral"]["model"] == "e"         # the small-council model is never a candidate


def test_reasoning_is_switched_off_only_where_a_model_has_it():
    from followup_study.providers import reasoning_off
    assert reasoning_off("openai", "gpt-5.4-2026-03-05") == {"reasoning_effort": "none"}
    assert reasoning_off("openai", "gpt-4.1-2025-04-14") == {}
    assert reasoning_off("openai", "gpt-4.1-mini-2025-04-14") == {}   # the small council is unchanged
    assert reasoning_off("mistral", "mistral-medium-3-5") == {"reasoning_effort": "none"}
    assert reasoning_off("mistral", "ministral-14b-2512") == {}
    assert reasoning_off("anthropic", "claude-sonnet-5-5") == {"thinking": {"type": "between_tools"}}
    assert reasoning_off("anthropic", "claude-opus-4-8") == {}
    assert reasoning_off("anthropic", "claude-haiku-4-5-20251001") == {}


async def test_a_mistral_reply_with_thinking_is_rejected(monkeypatch):
    import followup_study.providers as providers
    async def fake_post(*_args, **_kwargs):
        return {"choices": [{"message": {"content": [{"type": "thinking", "thinking": []},
                                                    {"type": "text", "text": "{}"}]}}]}, 1.0
    monkeypatch.setattr(providers, "post", fake_post)
    monkeypatch.setenv("MISTRAL_API_KEY", "x")
    spec, _ = load_spec(ROOT / "config/followup_v1.json")
    config = arm_config(spec, "small")
    q = Question(id="q", question="?", choices=CHOICES, correct_label="A")
    with pytest.raises(providers.ProviderError, match="reasoning"):
        await providers.ask_mistral(q, config, member_id="m", stage="initial", sample_index=1)


def test_temperature_is_left_out_only_for_models_that_reject_it():
    from followup_study.providers import temperature
    spec, _ = load_spec(ROOT / "config/followup_v1.json")
    config = arm_config(spec, "small")
    assert temperature(config, "claude-opus-5-5") == {}
    assert temperature(config, "claude-opus-4-8") == {}
    assert temperature(config, "claude-haiku-4-5-20251001") == {"temperature": 0.7}
    assert temperature(config, "gpt-5.4-2026-03-05") == {"temperature": 0.7}


async def test_a_rate_limited_call_waits_and_tries_again(monkeypatch):
    import followup_study.providers as providers
    calls = []

    async def flaky(question, config, **kwargs):
        calls.append(1)
        if len(calls) < 3:
            raise providers.ProviderError("mistral request failed: HTTP 429: rate limited")
        return "answer"

    async def no_wait(_seconds):
        return None

    monkeypatch.setitem(providers.PROVIDER_FUNCTIONS, "mistral", flaky)
    monkeypatch.setattr(providers.asyncio, "sleep", no_wait)
    result = await providers.ask_provider("mistral", None, None, member_id="m", stage="initial", sample_index=1)
    assert result == "answer" and len(calls) == 3


async def test_other_errors_are_not_retried(monkeypatch):
    import followup_study.providers as providers
    calls = []

    async def broken(question, config, **kwargs):
        calls.append(1)
        raise providers.ProviderError("mistral request failed: HTTP 400: bad request")

    monkeypatch.setitem(providers.PROVIDER_FUNCTIONS, "mistral", broken)
    with pytest.raises(providers.ProviderError):
        await providers.ask_provider("mistral", None, None, member_id="m", stage="initial", sample_index=1)
    assert len(calls) == 1


async def test_raising_the_cap_is_recorded_and_shown_in_the_report(tmp_path, world):
    qs = questions(3)
    spec, freeze_hash = make_spec(tmp_path, qs)
    world({q.id: q.correct_label for q in qs})
    db = tmp_path / "run.sqlite3"
    await run_all(spec, freeze_hash, qs, db)
    with FollowupStore(db, freeze_hash, qs) as store:
        assert store.effective_cap(10.0) == 10.0
        with pytest.raises(RuntimeError, match="above the current"):
            store.raise_cap(10.0, 5.0, "lower", "2026-11-20")
        with pytest.raises(RuntimeError, match="reason"):
            store.raise_cap(10.0, 40.0, " ", "2026-11-20")
        store.raise_cap(10.0, 40.0, "Estimate was low", "2026-11-20")
        assert store.effective_cap(10.0) == 40.0
    report = analyse(spec, freeze_hash, str(db))
    assert "Cap raised on 2026-11-20 from $10.00 to $40.00" in report
    assert "Estimate was low" in report
    assert "does strength help?" in report


async def test_only_unfinished_questions_are_picked_up(tmp_path, world):
    qs = questions(4)
    spec, freeze_hash = make_spec(tmp_path, qs)
    fake = world({q.id: q.correct_label for q in qs})
    db = tmp_path / "run.sqlite3"
    await run_all(spec, freeze_hash, qs[:2], db)   # as if the cap stopped the run after two questions
    with FollowupStore(db, freeze_hash, qs):
        pass
    fake.calls.clear()
    await run_all(spec, freeze_hash, qs, db)
    assert {qid for qid, _, _ in fake.calls} == {"q2", "q3"}
