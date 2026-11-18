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


def get(url: str, headers: dict) -> dict:
    response = httpx.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def main() -> None:
    load_env_file()
    sections = []
    if os.getenv("OPENAI_API_KEY"):
        data = get("https://api.openai.com/v1/models",
                   {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
        ids = sorted(m["id"] for m in data["data"] if m["id"].startswith(("gpt-", "chatgpt-")))
        sections.append(("OpenAI (chat models)", ids))
    if os.getenv("ANTHROPIC_API_KEY"):
        data = get("https://api.anthropic.com/v1/models?limit=100",
                   {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"})
        sections.append(("Anthropic", [f"{m['id']}  ({m.get('display_name', '')})" for m in data["data"]]))
    if os.getenv("MISTRAL_API_KEY"):
        data = get("https://api.mistral.ai/v1/models",
                   {"Authorization": f"Bearer {os.environ['MISTRAL_API_KEY']}"})
        rows = []
        for m in sorted(data["data"], key=lambda m: m["id"]):
            caps = m.get("capabilities") or {}
            if not caps.get("completion_chat"):
                continue
            rows.append(f"{m['id']}  reasoning={caps.get('reasoning', 'not reported')}")
        sections.append(("Mistral (chat models)", rows))
    for title, rows in sections:
        print(f"\n{title}")
        for row in rows:
            print(f"  {row}")
    if not sections:
        print("No API keys found in the environment or .env")


if __name__ == "__main__":
    main()
