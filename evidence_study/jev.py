from __future__ import annotations

import os
import re
import time
import hashlib
from typing import Any

import httpx

from arbiter_study.config import StudyConfig
from arbiter_study.models import ModelAnswer
from evidence_study.models import EvidenceDecision, EvidenceQuestion


class EvidenceJEVError(RuntimeError):
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
        raise EvidenceJEVError(f"JEV request failed: {type(exc).__name__}") from exc


def _choice(raw: dict[str, Any], name: str, allowed: set[str]):
    try:
        answer = raw["answers"][name]
        if answer["choice"] not in allowed or set(answer["probabilities"]) != allowed:
            raise ValueError("choice keys differ from criteria")
        return answer["choice"], answer["confidence"], answer["probabilities"]
    except (KeyError, TypeError, ValueError) as exc:
        raise EvidenceJEVError(f"Invalid JEV response for {name}: {exc}", raw) from exc


def _answer_criteria(question: EvidenceQuestion) -> dict[str, dict[str, str]]:
    return {
        chr(ord("A") + i): {"answer_text": text}
        for i, text in enumerate(question.choices)
    }


async def decide(question: EvidenceQuestion, config: StudyConfig, condition: str,
                 reports: list[ModelAnswer] | None = None) -> EvidenceDecision:
    answer_criteria = _answer_criteria(question)
    state: dict[str, Any] = {
        "question": question.question,
        "choices": answer_criteria,
    }
    evidence_criteria: dict[str, dict[str, Any]] = {}
    instructions = "Select the objectively correct answer."

    if condition == "question_only":
        instructions += " No evidence is available; do not assume unstated entity relationships."
    elif condition == "raw_evidence":
        evidence_criteria = {
            fact.evidence_id: {"reported_claims": [fact.text]}
            for fact in question.facts
        }
        state["evidence"] = [
            {"evidence_id": fact.evidence_id, "text": fact.text}
            for fact in question.facts
        ]
        instructions += " Use the supplied evidence and identify the three links that form the proof."
    elif condition == "report_synthesis":
        if reports is None or len(reports) != 3:
            raise ValueError("Report synthesis requires three specialist reports")
        public_reports = []
        claims: dict[str, list[str]] = {}
        anonymous_reports = sorted(
            reports,
            key=lambda report: hashlib.sha256(
                f"{question.id}:{report.member_id}".encode()
            ).hexdigest(),
        )
        for index, report in enumerate(anonymous_reports, start=1):
            public_reports.append({
                "report_id": f"report-{index}",
                "answer_label": report.answer_label,
                "confidence": report.confidence,
                "rationale": report.rationale,
                "reported_evidence": report.evidence,
            })
            for item in report.evidence:
                match = re.match(r"\s*(E\d{2})\s*:\s*(.+)", item, flags=re.S)
                if match:
                    claims.setdefault(match.group(1), []).append(match.group(2).strip())
        evidence_criteria = {
            evidence_id: {"reported_claims": statements}
            for evidence_id, statements in sorted(claims.items())
        }
        state["anonymous_specialist_reports"] = public_reports
        instructions += (
            " Synthesize the anonymous reports rather than following their vote mechanically. "
            "Identify the three reported evidence links that form the proof."
        )
    else:
        raise ValueError(f"Unknown condition {condition}")

    questions: dict[str, Any] = {
        "best_answer": {
            "type": "choice", "instructions": instructions,
            "criteria": answer_criteria,
        }
    }
    if evidence_criteria:
        link_criteria = dict(evidence_criteria)
        link_criteria["none"] = {"reported_claims": ["No defensible evidence link is available."]}
        for index in range(1, 4):
            questions[f"proof_link_{index}"] = {
                "type": "choice",
                "instructions": (
                    "Select one evidence ID that belongs in the three-link proof. "
                    "Choose none only if no defensible link is available."
                ),
                "criteria": link_criteria,
            }

    raw, latency = await _post({
        "model": config.jev_model, "state": state, "questions": questions,
    }, config)
    selected, confidence, probabilities = _choice(
        raw, "best_answer", set(answer_criteria)
    )
    citations = []
    if evidence_criteria:
        allowed = set(evidence_criteria) | {"none"}
        for index in range(1, 4):
            citation, _, _ = _choice(raw, f"proof_link_{index}", allowed)
            if citation != "none" and citation not in citations:
                citations.append(citation)
    usage = raw.get("usage", {})
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    return EvidenceDecision(
        condition=condition, selected_answer_label=selected,
        confidence=confidence, probabilities=probabilities,
        cited_evidence_ids=citations, resolved_model=raw.get("model"),
        latency_ms=latency, input_tokens=input_tokens, output_tokens=output_tokens,
        estimated_cost_usd=config.cost(config.jev_model, input_tokens, output_tokens),
        raw_response=raw,
    )
