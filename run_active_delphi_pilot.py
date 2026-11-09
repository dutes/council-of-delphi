"""Run the frozen 30-question classifier-led Delphi engineering pilot."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
from pathlib import Path

from active_delphi.generate import PROVIDERS, RELATIONS, generate_question
from active_delphi.jev import classify_next_action
from active_delphi.models import ActiveFact, ActiveOutcome, ActiveQuestion
from active_delphi.store import ActiveStore
from arbiter_study.config import StudyConfig
from arbiter_study.models import ModelAnswer, Question
from arbiter_study.providers import ask_provider
from run_study import load_env_file


IMPLEMENTATION_FILES = (
    "active_delphi/models.py", "active_delphi/generate.py", "active_delphi/jev.py",
    "active_delphi/store.py", "run_active_delphi_pilot.py",
    "analyze_active_delphi_pilot.py", "docs/ACTIVE_DELPHI_PILOT_PROTOCOL.md",
)


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
    questions = [ActiveQuestion.model_validate_json(line) for line in dataset.read_text(
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


def retrieval_question(question: ActiveQuestion, provider: str, subject: str,
                       relation: str, stage: int, attempt: int) -> Question:
    relation_text = {
        "stored_in": "which vault stores",
        "administered_by": "which sector administers",
        "uses_clearance": "which clearance code is used by",
    }[relation]
    evidence = "\n".join(
        f"{fact.evidence_id}: {fact.text}" for fact in question.facts_for(provider)
    )
    prompt = (
        f"TARGETED RETRIEVAL: Find evidence stating {relation_text} {subject}.\n\n"
        f"PRIVATE EVIDENCE PARTITION:\n{evidence}\n\n"
        "Choose A only if one or more statements directly match the exact subject and requested "
        "relationship; otherwise choose B. In the evidence array, copy every direct match in "
        "the exact format 'E##: fact'. Do not report merely related facts, infer a missing link, "
        "or invent evidence IDs."
    )
    return Question(
        id=f"{question.id}-s{stage}-a{attempt}", question=prompt,
        choices=["Direct matching evidence is present", "No direct matching evidence is present"],
        correct_label="A",
    )


def cited_candidates(question: ActiveQuestion, reports: list[ModelAnswer]) -> list[ActiveFact]:
    candidates: dict[str, ActiveFact] = {}
    for report in reports:
        owned = {fact.evidence_id: fact for fact in question.facts_for(report.provider)}
        for item in report.evidence:
            match = re.match(r"\s*(E\d{2})\b", item)
            if match and match.group(1) in owned:
                candidates[match.group(1)] = owned[match.group(1)]
    return list(candidates.values())


async def collect_reports(question: ActiveQuestion, config: StudyConfig, store: ActiveStore,
                          stage: int, attempt: int, subject: str, relation: str) -> list[ModelAnswer]:
    existing = {report.provider: report for report in store.retrievals(question.id, stage, attempt)}
    missing = [provider for provider in PROVIDERS if provider not in existing]
    outcomes = await asyncio.gather(*[
        ask_provider(
            provider, retrieval_question(question, provider, subject, relation, stage, attempt), config,
            member_id=f"{provider}-stage-{stage}-attempt-{attempt}", stage="initial", sample_index=1,
        ) for provider in missing
    ], return_exceptions=True)
    for provider, outcome in zip(missing, outcomes, strict=True):
        if isinstance(outcome, ModelAnswer):
            store.save_retrieval(question.id, stage, attempt, outcome)
        else:
            store.save_failure(question.id, f"retrieve_{stage}_{attempt}", provider, outcome)
    return store.retrievals(question.id, stage, attempt)


async def run_question(question: ActiveQuestion, config: StudyConfig, store: ActiveStore,
                       attempts_per_stage: int) -> None:
    if store.outcome(question.id):
        return
    subject = question.target_artifact
    accepted: list[ActiveFact] = []
    specialist_calls = 0
    jev_calls = 0
    status = "halt_unresolved"

    for stage, relation in enumerate(RELATIONS):
        accepted_this_stage = False
        for attempt in range(1, attempts_per_stage + 1):
            reports = await collect_reports(question, config, store, stage, attempt, subject, relation)
            specialist_calls += len(reports)
            if len(reports) != len(PROVIDERS):
                status = "provider_failure"
                break
            action = store.action(question.id, stage, attempt)
            if action is None:
                try:
                    action = await classify_next_action(
                        question, config, stage_index=stage, attempt=attempt,
                        subject=subject, relation=relation,
                        candidates=cited_candidates(question, reports), accepted_path=accepted,
                    )
                    store.save_action(question.id, action)
                except Exception as exc:
                    store.save_failure(question.id, f"jev_{stage}_{attempt}", None, exc)
                    status = "jev_failure"
                    break
            jev_calls += 1
            if action.accepted_evidence_id:
                fact = question.fact(action.accepted_evidence_id)
                if fact is None or fact not in cited_candidates(question, reports):
                    status = "invalid_acceptance"
                    break
                accepted.append(fact)
                subject = fact.object
                accepted_this_stage = True
                status = "in_progress"
                break
            if action.action == "halt_unresolved":
                status = "halt_unresolved"
                break
        if not accepted_this_stage:
            break

    selected = None
    if len(accepted) == len(RELATIONS):
        try:
            selected = chr(ord("A") + question.choices.index(accepted[-1].object))
            status = "complete"
        except ValueError:
            status = "clearance_not_in_choices"
    store.save_outcome(question.id, ActiveOutcome(
        status=status, selected_answer_label=selected,
        accepted_evidence_ids=[fact.evidence_id for fact in accepted],
        rounds_used=len(accepted), specialist_calls=specialist_calls, jev_calls=jev_calls,
    ))


async def preflight(config: StudyConfig) -> None:
    question = generate_question(99999, 20260929, prefix="active-preflight")
    subject = question.target_artifact
    reports = await asyncio.gather(*[
        ask_provider(
            provider, retrieval_question(question, provider, subject, RELATIONS[0], 0, 1), config,
            member_id=f"{provider}-preflight", stage="initial", sample_index=1,
        ) for provider in PROVIDERS
    ])
    action = await classify_next_action(
        question, config, stage_index=0, attempt=1, subject=subject,
        relation=RELATIONS[0], candidates=cited_candidates(question, reports), accepted_path=[],
    )
    for report in reports:
        print(f"{report.provider}: PASS | resolved={report.resolved_model or report.requested_model}")
    print(f"jev-classifier: PASS | action={action.action} | resolved={action.resolved_model}")


async def main() -> int:
    load_env_file()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/active_delphi_pilot_v1.json")
    parser.add_argument("--db", default="results/active-delphi-pilot-v1.sqlite3")
    parser.add_argument("--progress", default="results/active-delphi-pilot-progress-v1.txt")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    spec, config, questions, freeze_hash = load_frozen(Path(args.config))
    print(f"Freeze: {spec['freeze_id']} | Pilot questions: {len(questions)}")
    if args.preflight:
        await preflight(config)
        return 0
    if not args.execute:
        print("Validation passed. No network calls or result writes made.")
        return 0
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    with ActiveStore(args.db, freeze_hash) as store:
        for index, question in enumerate(questions, start=1):
            if store.outcome(question.id):
                continue
            print(f"[{index:02d}/{len(questions)}] {question.id}")
            await run_question(question, config, store, spec["retrieval_attempts_per_stage"])
            Path(args.progress).write_text(
                "ACTIVE DELPHI PILOT - OPERATIONS ONLY\n"
                f"Freeze: {spec['freeze_id']}\nComplete: {store.complete_count()}/{len(questions)}\n"
                f"Recorded spend: ${store.cost():.4f}\nFailed calls: {store.failures()}\n",
                encoding="utf-8",
            )
        print("Pilot pass complete. Rerun once for resumable failures, then analyze.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

