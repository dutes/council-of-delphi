from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx
from pydantic import BaseModel, Field

from arbiter_study.config import StudyConfig
from arbiter_study.models import ModelAnswer, Question


class ProviderPayload(BaseModel):
    answer_label: str
    confidence: float = Field(ge=0, le=1)
    rationale: str
    evidence: list[str] = Field(default_factory=list)


class ProviderError(RuntimeError):
    def __init__(self, message: str, raw: dict[str, Any] | None = None):
        super().__init__(message)
        self.raw = raw


def output_schema(question: Question) -> dict[str, Any]:
    labels = [chr(ord("A") + index) for index in range(len(question.choices))]
    return {
        "type": "object",
        "properties": {
            "answer_label": {"type": "string", "enum": labels},
            "confidence": {"type": "number"},
            "rationale": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["answer_label", "confidence", "rationale", "evidence"],
        "additionalProperties": False,
    }


def prompts(question: Question, stage: str, context: dict[str, Any] | None = None) -> tuple[str, str]:
    system = (
        "Return only the requested JSON. Choose exactly one answer label. Give a concise "
        "visible justification, not hidden chain-of-thought. Judge independently and do not "
        "defer to a majority merely because it is a majority."
    )
    choices = "\n".join(
        f"{chr(ord('A') + index)}: {choice}"
        for index, choice in enumerate(question.choices)
    )
    user = f"{question.question}\nChoices:\n{choices}"
    if stage == "reconsideration":
        if context is None:
            raise ValueError("Reconsideration requires anonymized council context")
        user += (
            "\n\nA neutral arbiter found that another independent review was warranted. "
            "Reconsider the question using the anonymized initial positions below. They may "
            "all be wrong. Return your own revised answer.\n"
            + json.dumps(context, ensure_ascii=False, separators=(",", ":"))
        )
    return system, user


async def post(config: StudyConfig, provider: str, url: str, *, headers: dict,
               payload: dict, params: dict | None = None) -> tuple[dict, float]:
    started = time.perf_counter()
    last: Exception | None = None
    async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
        for attempt in range(config.max_retries + 1):
            try:
                response = await client.post(url, headers=headers, json=payload, params=params)
                response.raise_for_status()
                return response.json(), (time.perf_counter() - started) * 1000
            except (httpx.HTTPError, ValueError) as exc:
                last = exc
                status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
                if attempt == config.max_retries or (status is not None and status < 500 and status != 429):
                    break
                await asyncio.sleep(0.5 * (2 ** attempt))
    if isinstance(last, httpx.HTTPStatusError):
        detail = last.response.text[:1000].replace("\r", " ").replace("\n", " ")
        message = f"HTTP {last.response.status_code}: {detail}"
    elif isinstance(last, httpx.RequestError):
        message = type(last).__name__
    else:
        message = type(last).__name__ if last is not None else "unknown error"
    raise ProviderError(f"{provider} request failed: {message}")


def normalise(member_id: str, provider: str, stage: str, sample_index: int,
              model: str, question: Question, content: str, raw: dict,
              usage: dict, latency: float, config: StudyConfig,
              resolved_model: str | None) -> ModelAnswer:
    try:
        parsed = ProviderPayload.model_validate_json(content)
    except Exception as exc:
        raise ProviderError(f"{provider} returned invalid structured output: {exc}", raw) from exc
    labels = [chr(ord("A") + index) for index in range(len(question.choices))]
    if parsed.answer_label not in labels:
        raise ProviderError(f"{provider} returned invalid label", raw)
    input_tokens = usage.get("prompt_tokens", usage.get("input_tokens", usage.get("promptTokenCount")))
    output_tokens = usage.get("completion_tokens", usage.get("output_tokens", usage.get("candidatesTokenCount")))
    return ModelAnswer(
        member_id=member_id, provider=provider, stage=stage, sample_index=sample_index,
        requested_model=model, resolved_model=resolved_model,
        answer_label=parsed.answer_label, confidence=parsed.confidence,
        rationale=parsed.rationale, evidence=parsed.evidence, latency_ms=latency,
        input_tokens=input_tokens, output_tokens=output_tokens,
        estimated_cost_usd=config.cost(model, input_tokens, output_tokens),
        raw_response=raw, usage=usage,
    )


async def ask_openai(question: Question, config: StudyConfig, *, member_id: str = "openai-initial-1",
                     stage: str = "initial", sample_index: int = 1,
                     context: dict[str, Any] | None = None) -> ModelAnswer:
    system, user = prompts(question, stage, context)
    raw, latency = await post(
        config, "openai", "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.key('openai')}", "Content-Type": "application/json"},
        payload={
            "model": config.openai_model, "temperature": config.temperature,
            "max_completion_tokens": config.max_output_tokens,
            "response_format": {"type": "json_schema", "json_schema": {
                "name": f"{stage}_answer", "strict": True, "schema": output_schema(question),
            }},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        },
    )
    usage = raw.get("usage", {})
    reasoning = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
    if reasoning:
        raise ProviderError("OpenAI emitted hidden reasoning tokens", raw)
    try:
        content = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError("Unexpected OpenAI response", raw) from exc
    return normalise(member_id, "openai", stage, sample_index, config.openai_model,
                     question, content, raw, usage, latency, config, raw.get("model"))


