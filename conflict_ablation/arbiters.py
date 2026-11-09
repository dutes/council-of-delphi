from __future__ import annotations

import hashlib
import json
import time

from pydantic import BaseModel, Field

from arbiter_study.config import StudyConfig
from arbiter_study.providers import ProviderError, post
from conflict_ablation.models import ArbiterDecision, ConflictQuestion, ConflictStage
from evidence_study.jev import _choice, _post


POLICY = (
    "Choose the claim with the strongest auditable provenance. Prefer current, ratified, "
    "authenticated primary or direct records and genuinely independent corroboration. "
    "Discount superseded, withdrawn, preliminary, rejected, draft, derivative, anonymous, "
    "hearsay, inferred, unverified, common-source, or uncorroborated material. Judge provenance, "
    "not candidate order."
)

POSITIVE = ("current controlling", "signed after", "authenticated primary", "responsible custodian",
            "tamper-evident", "directly recording", "independently authenticated", "separate systems",
            "final audited", "explicitly replacing")
NEGATIVE = ("superseded", "not ratified", "secondary", "may not reflect", "anonymous", "no verifiable",
            "inference", "incomplete", "hearsay", "never checked", "same unverified", "uncorroborated",
            "unknown", "preliminary", "withdrawn", "rejected")


def hash_tie(question: ConflictQuestion, stage: ConflictStage, seed: int) -> ArbiterDecision:
    selected = min(stage.candidates, key=lambda candidate: hashlib.sha256(
        f"{seed}:{question.id}:{stage.stage_index}:{candidate.candidate_id}".encode()
    ).hexdigest())
    return ArbiterDecision(arbiter="hash_tie", stage_index=stage.stage_index,
                           selected_candidate_id=selected.candidate_id)


def keyword_rule(stage: ConflictStage) -> ArbiterDecision:
    def score(text: str) -> int:
        lowered = text.lower()
        return 2*sum(term in lowered for term in POSITIVE) - 3*sum(term in lowered for term in NEGATIVE)
    selected = max(stage.candidates, key=lambda candidate: (score(candidate.provenance), candidate.candidate_id))
    return ArbiterDecision(arbiter="keyword_rule", stage_index=stage.stage_index,
                           selected_candidate_id=selected.candidate_id,
                           rationale="Frozen lexical provenance score")


async def jev_classify(question: ConflictQuestion, stage: ConflictStage,
                       config: StudyConfig) -> ArbiterDecision:
    criteria = {candidate.candidate_id: {"evidence_packet": candidate.public_text}
                for candidate in stage.candidates}
    raw, latency = await _post({
        "model": config.jev_model,
        "state": {"question": question.question, "evidence_quality_policy": POLICY,
                  "requested_relation": stage.relation, "requested_subject": stage.subject,
                  "candidate_packets": [{"candidate_id": c.candidate_id, "text": c.public_text}
                                        for c in stage.candidates]},
        "questions": {"best_evidence": {"type": "choice", "instructions": POLICY,
                                         "criteria": criteria}},
    }, config)
    selected, confidence, probabilities = _choice(raw, "best_evidence", set(criteria))
    usage = raw.get("usage", {})
    input_tokens, output_tokens = usage.get("input_tokens"), usage.get("output_tokens")
    return ArbiterDecision(
        arbiter="jev", stage_index=stage.stage_index, selected_candidate_id=selected,
        confidence=confidence, probabilities=probabilities, resolved_model=raw.get("model"),
        latency_ms=latency, input_tokens=input_tokens, output_tokens=output_tokens,
        estimated_cost_usd=config.cost(config.jev_model, input_tokens, output_tokens), raw_response=raw,
    )


class OpenAIChoice(BaseModel):
    selected_candidate_id: str
    confidence: float = Field(ge=0, le=1)
    rationale: str


async def openai_classify(question: ConflictQuestion, stage: ConflictStage,
                          config: StudyConfig) -> ArbiterDecision:
    ids = [candidate.candidate_id for candidate in stage.candidates]
    schema = {"type": "object", "properties": {
        "selected_candidate_id": {"type": "string", "enum": ids},
        "confidence": {"type": "number"}, "rationale": {"type": "string"}},
        "required": ["selected_candidate_id", "confidence", "rationale"],
        "additionalProperties": False}
    user = json.dumps({
        "question": question.question, "policy": POLICY, "relation": stage.relation,
        "subject": stage.subject,
        "candidates": [{"candidate_id": c.candidate_id, "text": c.public_text}
                       for c in stage.candidates],
    }, ensure_ascii=False)
    raw, latency = await post(
        config, "openai", "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.key('openai')}", "Content-Type": "application/json"},
        payload={"model": config.openai_model, "temperature": 0,
                 "max_completion_tokens": config.max_output_tokens,
                 "response_format": {"type": "json_schema", "json_schema": {
                     "name": "evidence_choice", "strict": True, "schema": schema}},
                 "messages": [{"role": "system", "content": "Apply the supplied evidence-quality policy. Return only JSON and no hidden chain-of-thought."},
                              {"role": "user", "content": user}]},
    )
    usage = raw.get("usage", {})
    if ((usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0):
        raise ProviderError("OpenAI classifier emitted hidden reasoning tokens", raw)
    try:
        parsed = OpenAIChoice.model_validate_json(raw["choices"][0]["message"]["content"])
    except Exception as exc:
        raise ProviderError(f"Invalid OpenAI classifier output: {exc}", raw) from exc
    return ArbiterDecision(
        arbiter="openai", stage_index=stage.stage_index,
        selected_candidate_id=parsed.selected_candidate_id, confidence=parsed.confidence,
        rationale=parsed.rationale, resolved_model=raw.get("model"), latency_ms=latency,
        input_tokens=usage.get("prompt_tokens"), output_tokens=usage.get("completion_tokens"),
        estimated_cost_usd=config.cost(config.openai_model, usage.get("prompt_tokens"), usage.get("completion_tokens")),
        raw_response=raw,
    )

