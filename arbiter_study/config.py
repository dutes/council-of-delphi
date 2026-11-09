from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(slots=True)
class StudyConfig:
    openai_model: str = "gpt-4.1-mini-2025-04-14"
    anthropic_model: str = "claude-haiku-4-5-20251001"
    mistral_model: str = "ministral-14b-2512"
    jev_model: str = "jev-latest"
    crowd_size: int = 3
    temperature: float = 0.7
    max_output_tokens: int = 2048
    timeout_seconds: float = 60.0
    max_retries: int = 2
    crowd_seed: int = 20260923
    arbitration_seed: int = 20260924
    tie_seed: int = 20260925
    pricing: dict[str, tuple[float, float]] = field(default_factory=lambda: {
        "gpt-4.1-mini-2025-04-14": (0.40, 1.60),
        "claude-haiku-4-5-20251001": (1.00, 5.00),
        "ministral-14b-2512": (0.20, 0.20),
        "jev-latest": (0.042, 0.0),
    })

    def key(self, provider: str) -> str:
        name = {
            "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
            "mistral": "MISTRAL_API_KEY", "jev": "TYPESAFE_API_KEY",
        }[provider]
        value = os.getenv(name)
        if not value:
            raise RuntimeError(f"Missing {name}")
        return value

    def model(self, provider: str) -> str:
        return {
            "openai": self.openai_model,
            "anthropic": self.anthropic_model,
            "mistral": self.mistral_model,
        }[provider]

    def cost(self, model: str, input_tokens: int | None,
             output_tokens: int | None) -> float | None:
        if input_tokens is None or output_tokens is None or model not in self.pricing:
            return None
        rates = self.pricing[model]
        return (input_tokens * rates[0] + output_tokens * rates[1]) / 1_000_000
