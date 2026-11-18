"""List the models your API keys can reach, to pick the follow-up candidates.

    python tools/list_models.py

Read-only: it calls each provider's model-list endpoint and nothing else, so it
costs nothing. For Mistral it also shows whether a model reports reasoning,
because the protocol only allows models with no hidden reasoning mode.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_study import load_env_file  # noqa: E402

KEYS = {"OpenAI": "OPENAI_API_KEY", "Anthropic": "ANTHROPIC_API_KEY", "Mistral": "MISTRAL_API_KEY"}
# A key already set in Windows wins over the .env file, so note where each one came from.
PRESET = {name for name in KEYS.values() if os.getenv(name)}


def get(url: str, headers: dict) -> dict:
    response = httpx.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def openai(key: str) -> list[str]:
    data = get("https://api.openai.com/v1/models", {"Authorization": f"Bearer {key}"})
    return sorted(m["id"] for m in data["data"] if m["id"].startswith(("gpt-", "chatgpt-")))


def anthropic(key: str) -> list[str]:
    data = get("https://api.anthropic.com/v1/models?limit=100",
               {"x-api-key": key, "anthropic-version": "2023-06-01"})
    return [f"{m['id']}  ({m.get('display_name', '')})" for m in data["data"]]


def mistral(key: str) -> list[str]:
    data = get("https://api.mistral.ai/v1/models", {"Authorization": f"Bearer {key}"})
    rows = []
    for m in sorted(data["data"], key=lambda m: m["id"]):
        caps = m.get("capabilities") or {}
        if caps.get("completion_chat"):
            rows.append(f"{m['id']}  reasoning={caps.get('reasoning', 'not reported')}")
    return rows


def main() -> None:
    load_env_file()
    listers = {"OpenAI": openai, "Anthropic": anthropic, "Mistral": mistral}
    for provider, name in KEYS.items():
        key = os.getenv(name)
        if not key:
            print(f"\n{provider}: no {name} found")
            continue
        try:
            rows = listers[provider](key)
        except httpx.HTTPError as error:
            where = "your Windows environment (it overrides .env)" if name in PRESET else ".env"
            print(f"\n{provider}: FAILED, {error}\n  The {name} in use came from {where}.")
            continue
        print(f"\n{provider}")
        for row in rows:
            print(f"  {row}")


if __name__ == "__main__":
    main()
