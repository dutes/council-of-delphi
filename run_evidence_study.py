"""Run the frozen evidence-partitioned JEV arbitration study."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path

from arbiter_study.config import StudyConfig
from arbiter_study.models import ModelAnswer, Question
from arbiter_study.providers import ask_provider
from evidence_study.generate import PROVIDERS, generate_question
from evidence_study.jev import decide
from evidence_study.models import EvidenceQuestion
from evidence_study.store import EvidenceStore
from run_study import load_env_file


IMPLEMENTATION_FILES = (
    "evidence_study/models.py", "evidence_study/generate.py", "evidence_study/jev.py",
    "evidence_study/store.py", "run_evidence_study.py", "analyze_evidence_study.py",
    "docs/EVIDENCE_PROTOCOL.md",
)
CONDITIONS = ("question_only", "report_synthesis", "raw_evidence")


def implementation_hash() -> str:
    digest = hashlib.sha256()
    for name in IMPLEMENTATION_FILES:
        digest.update(name.encode() + b"\0")
        digest.update(Path(name).read_bytes() + b"\0")
    return digest.hexdigest()


def load_frozen(path: Path):
    spec = json.loads(path.read_text(encoding="utf-8"))
    if tuple(spec["implementation_files"]) != IMPLEMENTATION_FILES:
        raise RuntimeError("Implementation file list differs from freeze")
    if spec["implementation_sha256"] != implementation_hash():
        raise RuntimeError("Implementation differs from freeze")
    dataset = Path(spec["dataset_path"])
    if hashlib.sha256(dataset.read_bytes()).hexdigest() != spec["dataset_sha256"]:
        raise RuntimeError("Dataset differs from freeze")
    questions = [EvidenceQuestion.model_validate_json(line) for line in dataset.read_text(
        encoding="utf-8"
    ).splitlines() if line]
    if len(questions) != spec["question_count"]:
        raise RuntimeError("Question count differs from freeze")
    config = StudyConfig(
        openai_model=spec["models"]["openai"],
        anthropic_model=spec["models"]["anthropic"],
        mistral_model=spec["models"]["mistral"], jev_model=spec["models"]["jev"],
        temperature=spec["temperature"], max_output_tokens=spec["max_output_tokens"],
        pricing={key: tuple(value) for key, value in spec["pricing"].items()},
    )
    return spec, config, questions, hashlib.sha256(path.read_bytes()).hexdigest()


def specialist_question(question: EvidenceQuestion, provider: str) -> Question:
    evidence = "\n".join(
        f"{fact.evidence_id}: {fact.text}" for fact in question.facts_for(provider)
    )
    prompt = (
        f"{question.question}\n\nPRIVATE EVIDENCE PARTITION:\n{evidence}\n\n"
        "Use only this partition. No single specialist is guaranteed to have a complete proof. "
        "In the evidence array, report every fact that could participate in a chain from the "
        "named artifact to a clearance, preserving the exact format 'E##: fact'. Do not invent "
        "evidence IDs. Choose the best answer label even if the evidence is incomplete."
    )
    return Question(
        id=question.id, question=prompt, choices=question.choices, correct_label="A",
    )


async def preflight(config: StudyConfig) -> None:
    question = generate_question(9999, 20260925)
    reports = await asyncio.gather(*[
        ask_provider(provider, specialist_question(question, provider), config,
                     member_id=f"{provider}-specialist", stage="initial", sample_index=1)
        for provider in PROVIDERS
    ])
    decisions = await asyncio.gather(*[
        decide(question, config, condition, reports if condition == "report_synthesis" else None)
        for condition in CONDITIONS
    ])
    for report in reports:
        print(f"{report.provider}: PASS | resolved={report.resolved_model or report.requested_model}")
    for decision in decisions:
        print(f"jev-{decision.condition}: PASS | resolved={decision.resolved_model}")


async def run_question(question: EvidenceQuestion, config: StudyConfig, store: EvidenceStore,
                       max_attempts: int) -> None:
    missing = [provider for provider in PROVIDERS
               if store.specialist(question.id, provider) is None
               and store.attempts(question.id, "specialist", provider) < max_attempts]
    outcomes = await asyncio.gather(*[
        ask_provider(provider, specialist_question(question, provider), config,
                     member_id=f"{provider}-specialist", stage="initial", sample_index=1)
        for provider in missing
    ], return_exceptions=True)
    for provider, outcome in zip(missing, outcomes, strict=True):
        if isinstance(outcome, ModelAnswer):
            store.save_specialist(question.id, outcome)
        else:
            store.save_failure(question.id, "specialist", provider, outcome)
            print(f"  {provider}-specialist failed: {outcome}")
    reports = store.specialists(question.id)
    if len(reports) != 3:
        return
    for condition in CONDITIONS:
        if store.decision(question.id, condition) is not None:
            continue
        if store.attempts(question.id, condition, None) >= max_attempts:
            continue
        try:
            decision = await decide(
                question, config, condition,
                reports if condition == "report_synthesis" else None,
            )
            store.save_decision(question.id, decision)
        except Exception as exc:
            store.save_failure(question.id, condition, None, exc)
            print(f"  jev-{condition} failed: {exc}")


async def main() -> int:
    load_env_file()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/evidence_study_v1.json")
    parser.add_argument("--db", default="results/evidence-study-v1.sqlite3")
    parser.add_argument("--progress", default="results/evidence-progress-v1.txt")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    spec, config, questions, freeze_hash = load_frozen(Path(args.config))
    print(f"Freeze: {spec['freeze_id']} | Questions: {len(questions)}")
    if args.preflight:
        await preflight(config)
        return 0
    if not args.execute:
        print("Validation passed. No network calls or result writes made.")
        return 0
    selected = questions[:args.limit] if args.limit else questions
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    with EvidenceStore(args.db, freeze_hash) as store:
        for index, question in enumerate(selected, start=1):
            if store.complete(question.id):
                continue
            print(f"[{index:03d}/{len(selected)}] {question.id}")
            await run_question(question, config, store, spec["max_attempts_per_stage"])
            Path(args.progress).write_text(
                f"EVIDENCE STUDY - OPERATIONS ONLY\nFreeze: {spec['freeze_id']}\n"
                f"Complete: {store.complete_count()}/{len(questions)}\n"
                f"Recorded spend: ${store.cost():.4f}\nFailed calls: {store.failures()}\n"
                "No interim accuracy or auditability results displayed.\n",
                encoding="utf-8",
            )
        print("Pass complete. Rerun once for eligible retries before locked analysis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
