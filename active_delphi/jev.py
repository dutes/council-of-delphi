from __future__ import annotations

from typing import Iterable

from arbiter_study.config import StudyConfig
from evidence_study.jev import _choice, _post
from active_delphi.models import ActiveFact, ActiveQuestion, JEVAction


async def classify_next_action(
    question: ActiveQuestion,
    config: StudyConfig,
    *,
    stage_index: int,
    attempt: int,
    subject: str,
    relation: str,
    candidates: Iterable[ActiveFact],
    accepted_path: list[ActiveFact],
) -> JEVAction:
    unique = {fact.evidence_id: fact for fact in candidates}
    criteria = {
        f"accept_{evidence_id}": {
            "action": "Accept this evidence and advance to the next fixed retrieval stage.",
            "candidate_claim": fact.text,
        }
        for evidence_id, fact in sorted(unique.items())
    }
    criteria.update({
        "retry": {
            "action": "No candidate directly answers the requested relationship; repeat this targeted retrieval once."
        },
        "halt_unresolved": {
            "action": "The candidates are contradictory or unusable; halt without an answer."
        },
    })
    state = {
        "original_question": question.question,
        "requested_relationship": relation,
        "requested_subject": subject,
        "accepted_path": [
            {"evidence_id": fact.evidence_id, "claim": fact.text} for fact in accepted_path
        ],
        "candidate_evidence": [
            {"evidence_id": fact.evidence_id, "claim": fact.text}
            for fact in sorted(unique.values(), key=lambda item: item.evidence_id)
        ],
    }
    raw, latency = await _post({
        "model": config.jev_model,
        "state": state,
        "questions": {
            "next_action": {
                "type": "choice",
                "instructions": (
                    "Act only as a classifier. Select accept_E## only when that claim directly states "
                    "the requested relationship for the exact requested subject. Do not infer a missing "
                    "link. Select retry when no such candidate is present. Select halt_unresolved for "
                    "conflicting or malformed candidates."
                ),
                "criteria": criteria,
            }
        },
    }, config)
    selected, confidence, probabilities = _choice(raw, "next_action", set(criteria))
    accepted_id = selected.removeprefix("accept_") if selected.startswith("accept_") else None
    usage = raw.get("usage", {})
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    return JEVAction(
        stage_index=stage_index, attempt=attempt, subject=subject, relation=relation,
        action=selected, confidence=confidence, probabilities=probabilities,
        candidate_ids=sorted(unique), accepted_evidence_id=accepted_id,
        resolved_model=raw.get("model"), latency_ms=latency,
        input_tokens=input_tokens, output_tokens=output_tokens,
        estimated_cost_usd=config.cost(config.jev_model, input_tokens, output_tokens),
        raw_response=raw,
    )

