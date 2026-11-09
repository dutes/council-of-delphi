from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ConflictCandidate(BaseModel):
    candidate_id: str
    claim: str
    provenance: str
    relation: str
    subject: str
    object: str
    quality_class: str
    is_correct: bool

    @property
    def public_text(self) -> str:
        return f"Claim: {self.claim} Provenance: {self.provenance}"


class ConflictStage(BaseModel):
    stage_index: int
    relation: str
    subject: str
    candidates: list[ConflictCandidate]


class ConflictQuestion(BaseModel):
    id: str
    question: str
    choices: list[str]
    correct_label: str
    stages: list[ConflictStage]


class ArbiterDecision(BaseModel):
    arbiter: str
    stage_index: int
    selected_candidate_id: str
    confidence: float | None = None
    probabilities: dict[str, float] | None = None
    rationale: str | None = None
    resolved_model: str | None = None
    latency_ms: float = 0.0
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    raw_response: dict[str, Any] | None = None

