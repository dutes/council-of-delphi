"""Run the frozen 300-question active Delphi confirmatory study."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path

from active_delphi.models import ActiveQuestion
from active_delphi.store import ActiveStore
from arbiter_study.config import StudyConfig
from evidence_study.models import EvidenceFact, EvidenceQuestion
from evidence_study.store import EvidenceStore
from run_active_delphi_pilot import run_question as run_active_question
from run_evidence_study import run_question as run_baseline_question
from run_study import load_env_file


IMPLEMENTATION_FILES = (
    "active_delphi/models.py", "active_delphi/generate.py", "active_delphi/jev.py",
    "active_delphi/store.py", "evidence_study/models.py", "evidence_study/jev.py",
    "evidence_study/store.py", "run_active_delphi_pilot.py", "run_evidence_study.py",
    "run_active_delphi_confirmatory.py", "analyze_active_delphi_confirmatory.py",
    "docs/ACTIVE_DELPHI_CONFIRMATORY_PROTOCOL.md",
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
        openai_model=spec["models"]["openai"], anthropic_model=spec["models"]["anthropic"],
        mistral_model=spec["models"]["mistral"], jev_model=spec["models"]["jev"],
        temperature=spec["temperature"], max_output_tokens=spec["max_output_tokens"],
        pricing={key: tuple(value) for key, value in spec["pricing"].items()},
    )
    return spec, config, questions, hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_version(question: ActiveQuestion) -> EvidenceQuestion:
    return EvidenceQuestion(
        id=question.id, question=question.question, choices=question.choices,
        correct_label=question.correct_label,
        facts=[EvidenceFact(
            evidence_id=f.evidence_id, text=f.text, partition=f.partition, is_support=f.is_support,
        ) for f in question.facts],
        support_ids=question.support_ids, metadata=question.metadata,
    )


async def main() -> int:
    load_env_file()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/active_delphi_confirmatory_v1.json")
    parser.add_argument("--baseline-db", default="results/active-confirmatory-baselines-v1.sqlite3")
    parser.add_argument("--active-db", default="results/active-confirmatory-controller-v1.sqlite3")
    parser.add_argument("--progress", default="results/active-confirmatory-progress-v1.txt")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    spec, config, questions, freeze_hash = load_frozen(Path(args.config))
    print(f"Freeze: {spec['freeze_id']} | Questions: {len(questions)}")
    if not args.execute:
        print("Validation passed. No network calls or result writes made.")
        return 0
    with EvidenceStore(args.baseline_db, freeze_hash) as baseline, ActiveStore(args.active_db, freeze_hash) as active:
        for start in range(0, len(questions), spec["concurrency"]):
            batch = questions[start:start + spec["concurrency"]]

            async def process(question: ActiveQuestion):
                await run_baseline_question(
                    evidence_version(question), config, baseline, spec["max_attempts_per_stage"]
                )
                await run_active_question(
                    question, config, active, spec["retrieval_attempts_per_stage"]
                )

            await asyncio.gather(*(process(question) for question in batch))
            Path(args.progress).write_text(
                "ACTIVE DELPHI CONFIRMATORY - OPERATIONS ONLY\n"
                f"Freeze: {spec['freeze_id']}\n"
                f"Baseline complete: {baseline.complete_count()}/{len(questions)}\n"
                f"Active terminal: {active.complete_count()}/{len(questions)}\n"
                f"Recorded spend: ${baseline.cost()+active.cost():.4f}\n"
                f"Failed calls: {baseline.failures()+active.failures()}\n"
                "No interim accuracy or auditability results displayed.\n",
                encoding="utf-8",
            )
            print(f"Operations complete through {min(start+len(batch), len(questions))}/{len(questions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

