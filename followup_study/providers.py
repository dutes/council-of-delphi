"""Council model calls for the follow-up, with reasoning switched off.

The first study used only models with no reasoning mode at all. The follow-up
needs a council as strong as JEV, so it also allows models that *can* reason,
with reasoning switched off on every call (docs/FOLLOWUP_PROTOCOL.md,
"Reasoning switched off"):

- OpenAI GPT-5 family: ``reasoning_effort: "none"``
- Mistral Medium and Small: ``reasoning_effort: "none"``
- Anthropic: extended thinking is never requested, as in the first study

Every response is still checked: reasoning tokens, a thinking block or a
reasoning field fails the call, exactly as before. Models that can't reason
get the first study's request unchanged, so the small council is identical.

The prompts, output schema, retries and parsing are the first study's, imported
from arbiter_study.providers without changes.
"""

from __future__ import annotations

from typing import Any

from arbiter_study.config import StudyConfig
from arbiter_study.models import ModelAnswer, Question
from arbiter_study.providers import ProviderError, normalise, output_schema, post, prompts


# Models whose API no longer accepts a temperature ("temperature is deprecated for this
# model"). They're sampled at the provider's fixed default instead of the protocol's 0.7,
# which the freeze record discloses. Every other model gets the protocol temperature.
FIXED_TEMPERATURE = frozenset({"claude-sonnet-5-5", "claude-opus-5-5"})


def temperature(config: StudyConfig, model: str) -> dict[str, Any]:
    return {} if model in FIXED_TEMPERATURE else {"temperature": config.temperature}


def reasoning_off(provider: str, model: str) -> dict[str, Any]:
    """The request fields that switch reasoning off for models that have it."""
    if provider == "openai" and model.startswith("gpt-5"):
        return {"reasoning_effort": "none"}
    if provider == "mistral" and model.startswith(("mistral-medium", "mistral-small")):
        return {"reasoning_effort": "none"}
    return {}


async def ask_openai(question: Question, config: StudyConfig, *, member_id: str, stage: str,
                     sample_index: int, context: dict[str, Any] | None = None) -> ModelAnswer:
    system, user = prompts(question, stage, context)
    model = config.openai_model
    raw, latency = await post(
        config, "openai", "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.key('openai')}", "Content-Type": "application/json"},
        payload={
            "model": model, **temperature(config, model),
            "max_completion_tokens": config.max_output_tokens,
            "response_format": {"type": "json_schema", "json_schema": {
                "name": f"{stage}_answer", "strict": True, "schema": output_schema(question)}},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            **reasoning_off("openai", model),
        },
    )
    usage = raw.get("usage", {})
    if (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"):
        raise ProviderError("OpenAI emitted hidden reasoning tokens", raw)
    try:
        content = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError("Unexpected OpenAI response", raw) from exc
    return normalise(member_id, "openai", stage, sample_index, model, question, content, raw,
                     usage, latency, config, raw.get("model"))


async def ask_anthropic(question: Question, config: StudyConfig, *, member_id: str, stage: str,
                        sample_index: int, context: dict[str, Any] | None = None) -> ModelAnswer:
    system, user = prompts(question, stage, context)
    model = config.anthropic_model
    raw, latency = await post(
        config, "anthropic", "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": config.key("anthropic"), "anthropic-version": "2023-06-01",
                 "Content-Type": "application/json"},
        payload={
            "model": model, **temperature(config, model),
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
    return normalise(member_id, "anthropic", stage, sample_index, model, question, content, raw,
                     raw.get("usage", {}), latency, config, raw.get("model"))


async def ask_mistral(question: Question, config: StudyConfig, *, member_id: str, stage: str,
                      sample_index: int, context: dict[str, Any] | None = None) -> ModelAnswer:
    system, user = prompts(question, stage, context)
    model = config.mistral_model
    raw, latency = await post(
        config, "mistral", "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.key('mistral')}", "Content-Type": "application/json"},
        payload={
            "model": model, **temperature(config, model),
            "max_tokens": config.max_output_tokens,
            "response_format": {"type": "json_schema", "json_schema": {
                "name": f"{stage}_answer", "schema": output_schema(question), "strict": True}},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            **reasoning_off("mistral", model),
        },
    )
    try:
        message = raw["choices"][0]["message"]
        content = message["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError("Unexpected Mistral response", raw) from exc
    # With reasoning on, Mistral returns content as a list of chunks that includes "thinking".
    thinking = isinstance(content, list) and any(
        isinstance(chunk, dict) and chunk.get("type") == "thinking" for chunk in content)
    if thinking or message.get("reasoning") or message.get("reasoning_content"):
        raise ProviderError("Mistral emitted reasoning", raw)
    if not isinstance(content, str):
        raise ProviderError("Unexpected Mistral content format", raw)
    return normalise(member_id, "mistral", stage, sample_index, model, question, content, raw,
                     raw.get("usage", {}), latency, config, raw.get("model"))


PROVIDER_FUNCTIONS = {"openai": ask_openai, "anthropic": ask_anthropic, "mistral": ask_mistral}


async def ask_provider(provider: str, question: Question, config: StudyConfig, *, member_id: str,
                       stage: str, sample_index: int, context: dict[str, Any] | None = None) -> ModelAnswer:
    return await PROVIDER_FUNCTIONS[provider](question, config, member_id=member_id, stage=stage,
                                              sample_index=sample_index, context=context)