async def ask_anthropic(question: Question, config: StudyConfig, *, member_id: str = "anthropic-initial-1",
                        stage: str = "initial", sample_index: int = 1,
                        context: dict[str, Any] | None = None) -> ModelAnswer:
    system, user = prompts(question, stage, context)
    raw, latency = await post(
        config, "anthropic", "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": config.key("anthropic"), "anthropic-version": "2023-06-01",
                 "Content-Type": "application/json"},
        payload={
            "model": config.anthropic_model, "temperature": config.temperature,
            "max_tokens": config.max_output_tokens, "system": system,
            "messages": [{"role": "user", "content": user}],
            "output_config": {"format": {"type": "json_schema", "schema": output_schema(question)}},
        },
    )
    blocks = raw.get("content", [])
    if any(block.get("type") in {"thinking", "redacted_thinking"} for block in blocks):
        raise ProviderError("Anthropic emitted a thinking block", raw)
    try:
        content = next(block["text"] for block in blocks if block.get("type") == "text")
    except (KeyError, StopIteration, TypeError) as exc:
        raise ProviderError("Unexpected Anthropic response", raw) from exc
    return normalise(member_id, "anthropic", stage, sample_index, config.anthropic_model,
                     question, content, raw, raw.get("usage", {}), latency, config, raw.get("model"))


async def ask_mistral(question: Question, config: StudyConfig, *, member_id: str = "mistral-initial-1",
                      stage: str = "initial", sample_index: int = 1,
                      context: dict[str, Any] | None = None) -> ModelAnswer:
    system, user = prompts(question, stage, context)
    raw, latency = await post(
        config, "mistral", "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.key('mistral')}",
                 "Content-Type": "application/json"},
        payload={
            "model": config.mistral_model, "temperature": config.temperature,
            "max_tokens": config.max_output_tokens,
            "response_format": {"type": "json_schema", "json_schema": {
                "name": f"{stage}_answer", "schema": output_schema(question),
                "strict": True,
            }},
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
        },
    )
    usage = raw.get("usage", {})
    try:
        message = raw["choices"][0]["message"]
        if message.get("reasoning") or message.get("reasoning_content"):
            raise ProviderError("Mistral emitted a reasoning field", raw)
        content = message["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError("Unexpected Mistral response", raw) from exc
    return normalise(member_id, "mistral", stage, sample_index, config.mistral_model,
                     question, content, raw, usage, latency, config, raw.get("model"))


PROVIDER_FUNCTIONS = {
    "openai": ask_openai,
    "anthropic": ask_anthropic,
    "mistral": ask_mistral,
}


async def ask_provider(provider: str, question: Question, config: StudyConfig, *,
                       member_id: str, stage: str, sample_index: int,
                       context: dict[str, Any] | None = None) -> ModelAnswer:
    return await PROVIDER_FUNCTIONS[provider](
        question, config, member_id=member_id, stage=stage,
        sample_index=sample_index, context=context,
    )
