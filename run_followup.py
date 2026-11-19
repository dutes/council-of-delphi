"""Run the frozen follow-up study without showing any interim accuracy.

    python run_followup.py                # validate the freeze; no network calls
    python run_followup.py --preflight    # one synthetic question through every model and JEV call
    python run_followup.py --execute      # the scored run
    python run_followup.py --status       # progress and spend; never accuracy

Resuming: run --execute again. Finished questions are skipped, and unfinished ones
pick up at the step they stopped on, so only the missing calls are made.

If the cost cap pauses the run, raise it with a reason, which is recorded in the
database and shown in the analysis report, then carry on:

    python run_followup.py --execute --raise-cap 40 --reason "Estimate was low"
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import os
from pathlib import Path

from arbiter_study.core import PROVIDERS
from arbiter_study.jev import answer_alone, arbitrate, assess_delphi
from arbiter_study.models import ProviderPosition, Question
from followup_study.providers import ask_provider
from followup_study.pipeline import FINAL_STAGES, finished, run_question
from followup_study.seat import seat_position
from followup_study.spec import ARMS, arm_config, load_questions, load_spec, require_frozen
from followup_study.store import FollowupStore
from run_study import load_env_file


KEYS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "MISTRAL_API_KEY", "TYPESAFE_API_KEY")


async def preflight(configs: dict) -> None:
    """Unscored: a synthetic arithmetic question, never a study question."""
    question = Question(id="unscored-preflight", question="Which value equals two plus two?",
                        choices=["3", "4", "5"], correct_label="A")
    failures: list[str] = []
    for arm in configs:
        results = await asyncio.gather(*(
            ask_provider(p, question, configs[arm], member_id=f"{p}-initial-1", stage="initial",
                         sample_index=1) for p in PROVIDERS), return_exceptions=True)
        for provider, result in zip(PROVIDERS, results, strict=True):
            model = configs[arm].model(provider)
            if isinstance(result, Exception):
                print(f"{arm} {provider} {model}: FAIL | {result}")
                failures.append(f"{arm}:{provider}")
            else:
                print(f"{arm} {provider} {model}: PASS | resolved={result.resolved_model}")
    positions = [
        ProviderPosition(position_id=f"{p}-initial-position", provider=p, stage="initial",
                         answer_label=label, label_counts={label: 1},
                         samples=[{"answer_label": label, "confidence": .7, "rationale": why, "evidence": []}])
        for p, label, why in (("openai", "A", "Three is one below four."),
                              ("anthropic", "B", "Two plus two equals four."),
                              ("mistral", "B", "Adding the two pairs gives four."))]
    config = configs.get("matched") or configs["small"]
    direct = await answer_alone(question, config)
    with_seat = positions + [seat_position(direct)]
    checks = await asyncio.gather(arbitrate(question, with_seat, config),
                                  assess_delphi(question, with_seat, config), return_exceptions=True)
    print(f"jev-alone: PASS | selected={direct.selected_answer_label}")
    for name, result in zip(("jev-selection with seat", "jev-controller with seat"), checks, strict=True):
        if isinstance(result, Exception):
            print(f"{name}: FAIL | {result}")
            failures.append(name)
        else:
            print(f"{name}: PASS")
    if failures:
        raise RuntimeError("Preflight failures: " + ", ".join(failures))


async def main() -> int:
    load_env_file()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="config/followup_v1.json")
    parser.add_argument("--db", default="results/followup-v1.sqlite3")
    parser.add_argument("--progress", default="results/followup-progress-v1.txt")
    parser.add_argument("--limit", type=int, help="only the first N questions (for a smoke test)")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--raise-cap", type=float, help="new cost cap in USD (recorded as an amendment)")
    parser.add_argument("--reason", default="", help="why the cap is being raised")
    args = parser.parse_args()

    spec, freeze_hash = load_spec(args.config)
    ready = [arm for arm in ARMS if all(spec["arms"][arm].get(p) for p in PROVIDERS)]
    configs = {arm: arm_config(spec, arm) for arm in ready}
    if args.preflight:  # allowed before the freeze; checks whichever councils are chosen so far
        await preflight(configs)
        return 0
    if "matched" not in ready:
        raise RuntimeError("The matched council isn't chosen yet. Run run_followup_calibration.py, "
                           "then tools/freeze_followup.py.")
    require_frozen(spec)
    questions = load_questions(spec["dataset_path"], spec["dataset_sha256"], spec["question_count"])
    print(f"Freeze: {spec['freeze_id']} | questions: {len(questions)}")
    print("Primary comparison: JEV alone minus Delphi with the strength-matched council")
    if args.status or args.raise_cap is not None:
        Path(args.db).parent.mkdir(parents=True, exist_ok=True)
        with FollowupStore(args.db, freeze_hash, questions) as store:
            if args.raise_cap is not None:
                store.raise_cap(spec["max_recorded_cost_usd"], args.raise_cap, args.reason,
                                dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
                print(f"Cost cap raised to ${args.raise_cap:.2f}. This is recorded and shown in the report.")
            if args.status:
                done = sum(finished(store, q.id) for q in questions)
                print(f"Finished questions: {done}/{len(questions)}")
                print(f"Recorded spend: ${store.cost():.4f} of ${store.effective_cap(spec['max_recorded_cost_usd']):.2f}")
                print(f"Failed calls: {store.failures()}")
        if not args.execute:
            return 0
    if not args.execute:
        print("Validation passed. No network calls or writes made.")
        return 0
    missing = [name for name in KEYS if not os.getenv(name)]
    if missing:
        print("Missing environment variables: " + ", ".join(missing))
        return 2

    selected = questions[:args.limit] if args.limit else questions
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    with FollowupStore(args.db, freeze_hash, questions) as store:
        cap = store.effective_cap(spec["max_recorded_cost_usd"])
        remaining = [q for q in selected if not finished(store, q.id)]
        print(f"Questions still to finish: {len(remaining)} of {len(selected)}")
        for index, question in enumerate(remaining, start=1):
            if store.cost() >= cap:
                print(f"PAUSED: recorded cost cap of ${cap:.2f} reached with {len(remaining) - index + 1} "
                      "questions unfinished. To carry on, re-run with --raise-cap and --reason.")
                break
            print(f"[{index:03d}/{len(remaining)}] {question.id}")
            await run_question(question, configs, store, spec["max_attempts_per_stage"])
            Path(args.progress).write_text(
                "FOLLOW-UP STUDY - OPERATIONS ONLY\n"
                f"Freeze: {spec['freeze_id']}\n"
                + "".join(f"Complete {name}: {store.complete_count(stage)}/{len(questions)}\n"
                          for name, stage in FINAL_STAGES.items())
                + f"Recorded spend: ${store.cost():.4f} of ${cap:.2f}\nFailed calls: {store.failures()}\n"
                "No interim accuracy is displayed.\n", encoding="utf-8")
        print("Run paused or complete. Run analyze_followup.py only when every question is finished.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except RuntimeError as error:
        raise SystemExit(f"Stopped: {error}") from None
