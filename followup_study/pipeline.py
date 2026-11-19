"""One question through every follow-up condition.

Conditions (see docs/FOLLOWUP_PROTOCOL.md):
  D          jev_alone                 JEV answers with no council input
  F-small    small:*                   Delphi with the first study's council
  F-matched  matched:*                 Delphi with the strength-matched council
  G          seat:*                    F-matched, plus JEV's own answer as a candidate
  C-matched  (computed in analysis)    equal vote over the matched council's positions

The Delphi procedure is the first study's, unchanged: three samples per model,
a JEV assessment that stops or asks for one reconsideration round, then a JEV
selection among the revised positions.
"""

from __future__ import annotations

import asyncio

from arbiter_study.config import StudyConfig
from arbiter_study.core import PROVIDERS, aggregate_provider_crowd, reconsideration_context
from arbiter_study.jev import answer_alone, arbitrate, assess_delphi
from arbiter_study.models import Arbitration, DelphiAssessment, ModelAnswer, ProviderPosition, Question
from followup_study.providers import ask_provider
from followup_study.seat import seat_position
from followup_study.store import FollowupStore


FINAL_STAGES = {
    "jev_alone": "jev_alone",
    "small": "small:delphi_final",
    "matched": "matched:delphi_final",
    "seat": "seat:delphi_final",
}


def as_final(decision: Arbitration | DelphiAssessment) -> Arbitration:
    """The answer a Delphi run ends on, whether it stopped or reconsidered."""
    if isinstance(decision, Arbitration):
        return decision.model_copy(update={"estimated_cost_usd": 0})
    return Arbitration(
        selected_candidate_id=decision.selected_candidate_id,
        selected_answer_label=decision.selected_answer_label,
        confidence=decision.answer_confidence, probabilities=decision.answer_probabilities,
        resolved_model="derived-from-delphi-controller", latency_ms=0,
        input_tokens=0, output_tokens=0, estimated_cost_usd=0,
        raw_response={"derived_from": "controller", "action": decision.action},
    )


async def answer_stage(question: Question, config: StudyConfig, store: FollowupStore,
                       stage_key: str, model_stage: str, members: list[tuple[str, int]],
                       context: dict | None, max_attempts: int) -> list[ModelAnswer]:
    have = {answer.member_id for answer in store.answers(question.id, stage_key)}
    eligible = []
    for provider, index in members:
        member_id = f"{provider}-{model_stage}-{index}"
        if member_id not in have and store.attempts(question.id, stage_key, member_id) < max_attempts:
            eligible.append((provider, index, member_id))
    outcomes = await asyncio.gather(*(
        ask_provider(provider, question, config, member_id=member_id, stage=model_stage,
                     sample_index=index, context=context)
        for provider, index, member_id in eligible
    ), return_exceptions=True)
    for (_, _, member_id), outcome in zip(eligible, outcomes, strict=True):
        if isinstance(outcome, ModelAnswer):
            store.save_answer(question.id, stage_key, outcome)
        else:
            store.save_failure(question.id, stage_key, member_id, outcome)
            print(f"  {stage_key} {member_id} failed: {outcome}")
    return store.answers(question.id, stage_key)


async def decision_stage(question: Question, store: FollowupStore, stage: str, model: type,
                         call, max_attempts: int):
    existing = store.decision(question.id, stage, model)
    if existing is not None:
        return existing
    if store.attempts(question.id, stage) >= max_attempts:
        return None
    try:
        result = await call()
    except Exception as exc:  # noqa: BLE001 - every failure is recorded, never retried silently
        store.save_failure(question.id, stage, None, exc)
        print(f"  {stage} failed: {exc}")
        return None
    store.save_decision(question.id, stage, result)
    return result


def crowd_positions(question: Question, store: FollowupStore, stage_key: str, model_stage: str,
                    answers: list[ModelAnswer], seed: int) -> list[ProviderPosition]:
    positions = store.positions(question.id, stage_key)
    if not positions:
        positions = [aggregate_provider_crowd(question, provider, answers, seed, model_stage)
                     for provider in PROVIDERS]
        store.save_positions(question.id, stage_key, positions)
    return positions


async def run_delphi(question: Question, config: StudyConfig, store: FollowupStore, prefix: str,
                     council: list[ProviderPosition], extra: list[ProviderPosition],
                     max_attempts: int) -> Arbitration | None:
    """The first study's Delphi procedure. ``extra`` positions (the seat) stay in every list JEV sees."""
    final_stage = f"{prefix}:delphi_final"
    done = store.decision(question.id, final_stage, Arbitration)
    if done is not None:
        return done
    candidates_now = council + extra
    controller = await decision_stage(
        question, store, f"{prefix}:controller", DelphiAssessment,
        lambda: assess_delphi(question, candidates_now, config), max_attempts)
    if controller is None:
        return None
    if controller.action == "reconsider":
        context = reconsideration_context(question, candidates_now, config.arbitration_seed)
        revised = await answer_stage(question, config, store, f"{prefix}:reconsideration",
                                     "reconsideration", [(p, 1) for p in PROVIDERS], context,
                                     max_attempts)
        if len(revised) != len(PROVIDERS):
            return None
        revised_positions = crowd_positions(question, store, f"{prefix}:reconsideration",
                                            "reconsideration", revised, config.crowd_seed)
        final_list = revised_positions + extra
        source = await decision_stage(
            question, store, f"{prefix}:final_select", Arbitration,
            lambda: arbitrate(question, final_list, config), max_attempts)
        if source is None:
            return None
    else:
        source = controller
    final = as_final(source)
    store.save_decision(question.id, final_stage, final, billable=False)
    return final


def finished(store: FollowupStore, question_id: str) -> bool:
    return all(store.decision(question_id, stage, Arbitration) is not None
               for stage in FINAL_STAGES.values())


async def run_question(source: Question, configs: dict[str, StudyConfig], store: FollowupStore,
                       max_attempts: int) -> bool:
    """Run every condition for one question. Returns True when all four finals exist."""
    question = source.model_copy(update={"correct_label": "A"})  # ground truth never leaves this machine
    members = [(provider, index) for provider in PROVIDERS
               for index in range(1, configs["matched"].crowd_size + 1)]

    direct = await decision_stage(question, store, "jev_alone", Arbitration,
                                  lambda: answer_alone(question, configs["matched"]), max_attempts)

    councils: dict[str, list[ProviderPosition] | None] = {}
    for arm in ("small", "matched"):
        answers = await answer_stage(question, configs[arm], store, f"{arm}:initial", "initial",
                                     members, None, max_attempts)
        councils[arm] = (crowd_positions(question, store, f"{arm}:initial", "initial", answers,
                                         configs[arm].crowd_seed)
                         if len(answers) == len(members) else None)

    for arm in ("small", "matched"):
        if councils[arm] is not None:
            await run_delphi(question, configs[arm], store, arm, councils[arm], [], max_attempts)
    if councils["matched"] is not None and direct is not None:
        await run_delphi(question, configs["matched"], store, "seat", councils["matched"],
                         [seat_position(direct)], max_attempts)

    return finished(store, question.id)
