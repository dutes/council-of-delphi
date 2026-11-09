"""Shared execution logic for the conflicting-evidence arbiter ablation."""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

from arbiter_study.config import StudyConfig
from conflict_ablation.arbiters import hash_tie, jev_classify, keyword_rule, openai_classify
from conflict_ablation.models import ArbiterDecision, ConflictQuestion
from conflict_ablation.store import ConflictStore


ARBITERS = ("hash_tie", "keyword_rule", "openai", "jev")


def hash_files(files: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for name in files:
        digest.update(name.encode()+b"\0")
        digest.update(Path(name).read_bytes()+b"\0")
    return digest.hexdigest()


def load_frozen(path: Path, implementation_files: tuple[str, ...]):
    raw = path.read_bytes()
    spec = json.loads(raw)
    if tuple(spec["implementation_files"]) != implementation_files:
        raise RuntimeError("Implementation file list differs from freeze")
    if spec["implementation_sha256"] != hash_files(implementation_files):
        raise RuntimeError("Implementation differs from freeze")
    dataset = Path(spec["dataset_path"])
    if hashlib.sha256(dataset.read_bytes()).hexdigest() != spec["dataset_sha256"]:
        raise RuntimeError("Dataset differs from freeze")
    questions = [ConflictQuestion.model_validate_json(line) for line in dataset.read_text(
        encoding="utf-8").splitlines() if line]
    if len(questions) != spec["question_count"]:
        raise RuntimeError("Question count differs from freeze")
    config = StudyConfig(
        openai_model=spec["models"]["openai"], jev_model=spec["models"]["jev"],
        temperature=0, max_output_tokens=spec["max_output_tokens"],
        pricing={key: tuple(value) for key, value in spec["pricing"].items()},
    )
    return spec, config, questions, hashlib.sha256(raw).hexdigest()


async def run_question(question: ConflictQuestion, config: StudyConfig, store: ConflictStore,
                       tie_seed: int, max_attempts: int) -> None:
    for stage in question.stages:
        for local in (hash_tie(question, stage, tie_seed), keyword_rule(stage)):
            if store.decision(question.id, stage.stage_index, local.arbiter) is None:
                store.save(question.id, local)
        calls = []
        names = []
        if (store.decision(question.id, stage.stage_index, "openai") is None and
                store.attempts(question.id, stage.stage_index, "openai") < max_attempts):
            names.append("openai"); calls.append(openai_classify(question, stage, config))
        if (store.decision(question.id, stage.stage_index, "jev") is None and
                store.attempts(question.id, stage.stage_index, "jev") < max_attempts):
            names.append("jev"); calls.append(jev_classify(question, stage, config))
        outcomes = await asyncio.gather(*calls, return_exceptions=True)
        for name, outcome in zip(names, outcomes, strict=True):
            if isinstance(outcome, ArbiterDecision):
                store.save(question.id, outcome)
            else:
                store.failure(question.id, stage.stage_index, name, outcome)


async def execute(spec: dict, config: StudyConfig, questions: list[ConflictQuestion],
                  freeze_hash: str, db_path: str, progress_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with ConflictStore(db_path, freeze_hash) as store:
        for start in range(0, len(questions), spec["concurrency"]):
            batch = questions[start:start+spec["concurrency"]]
            await asyncio.gather(*(run_question(
                question, config, store, spec["tie_seed"], spec["max_attempts_per_decision"]
            ) for question in batch))
            Path(progress_path).write_text(
                "CONFLICTING-EVIDENCE ABLATION - OPERATIONS ONLY\n"
                f"Freeze: {spec['freeze_id']}\nComplete: {store.complete_count()}/{len(questions)}\n"
                f"Recorded spend: ${store.cost():.4f}\nFailed calls: {store.failures()}\n"
                "No interim accuracy displayed.\n", encoding="utf-8")
            print(f"Operations complete through {min(start+len(batch),len(questions))}/{len(questions)}")

