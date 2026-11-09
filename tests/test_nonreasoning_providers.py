import pytest

from arbiter_study.config import StudyConfig
from arbiter_study.models import Question
from arbiter_study.providers import ProviderError, ask_anthropic, ask_mistral, ask_openai
from run_study import load_env_file


QUESTION = Question(id="q", question="2+2?", choices=["3", "4"], correct_label="B")
CONTENT = '{"answer_label":"B","confidence":1,"rationale":"sum","evidence":[]}'


def test_env_loader_accepts_dotenv_and_powershell_assignments(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("TEST_STANDARD_KEY", raising=False)
    monkeypatch.delenv("TEST_POWERSHELL_KEY", raising=False)
    path = tmp_path / ".env"
    path.write_text(
        "TEST_STANDARD_KEY=standard-value\n$env:TEST_POWERSHELL_KEY='powershell-value'\n",
        encoding="utf-8",
    )
    load_env_file(path)
    assert __import__("os").environ["TEST_STANDARD_KEY"] == "standard-value"
    assert __import__("os").environ["TEST_POWERSHELL_KEY"] == "powershell-value"


@pytest.mark.asyncio
async def test_mistral_uses_structured_output_and_rejects_reasoning_field(monkeypatch) -> None:
    monkeypatch.setenv("MISTRAL_API_KEY", "test")
    captured = {}

    async def fake_post(config, provider, url, *, headers, payload, params=None):
        captured["payload"] = payload
        captured["headers"] = headers
        captured["params"] = params
        return ({"choices": [{"message": {"content": CONTENT,
                                             "reasoning_content": "hidden"}}],
                 "usage": {}}, 1.0)

    monkeypatch.setattr("arbiter_study.providers.post", fake_post)
    with pytest.raises(ProviderError, match="reasoning field"):
        await ask_mistral(QUESTION, StudyConfig())
    assert captured["payload"]["temperature"] == StudyConfig().temperature
    assert captured["payload"]["response_format"]["type"] == "json_schema"
    assert captured["payload"]["response_format"]["json_schema"]["schema"]
    assert "reasoning_effort" not in captured["payload"]
    assert captured["headers"]["Authorization"] == "Bearer test"
    assert captured["params"] is None


@pytest.mark.asyncio
async def test_openai_rejects_reasoning_tokens(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    async def fake_post(config, provider, url, *, headers, payload, params=None):
        return ({"choices": [{"message": {"content": CONTENT}}],
                 "usage": {"completion_tokens_details": {"reasoning_tokens": 1}}}, 1.0)

    monkeypatch.setattr("arbiter_study.providers.post", fake_post)
    with pytest.raises(ProviderError, match="reasoning tokens"):
        await ask_openai(QUESTION, StudyConfig())


@pytest.mark.asyncio
async def test_anthropic_omits_thinking_and_rejects_thinking_block(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    captured = {}

    async def fake_post(config, provider, url, *, headers, payload, params=None):
        captured.update(payload)
        return ({"content": [{"type": "thinking", "thinking": "hidden"},
                             {"type": "text", "text": CONTENT}], "usage": {}}, 1.0)

    monkeypatch.setattr("arbiter_study.providers.post", fake_post)
    with pytest.raises(ProviderError, match="thinking block"):
        await ask_anthropic(QUESTION, StudyConfig())
    assert "thinking" not in captured


@pytest.mark.asyncio
async def test_reconsideration_prompt_uses_anonymous_context(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    captured = {}

    async def fake_post(config, provider, url, *, headers, payload, params=None):
        captured.update(payload)
        return ({"choices": [{"message": {"content": CONTENT}}], "usage": {}}, 1.0)

    monkeypatch.setattr("arbiter_study.providers.post", fake_post)
    await ask_openai(
        QUESTION, StudyConfig(), member_id="openai-reconsideration-1",
        stage="reconsideration", sample_index=1,
        context={"candidate_answers": [{"candidate_id": "candidate-1"}]},
    )
    prompt = captured["messages"][1]["content"]
    assert "candidate-1" in prompt
    assert "provider" not in prompt.lower()
