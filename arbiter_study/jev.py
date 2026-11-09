from __future__ import annotations

import os
import time
from typing import Any

import httpx

from arbiter_study.config import StudyConfig
from arbiter_study.core import candidates, public_jev_state
from arbiter_study.models import Arbitration, DelphiAssessment, ProviderPosition, Question


class ArbitrationError(RuntimeError):
    def __init__(self, message: str, raw: dict[str, Any] | None = None):
        super().__init__(message)
        self.raw = raw


async def _post(payload: dict[str, Any], config: StudyConfig) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.post(
                os.getenv("JEV_API_URL", "https://api.typesafe.ai/v1/systemone"),
                headers={"Authorization": f"Bearer {config.key('jev')}",
                         "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            return response.json(), (time.perf_counter() - started) * 1000
    except (httpx.HTTPError, ValueError) as exc:
        raise ArbitrationError(f"JEV request failed: {exc}") from exc


def _usage(raw: dict[str, Any], config: StudyConfig) -> tuple[int | None, int | None, float | None]:
    usage = raw.get("usage", {})
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    return input_tokens, output_tokens, config.cost(config.jev_model, input_tokens, output_tokens)


def _parse_choice(raw: dict[str, Any], name: str, allowed: set[str]) -> tuple[str, float, dict[str, float]]:
    try:
        answer = raw["answers"][name]
        selected = answer["choice"]
        probabilities = answer["probabilities"]
        if selected not in allowed or set(probabilities) != allowed:
            raise ValueError(f"{name} keys do not match allowed choices")
        return selected, answer["confidence"], probabilities
    except (KeyError, TypeError, ValueError) as exc:
        raise ArbitrationError(f"Invalid JEV {name} response: {exc}", raw) from exc


async def answer_alone(question: Question, config: StudyConfig) -> Arbitration:
    labels = [chr(ord("A") + index) for index in range(len(question.choices))]
    criteria = {label: {"answer_text": text} for label, text in zip(labels, question.choices, strict=True)}
    payload = {
        "model": config.jev_model,
        "state": {"question": question.question, "choices": criteria},
        "questions": {"best_answer": {
            "type": "choice",
            "instructions": "Answer the question directly. Select the answer most likely to be objectively correct.",
            "criteria": criteria,
        }},
    }
    raw, latency = await _post(payload, config)
    selected, confidence, probabilities = _parse_choice(raw, "best_answer", set(labels))
    input_tokens, output_tokens, cost = _usage(raw, config)
    return Arbitration(
        selected_candidate_id=selected, selected_answer_label=selected,
        confidence=confidence, probabilities=probabilities,
        resolved_model=raw.get("model"), latency_ms=latency,
        input_tokens=input_tokens, output_tokens=output_tokens,
        estimated_cost_usd=cost, raw_response=raw,
    )


async def arbitrate(question: Question, positions: list[ProviderPosition],
                    config: StudyConfig) -> Arbitration:
    options = candidates(question, positions, config.arbitration_seed)
    if len(options) == 1:
        only = options[0]
        return Arbitration(
            selected_candidate_id=only.candidate_id,
            selected_answer_label=only.answer_label,
            confidence=1.0, probabilities={only.candidate_id: 1.0},
            resolved_model="unanimous-pass-through", latency_ms=0,
            input_tokens=0, output_tokens=0, estimated_cost_usd=0,
            raw_response={"unanimous_pass_through": True},
        )
    criteria = {
        option.candidate_id: {
            "answer_label": option.answer_label,
            "answer_text": question.choices[ord(option.answer_label) - ord("A")],
            "anonymous_support": option.support,
        }
        for option in options
    }
    payload = {
        "model": config.jev_model,
        "state": public_jev_state(question, options),
        "questions": {"best_answer": {
            "type": "choice",
            "instructions": (
                "Select only from the supplied candidates. Judge objective correctness from "
                "the question and anonymous evidence; do not defer mechanically to vote count."
            ),
            "criteria": criteria,
        }},
    }
    raw, latency = await _post(payload, config)
    by_id = {option.candidate_id: option for option in options}
    selected, confidence, probabilities = _parse_choice(raw, "best_answer", set(by_id))
    input_tokens, output_tokens, cost = _usage(raw, config)
    return Arbitration(
        selected_candidate_id=selected,
        selected_answer_label=by_id[selected].answer_label,
        confidence=confidence, probabilities=probabilities,
        resolved_model=raw.get("model"), latency_ms=latency,
        input_tokens=input_tokens, output_tokens=output_tokens,
        estimated_cost_usd=cost, raw_response=raw,
    )


async def assess_delphi(question: Question, positions: list[ProviderPosition],
                         config: StudyConfig) -> DelphiAssessment:
    """Select the current best candidate and decide whether one review round is warranted."""
    options = candidates(question, positions, config.arbitration_seed)
    candidate_criteria = {
        option.candidate_id: {
            "answer_label": option.answer_label,
            "answer_text": question.choices[ord(option.answer_label) - ord("A")],
            "anonymous_support": option.support,
        }
        for option in options
    }
    action_criteria = {
        "stop": {
            "meaning": "The available evidence is sufficiently consistent and credible to finalize now."
        },
        "reconsider": {
            "meaning": (
                "A single independent reconsideration round could realistically correct or resolve "
                "a weak, conflicting, or poorly supported answer."
            )
        },
    }
    payload = {
        "model": config.jev_model,
        "state": public_jev_state(question, options),
        "questions": {
            "best_answer": {
                "type": "choice",
                "instructions": "Select the currently strongest supplied candidate.",
                "criteria": candidate_criteria,
            },
            "next_action": {
                "type": "choice",
                "instructions": (
                    "Decide whether consensus is sufficient or whether exactly one further review "
                    "round is warranted. Unanimity alone is not proof of correctness."
                ),
                "criteria": action_criteria,
            },
        },
    }
    raw, latency = await _post(payload, config)
    by_id = {option.candidate_id: option for option in options}
    selected, answer_confidence, answer_probabilities = _parse_choice(
        raw, "best_answer", set(by_id)
    )
    action, action_confidence, action_probabilities = _parse_choice(
        raw, "next_action", set(action_criteria)
    )
    input_tokens, output_tokens, cost = _usage(raw, config)
    return DelphiAssessment(
        action=action, selected_candidate_id=selected,
        selected_answer_label=by_id[selected].answer_label,
        answer_confidence=answer_confidence,
        answer_probabilities=answer_probabilities,
        action_confidence=action_confidence,
        action_probabilities=action_probabilities,
        resolved_model=raw.get("model"), latency_ms=latency,
        input_tokens=input_tokens, output_tokens=output_tokens,
        estimated_cost_usd=cost, raw_response=raw,
    )
