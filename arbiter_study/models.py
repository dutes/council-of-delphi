from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Question(BaseModel):
    id: str
    question: str
    choices: list[str]
    correct_label: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelAnswer(BaseModel):
    member_id: str
    provider: str
    stage: Literal["initial", "reconsideration"] = "initial"
    sample_index: int = Field(ge=1)
    requested_model: str
    resolved_model: str | None = None
    answer_label: str
    confidence: float = Field(ge=0, le=1)
    rationale: str
    evidence: list[str] = Field(default_factory=list)
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    raw_response: dict[str, Any]
    usage: dict[str, Any] = Field(default_factory=dict)


class ProviderPosition(BaseModel):
    position_id: str
    provider: str
    stage: Literal["initial", "reconsideration"]
    answer_label: str
    label_counts: dict[str, int]
    samples: list[dict[str, Any]]


class Candidate(BaseModel):
    candidate_id: str
    answer_label: str
    support: list[dict[str, Any]]


class Arbitration(BaseModel):
    selected_candidate_id: str
    selected_answer_label: str
    confidence: float
    probabilities: dict[str, float]
    resolved_model: str | None = None
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    raw_response: dict[str, Any]


class DelphiAssessment(BaseModel):
    action: Literal["stop", "reconsider"]
    selected_candidate_id: str
    selected_answer_label: str
    answer_confidence: float
    answer_probabilities: dict[str, float]
    action_confidence: float
    action_probabilities: dict[str, float]
    resolved_model: str | None = None
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    raw_response: dict[str, Any]
