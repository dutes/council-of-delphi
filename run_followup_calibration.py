"""Choose the strength-matched council (docs/FOLLOWUP_PROTOCOL.md, "Choosing the
strength-matched council").

    python run_followup_calibration.py --preflight   # synthetic question to every candidate; no study data
    python run_followup_calibration.py --execute     # 60 calibration questions; resumable

Measures JEV alone and each candidate's first answer (one sample, the first
study's prompt and temperature) on the 60 calibration questions, then applies
the selection rule: for each provider, the cheapest candidate within the
tolerance of JEV alone, otherwise that provider's most accurate candidate.

These 60 questions are only for matching. They're never used in the analysis.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
from statistics import mean

from arbiter_study.jev import answer_alone
from arbiter_study.models import Arbitration, Question
from arbiter_study.providers import ask_provider
from followup_study.pipeline import answer_stage, decision_stage
from followup_study.spec import PROVIDERS, load_questions, load_spec, sha256_file, single_model_config
from followup_study.store import FollowupStore
from run_study import load_env_file


RECONSIDER_RATE = 220 / 494   # how often JEV asked for a second round in the first study
RECONSIDER_COST_FACTOR = 1.5  # a reconsideration prompt carries the council's positions


def candidate_list(spec: dict) -> list[tuple[str, str, tuple[float, float], bool]]:
    """(provider, model, pricing, is_candidate). The small council is measured too, for cost estimates."""
    found = []
    for provider in PROVIDERS:
        entries = spec["candidates"].get(provider) or []
        if not entries:
            raise RuntimeError(f"No candidate models listed for {provider} in the config")
        for entry in entries:
            found.append((provider, entry["model"], tuple(entry["pricing"]), True))
        small = spec["arms"]["small"][provider]
        if small not in {e["model"] for e in entries}:
            found.append((provider, small, tuple(spec["pricing"][small]), False))
    return found


def stage_of(provider: str, model: str) -> str:
    return f"model:{provider}:{model}"


async def preflight(spec: dict) -> None:
    question = Question(id="unscored-preflight", question="Which value equals two plus two?",
                        choices=["3", "4", "5"], correct_label="A")
    failures = []
    for provider, model, pricing, _ in candidate_list(spec):
        config = single_model_config(spec, provider, model, {model: pricing})
        try:
            result = await ask_provider(provider, question, config, member_id=f"{provider}-initial-1",
                                        stage="initial", sample_index=1)
            print(f"{provider} {model}: PASS | resolved={result.resolved_model}")
        except Exception as exc:  # noqa: BLE001
            print(f"{provider} {model}: FAIL | {exc}")
            failures.append(model)
    if failures:
        raise RuntimeError("Remove or fix these candidates before calibrating: " + ", ".join(failures))


def choose(spec: dict, table: dict, jev_accuracy: float) -> dict:
    tolerance = spec["match_tolerance_pp"] / 100
    chosen = {}
    for provider in PROVIDERS:
        options = [row for row in table.values() if row["provider"] == provider and row["candidate"]]
        close = [row for row in options if row["accuracy"] >= jev_accuracy - tolerance]
        if close:
            pick = min(close, key=lambda row: (row["cost_per_question"], -row["accuracy"], row["model"]))
            rule = f"cheapest within {spec['match_tolerance_pp']} points of JEV alone"
        else:
            pick = max(options, key=lambda row: (row["accuracy"], -row["cost_per_question"], row["model"]))
            rule = "no candidate within tolerance; most accurate candidate"
        chosen[provider] = {"model": pick["model"], "accuracy": pick["accuracy"],
                            "gap_to_jev_pp": round(100 * (jev_accuracy - pick["accuracy"]), 2),
                            "rule": rule}
    return chosen


def estimate_cost(spec: dict, table: dict, chosen: dict, jev_cost: float, questions: int) -> dict:
    crowd = spec["crowd_size"]

    def council(models: list[tuple[str, str]]) -> float:
        per_call = sum(table[f"{p}|{m}"]["cost_per_question"] for p, m in models)
        return crowd * per_call + RECONSIDER_RATE * per_call * RECONSIDER_COST_FACTOR

    small = [(p, spec["arms"]["small"][p]) for p in PROVIDERS]
    matched = [(p, chosen[p]["model"]) for p in PROVIDERS]
    matched_recon = RECONSIDER_RATE * RECONSIDER_COST_FACTOR * sum(
        table[f"{p}|{m}"]["cost_per_question"] for p, m in matched)
    jev_calls = 1 + 3 * (1 + RECONSIDER_RATE)  # alone, then a controller (+ final) per Delphi run
    per_question = council(small) + council(matched) + matched_recon + jev_calls * jev_cost
    total = per_question * questions
    return {"per_question_usd": round(per_question, 5), "total_usd": round(total, 2),
            "suggested_cap_usd": round(total * 1.5 + 1, 0),
            "assumptions": f"reconsideration on {RECONSIDER_RATE:.0%} of questions (first study), "
                           f"reconsideration prompts {RECONSIDER_COST_FACTOR}x the cost of a first answer"}


async def main() -> int:
    load_env_file()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="config/followup_v1.json")
    parser.add_argument("--db", default="results/followup-calibration.sqlite3")
    parser.add_argument("--output", default="results/followup-calibration.json")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    spec, _ = load_spec(args.config)
    if spec.get("status") == "frozen":
        raise RuntimeError("The study is already frozen; calibration happens before the freeze")
    if args.preflight:
        await preflight(spec)
        return 0
    if not args.execute:
        print("Nothing to do. Use --preflight or --execute.")
        return 0
    missing = [k for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "MISTRAL_API_KEY", "TYPESAFE_API_KEY")
               if not os.getenv(k)]
    if missing:
        print("Missing environment variables: " + ", ".join(missing))
        return 2

    path = spec["calibration_path"]
    dataset_sha = sha256_file(path)
    questions = load_questions(path, expected_count=60)
    models = candidate_list(spec)
    plan = hashlib.sha256(json.dumps([dataset_sha, [m[:2] for m in models]]).encode()).hexdigest()
    attempts = spec["max_attempts_per_stage"]
    jev_config = single_model_config(spec, "openai", spec["arms"]["small"]["openai"])

    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    with FollowupStore(args.db, "calibration:" + plan, questions) as store:
        for index, source in enumerate(questions, start=1):
            print(f"[{index:02d}/60] {source.id}")
            question = source.model_copy(update={"correct_label": "A"})
            await decision_stage(question, store, "jev_alone", Arbitration,
                                 lambda: answer_alone(question, jev_config), attempts)
            for provider, model, pricing, _ in models:
                config = single_model_config(spec, provider, model, {model: pricing})
                await answer_stage(question, config, store, stage_of(provider, model), "initial",
                                   [(provider, 1)], None, attempts)

        truth = {q.id: q.correct_label for q in questions}
        jev = [(q.id, store.decision(q.id, "jev_alone", Arbitration)) for q in questions]
        jev_done = [(qid, d) for qid, d in jev if d is not None]
        table = {}
        for provider, model, _, is_candidate in models:
            answers = [(q.id, store.answers(q.id, stage_of(provider, model))) for q in questions]
            done = [(qid, a[0]) for qid, a in answers if a]
            table[f"{provider}|{model}"] = {
                "provider": provider, "model": model, "candidate": is_candidate,
                "answered": len(done),
                "accuracy": mean(a.answer_label == truth[qid] for qid, a in done) if done else 0.0,
                "cost_per_question": mean((a.estimated_cost_usd or 0) for _, a in done) if done else 0.0,
            }
        spent = store.cost()

    if len(jev_done) < 57 or any(row["answered"] < 57 for row in table.values()):
        print("More than 5% of calibration answers are missing; re-run --execute to retry, "
              "or drop the failing candidate from the config.")
        return 1
    jev_accuracy = mean(d.selected_answer_label == truth[qid] for qid, d in jev_done)
    jev_cost = mean((d.estimated_cost_usd or 0) for _, d in jev_done)
    chosen = choose(spec, table, jev_accuracy)
    estimate = estimate_cost(spec, table, chosen, jev_cost, spec["question_count"])
    report = {
        "calibration_sha256": dataset_sha, "jev_alone_accuracy": jev_accuracy,
        "jev_cost_per_call": jev_cost, "match_tolerance_pp": spec["match_tolerance_pp"],
        "models": table, "chosen": chosen, "main_run_cost_estimate": estimate,
        "calibration_spend_usd": round(spent, 4),
    }
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"\nJEV alone: {100 * jev_accuracy:.1f}%")
    for row in sorted(table.values(), key=lambda r: (r["provider"], -r["accuracy"])):
        tag = "" if row["candidate"] else "  (small council, for cost only)"
        print(f"{row['provider']:<10} {row['model']:<36} {100 * row['accuracy']:5.1f}%  "
              f"${row['cost_per_question']:.5f}/question{tag}")
    print("\nChosen matched council:")
    for provider, pick in chosen.items():
        gap = pick["gap_to_jev_pp"]
        print(f"  {provider}: {pick['model']} ({100 * pick['accuracy']:.1f}%, "
              f"{abs(gap):.1f} points {'below' if gap >= 0 else 'above'} JEV) - {pick['rule']}")
    print(f"\nEstimated main run: ${estimate['total_usd']:.2f}; suggested cost cap ${estimate['suggested_cap_usd']:.0f}")
    print(f"Calibration spend: ${spent:.4f}. Written to {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except RuntimeError as error:
        raise SystemExit(f"Stopped: {error}") from None
