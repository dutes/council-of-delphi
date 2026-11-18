"""Loading and validating the follow-up study configuration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from arbiter_study.config import StudyConfig
from arbiter_study.models import Question


ARMS = ("small", "matched")
PROVIDERS = ("openai", "anthropic", "mistral")

# Every file whose content can change what the follow-up run does or how it's analysed.
# The first study's modules are included because the follow-up reuses them.
IMPLEMENTATION_FILES = (
    "arbiter_study/models.py", "arbiter_study/core.py", "arbiter_study/config.py",
    "arbiter_study/providers.py", "arbiter_study/jev.py",
    "followup_study/__init__.py", "followup_study/spec.py", "followup_study/store.py",
    "followup_study/seat.py", "followup_study/pipeline.py",
    "run_followup.py", "analyze_followup.py", "docs/FOLLOWUP_PROTOCOL.md",
)


def normalised(data: bytes) -> bytes:
    """Windows checkouts may turn LF into CRLF; hash the same content either way."""
    return data.replace(b"\r\n", b"\n")


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(normalised(Path(path).read_bytes())).hexdigest()


def implementation_hash(root: Path = Path(".")) -> str:
    digest = hashlib.sha256()
    for name in IMPLEMENTATION_FILES:
        digest.update(name.encode() + b"\0")
        digest.update(normalised((root / name).read_bytes()) + b"\0")
    return digest.hexdigest()


def load_questions(path: str | Path, expected_sha: str | None = None,
                   expected_count: int | None = None) -> list[Question]:
    path = Path(path)
    if expected_sha is not None and sha256_file(path) != expected_sha:
        raise RuntimeError(f"{path} differs from the freeze")
    questions = [Question.model_validate_json(line)
                 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if expected_count is not None and len(questions) != expected_count:
        raise RuntimeError(f"{path} has {len(questions)} questions, expected {expected_count}")
    return questions


def load_spec(path: str | Path) -> tuple[dict[str, Any], str]:
    raw = normalised(Path(path).read_bytes())
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def is_frozen(spec: dict[str, Any]) -> bool:
    return spec.get("status") == "frozen"


def require_frozen(spec: dict[str, Any], root: Path = Path(".")) -> None:
    """Refuse to run or analyse anything that isn't exactly what was frozen."""
    if not is_frozen(spec):
        raise RuntimeError("The follow-up study isn't frozen yet. Run tools/freeze_followup.py first.")
    if tuple(spec["implementation_files"]) != IMPLEMENTATION_FILES:
        raise RuntimeError("Implementation file list differs from the freeze")
    if implementation_hash(root) != spec["implementation_sha256"]:
        raise RuntimeError("Follow-up implementation differs from the freeze")
    missing = [arm for arm in ARMS for provider in PROVIDERS if not spec["arms"][arm].get(provider)]
    if missing or spec.get("max_recorded_cost_usd") is None:
        raise RuntimeError("Frozen config is incomplete")


def arm_config(spec: dict[str, Any], arm: str) -> StudyConfig:
    models = spec["arms"][arm]
    if not all(models.get(provider) for provider in PROVIDERS):
        raise RuntimeError(f"The {arm} council isn't chosen yet")
    return StudyConfig(
        openai_model=models["openai"], anthropic_model=models["anthropic"],
        mistral_model=models["mistral"], jev_model=spec["jev_model"],
        crowd_size=spec["crowd_size"], temperature=spec["temperature"],
        max_output_tokens=spec["max_output_tokens"], crowd_seed=spec["crowd_seed"],
        arbitration_seed=spec["arbitration_seed"], tie_seed=spec["tie_seed"],
        pricing={key: tuple(value) for key, value in spec["pricing"].items()},
    )


def single_model_config(spec: dict[str, Any], provider: str, model: str,
                        pricing: dict[str, tuple[float, float]] | None = None) -> StudyConfig:
    """A config that sends one provider's calls to one specific model (used in calibration)."""
    models = {p: spec["arms"]["small"][p] for p in PROVIDERS}
    models[provider] = model
    prices = {key: tuple(value) for key, value in spec["pricing"].items()}
    prices.update(pricing or {})
    return StudyConfig(
        openai_model=models["openai"], anthropic_model=models["anthropic"],
        mistral_model=models["mistral"], jev_model=spec["jev_model"],
        crowd_size=1, temperature=spec["temperature"],
        max_output_tokens=spec["max_output_tokens"], crowd_seed=spec["crowd_seed"],
        arbitration_seed=spec["arbitration_seed"], tie_seed=spec["tie_seed"],
        pricing=prices,
    )
