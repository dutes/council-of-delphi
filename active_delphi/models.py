from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ActiveFact(BaseModel):
    evidence_id: str
    text: str
    partition: str
    relation: str
    subject: str
    object: str
    is_support: bool = False


class ActiveQuestion(BaseModel):
    id: str
    question: str
    choices: list[str]
    correct_label: str
    target_artifact: str
    facts: list[ActiveFact]
    support_ids: list[str]
    link_owners: dict[str, str]
    metadata: dict[str, Any] = Field(default_factory=dict)

    def facts_for(self, provider: str) -> list[ActiveFact]:
        return [fact for fact in self.facts if fact.partition == provider]

    def fact(self, evidence_id: str) -> ActiveFact | None:
        return next((fact for fact in self.facts if fact.evidence_id == evidence_id), None)


class JEVAction(BaseModel):
    stage_index: int
    attempt: int
    subject: str
    relation: str
    action: str
    confidence: float
    probabilities: dict[str, float]
    candidate_ids: list[str] = Field(default_factory=list)
    accepted_evidence_id: str | None = None
    resolved_model: str | None = None
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    raw_response: dict[str, Any]


class ActiveOutcome(BaseModel):
    status: str
    selected_answer_label: str | None = None
    accepted_evidence_ids: list[str] = Field(default_factory=list)
    rounds_used: int
    specialist_calls: int
    jev_calls: int

