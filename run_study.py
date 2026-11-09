"""Execute the frozen crowd-to-council JEV study without interim accuracy."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
from pathlib import Path

from arbiter_study.config import StudyConfig
from arbiter_study.core import PROVIDERS, aggregate_provider_crowd, reconsideration_context
from arbiter_study.jev import answer_alone, arbitrate, assess_delphi
from arbiter_study.models import Arbitration, DelphiAssessment, ModelAnswer, ProviderPosition, Question
from arbiter_study.providers import ask_provider
from arbiter_study.store import StudyStore


IMPLEMENTATION_FILES = (
    "arbiter_study/models.py", "arbiter_study/core.py", "arbiter_study/config.py",
    "arbiter_study/providers.py", "arbiter_study/jev.py", "arbiter_study/store.py",
    "run_study.py", "analyze_study.py", "docs/PROTOCOL.md",
)


def load_env_file(path: Path = Path(".env")) -> None:
    """Load simple KEY=value or $env:KEY=value assignments without executing them."""
    if not path.exists():
        return
    for number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("$env:"):
            line = line[5:]
        name, separator, value = line.partition("=")
        name, value = name.strip(), value.strip()
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise RuntimeError(f"Invalid .env assignment on line {number}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(name, value)


def implementation_hash() -> str:
    digest = hashlib.sha256()
    for name in IMPLEMENTATION_FILES:
        digest.update(name.encode() + b"\0")
        digest.update(Path(name).read_bytes() + b"\0")
    return digest.hexdigest()


def load_frozen(path: Path) -> tuple[dict, StudyConfig, list[Question], str]:
    raw_bytes = path.read_bytes()
    spec = json.loads(raw_bytes)
    if tuple(spec["implementation_files"]) != IMPLEMENTATION_FILES:
        raise RuntimeError("Implementation list differs from freeze")
    if implementation_hash() != spec["implementation_sha256"]:
        raise RuntimeError("Active study implementation differs from freeze")
    dataset = Path(spec["dataset_path"])
    if hashlib.sha256(dataset.read_bytes()).hexdigest() != spec["dataset_sha256"]:
        raise RuntimeError("Active dataset differs from freeze")
    questions = [Question.model_validate_json(line) for line in dataset.read_text(
        encoding="utf-8"
    ).splitlines() if line]
    if len(questions) != spec["question_count"]:
        raise RuntimeError("Question count differs from freeze")
    config = StudyConfig(
        openai_model=spec["models"]["openai"],
        anthropic_model=spec["models"]["anthropic"],
        mistral_model=spec["models"]["mistral"], jev_model=spec["models"]["jev"],
        crowd_size=spec["crowd_size"], temperature=spec["temperature"],
        max_output_tokens=spec["max_output_tokens"], crowd_seed=spec["crowd_seed"],
        arbitration_seed=spec["arbitration_seed"], tie_seed=spec["tie_seed"],
        pricing={key: tuple(value) for key, value in spec["pricing"].items()},
    )
    return spec, config, questions, hashlib.sha256(raw_bytes).hexdigest()


def as_final(decision: Arbitration | DelphiAssessment) -> Arbitration:
    if isinstance(decision, Arbitration):
        return decision.model_copy(update={"estimated_cost_usd": 0})
    return Arbitration(
        selected_candidate_id=decision.selected_candidate_id,
        selected_answer_label=decision.selected_answer_label,
        confidence=decision.answer_confidence,
        probabilities=decision.answer_probabilities,
        resolved_model="derived-from-delphi-controller", latency_ms=0,
        input_tokens=0, output_tokens=0, estimated_cost_usd=0,
        raw_response={"derived_from": "jev_controller", "action": decision.action},
    )


async def preflight(config: StudyConfig) -> None:
    question = Question(
        id="unscored-preflight", question="Which value equals two plus two?",
        choices=["3", "4", "5"], correct_label="B",
    )
    masked = question.model_copy(update={"correct_label": "A"})
    provider_results = await asyncio.gather(*(
        ask_provider(provider, masked, config, member_id=f"{provider}-initial-1",
                     stage="initial", sample_index=1)
        for provider in PROVIDERS
    ), return_exceptions=True)
    failures: list[str] = []
    for provider, result in zip(PROVIDERS, provider_results, strict=True):
        if isinstance(result, Exception):
            print(f"{provider}: FAIL | {result}")
            failures.append(provider)
        else:
            print(f"{provider}: PASS | resolved={result.resolved_model or result.requested_model}")

    # Force disagreement so selection is a real JEV request rather than unanimous pass-through.
    synthetic_positions = [
        ProviderPosition(
            position_id=f"{provider}-initial-position", provider=provider,
            stage="initial", answer_label=label, label_counts={label: 1},
            samples=[{"answer_label": label, "confidence": .7,
                      "rationale": rationale, "evidence": []}],
        )
        for provider, label, rationale in (
            ("openai", "A", "Three is one below four."),
            ("anthropic", "B", "Two plus two equals four."),
            ("mistral", "B", "Adding the two pairs gives four."),
        )
    ]
    jev_results = await asyncio.gather(
        answer_alone(masked, config), arbitrate(masked, synthetic_positions, config),
        assess_delphi(masked, synthetic_positions, config), return_exceptions=True,
    )
    for name, result in zip(("jev-alone", "jev-selection", "jev-controller"),
                            jev_results, strict=True):
        if isinstance(result, Exception):
            print(f"{name}: FAIL | {result}")
            failures.append(name)
        elif isinstance(result, DelphiAssessment):
            print(f"{name}: PASS | resolved={result.resolved_model} | action={result.action}")
        else:
            print(f"{name}: PASS | resolved={result.resolved_model} | selected={result.selected_answer_label}")
    if failures:
        raise RuntimeError("Preflight failures: " + ", ".join(failures))


async def _answer_stage(question: Question, config: StudyConfig, store: StudyStore,
                        stage: str, members: list[tuple[str, int]], context: dict | None,
                        maximum_attempts: int) -> None:
    eligible = [
        (provider, sample_index, f"{provider}-{stage}-{sample_index}")
        for provider, sample_index in members
        if store.attempts(question.id, stage, f"{provider}-{stage}-{sample_index}") < maximum_attempts
        and f"{provider}-{stage}-{sample_index}" not in {
            answer.member_id for answer in store.answers(question.id, stage)
        }
    ]
    outcomes = await asyncio.gather(*(
        ask_provider(provider, question, config, member_id=member_id,
                     stage=stage, sample_index=sample_index, context=context)
        for provider, sample_index, member_id in eligible
    ), return_exceptions=True)
    for (_, _, member_id), outcome in zip(eligible, outcomes, strict=True):
        if isinstance(outcome, ModelAnswer):
            store.save_answer(question.id, outcome)
        else:
            store.save_failure(question.id, stage, member_id, outcome)
            print(f"  {member_id} failed: {outcome}")


async def _decision_stage(question: Question, store: StudyStore, stage: str,
                          model: type, call, maximum_attempts: int):
    existing = store.decision(question.id, stage, model)
    if existing is not None:
        return existing
    if store.attempts(question.id, stage) >= maximum_attempts:
        return None
    try:
        result = await call()
        store.save_decision(question.id, stage, result)
        return result
    except Exception as exc:
        store.save_failure(question.id, stage, None, exc)
        print(f"  {stage} failed: {exc}")
        return None


async def main() -> int:
    load_env_file()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/study_v1.json")
    parser.add_argument("--db", default="results/arbiter-study-v5.sqlite3")
    parser.add_argument("--progress", default="results/progress-v5.txt")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--max-recorded-cost-usd", type=float, default=15)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    spec, config, questions, freeze_hash = load_frozen(Path(args.config))
    print(f"Freeze: {spec['freeze_id']}")
    print(f"Questions: {len(questions)} | crowd size per provider: {config.crowd_size}")
    print("Primary comparison: full JEV-Delphi final minus cross-model crowd majority")
    if args.preflight:
        await preflight(config)
        return 0
    if not args.execute:
        print("Validation passed. No network calls or writes made.")
        return 0
    needed = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "MISTRAL_API_KEY", "TYPESAFE_API_KEY")
    missing = [name for name in needed if not os.getenv(name)]
    if missing:
        print("Missing environment variables: " + ", ".join(missing))
        return 2

    maximum_attempts = spec["max_attempts_per_stage"]
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    selected = questions[:args.limit] if args.limit else questions
    with StudyStore(args.db, freeze_hash, questions) as store:
        for index, source_question in enumerate(selected, start=1):
            if store.decision(source_question.id, "delphi_final", Arbitration):
                continue
            if store.cost() >= args.max_recorded_cost_usd:
                print("PAUSED: recorded cost cap reached")
                break
            print(f"[{index:03d}/{len(selected)}] {source_question.id}")
            question = source_question.model_copy(update={"correct_label": "A"})

            initial_members = [(provider, sample_index) for provider in PROVIDERS
                               for sample_index in range(1, config.crowd_size + 1)]
            await _answer_stage(question, config, store, "initial", initial_members, None,
                                maximum_attempts)
            initial_answers = store.answers(question.id, "initial")
            if len(initial_answers) != len(initial_members):
                continue
            positions = store.positions(question.id, "initial")
            if not positions:
                positions = [aggregate_provider_crowd(
                    question, provider, initial_answers, config.crowd_seed, "initial"
                ) for provider in PROVIDERS]
                store.save_positions(question.id, positions)

            direct = await _decision_stage(
                question, store, "jev_alone", Arbitration,
                lambda: answer_alone(question, config), maximum_attempts,
            )
            selection = await _decision_stage(
                question, store, "jev_selection", Arbitration,
                lambda: arbitrate(question, positions, config), maximum_attempts,
            )
            controller = await _decision_stage(
                question, store, "jev_controller", DelphiAssessment,
                lambda: assess_delphi(question, positions, config), maximum_attempts,
            )
            if direct is None or selection is None or controller is None:
                continue

            if controller.action == "reconsider":
                context = reconsideration_context(question, positions, config.arbitration_seed)
                reconsider_members = [(provider, 1) for provider in PROVIDERS]
                await _answer_stage(question, config, store, "reconsideration",
                                    reconsider_members, context, maximum_attempts)
                revised_answers = store.answers(question.id, "reconsideration")
                if len(revised_answers) != 3:
                    continue
                revised_positions = store.positions(question.id, "reconsideration")
                if not revised_positions:
                    revised_positions = [aggregate_provider_crowd(
                        question, provider, revised_answers, config.crowd_seed,
                        "reconsideration",
                    ) for provider in PROVIDERS]
                    store.save_positions(question.id, revised_positions)
                final_source = await _decision_stage(
                    question, store, "jev_final", Arbitration,
                    lambda: arbitrate(question, revised_positions, config), maximum_attempts,
                )
                if final_source is None:
                    continue
            else:
                final_source = controller
            if store.decision(question.id, "delphi_final", Arbitration) is None:
                store.save_decision(question.id, "delphi_final", as_final(final_source))

            Path(args.progress).parent.mkdir(parents=True, exist_ok=True)
            Path(args.progress).write_text(
                f"JEV CROWD-COUNCIL STUDY — OPERATIONS ONLY\nFreeze: {spec['freeze_id']}\n"
                f"Complete: {store.complete_count()}/{len(questions)}\n"
                f"Recorded spend: ${store.cost():.4f}\nFailed calls: {store.failures()}\n"
                "No interim accuracy is displayed.\n",
                encoding="utf-8",
            )
        print("Run paused or complete. Use analyze_study.py only after terminal completion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
