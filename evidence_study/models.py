from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvidenceFact(BaseModel):
    evidence_id: str
    text: str
    partition: str
    is_support: bool = False


class EvidenceQuestion(BaseModel):
    id: str
    question: str
    choices: list[str]
    correct_label: str
    facts: list[EvidenceFact]
    support_ids: list[str]
    metadata: dict[str, Any] = Field(default_factory=dict)

    def facts_for(self, provider: str) -> list[EvidenceFact]:
        return [fact for fact in self.facts if fact.partition == provider]


class EvidenceDecision(BaseModel):
    condition: str
    selected_answer_label: str
    confidence: float
    probabilities: dict[str, float]
    cited_evidence_ids: list[str] = Field(default_factory=list)
    resolved_model: str | None = None
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    raw_response: dict[str, Any]
