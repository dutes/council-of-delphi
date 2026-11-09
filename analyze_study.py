"""Locked paired analysis of the frozen crowd-to-council JEV study."""

from __future__ import annotations

import argparse
import random
import sqlite3
from collections import Counter
from pathlib import Path
from statistics import mean

from arbiter_study.core import PROVIDERS, aggregate_provider_crowd, baseline_label
from arbiter_study.models import Arbitration, DelphiAssessment, ModelAnswer, ProviderPosition


def interval(values: list[int], draws: int, seed: int) -> tuple[float, float, float]:
    generator = random.Random(seed)
    estimates = sorted(mean(generator.choice(values) for _ in values) for _ in range(draws))
    return mean(values), estimates[int(.025 * draws)], estimates[int(.975 * draws) - 1]


def read_models(db: sqlite3.Connection, table: str, question_id: str,
                stage: str, model: type):
    if table == "decisions":
        row = db.execute(
            "SELECT payload FROM decisions WHERE question_id=? AND stage=?",
            (question_id, stage),
        ).fetchone()
        return model.model_validate_json(row[0]) if row else None
    return [model.model_validate_json(row[0]) for row in db.execute(
        f"SELECT payload FROM {table} WHERE question_id=? AND stage=?",
        (question_id, stage),
    )]


def attempts(db: sqlite3.Connection, question_id: str, stage: str,
             member_id: str | None = None) -> int:
    if member_id is None:
        return db.execute(
            "SELECT COUNT(*) FROM calls WHERE question_id=? AND stage=? AND member_id IS NULL",
            (question_id, stage),
        ).fetchone()[0]
    return db.execute(
        "SELECT COUNT(*) FROM calls WHERE question_id=? AND stage=? AND member_id=?",
        (question_id, stage, member_id),
    ).fetchone()[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/study_v1.json")
    parser.add_argument("--db", default="results/arbiter-study-v2.sqlite3")
    parser.add_argument("--output", default="results/final-analysis-v2.txt")
    args = parser.parse_args()
    from run_study import load_frozen
    spec, config, questions, freeze_hash = load_frozen(Path(args.config))
    rows = []
    with sqlite3.connect(Path(args.db).resolve().as_uri() + "?mode=ro", uri=True) as db:
        stored = db.execute("SELECT value FROM meta WHERE key='freeze_hash'").fetchone()
        if not stored or stored[0] != freeze_hash:
            raise RuntimeError("Database is not from this freeze")
        failures = db.execute("SELECT COUNT(*) FROM calls WHERE success=0").fetchone()[0]
        spend = float(db.execute("SELECT COALESCE(SUM(cost),0) FROM calls").fetchone()[0])
        for question in questions:
            final = read_models(db, "decisions", question.id, "delphi_final", Arbitration)
            if final is None:
                initial = read_models(db, "answers", question.id, "initial", ModelAnswer)
                missing_ids = {
                    f"{provider}-initial-{index}"
                    for provider in PROVIDERS for index in range(1, config.crowd_size + 1)
                } - {answer.member_id for answer in initial}
                terminal = bool(missing_ids) and all(
                    attempts(db, question.id, "initial", member) >= spec["max_attempts_per_stage"]
                    for member in missing_ids
                )
                if not terminal:
                    controller = read_models(
                        db, "decisions", question.id, "jev_controller", DelphiAssessment
                    )
                    pending_stages = ["jev_alone", "jev_selection", "jev_controller"]
                    terminal = any(
                        read_models(db, "decisions", question.id, stage,
                                    DelphiAssessment if stage == "jev_controller" else Arbitration) is None
                        and attempts(db, question.id, stage) >= spec["max_attempts_per_stage"]
                        for stage in pending_stages
                    )
                    if controller and controller.action == "reconsider":
                        revised = read_models(
                            db, "answers", question.id, "reconsideration", ModelAnswer
                        )
                        missing_revised = {
                            f"{provider}-reconsideration-1" for provider in PROVIDERS
                        } - {answer.member_id for answer in revised}
                        terminal = terminal or (
                            bool(missing_revised) and all(
                                attempts(db, question.id, "reconsideration", member)
                                >= spec["max_attempts_per_stage"] for member in missing_revised
                            )
                        ) or attempts(db, question.id, "jev_final") >= spec["max_attempts_per_stage"]
                if not terminal:
                    raise RuntimeError("Study is still in progress; final analysis is locked")
                continue

            initial_answers = read_models(db, "answers", question.id, "initial", ModelAnswer)
            crowd_positions = read_models(db, "positions", question.id, "initial", ProviderPosition)
            direct = read_models(db, "decisions", question.id, "jev_alone", Arbitration)
            selection = read_models(db, "decisions", question.id, "jev_selection", Arbitration)
            controller = read_models(db, "decisions", question.id, "jev_controller", DelphiAssessment)
            if not (len(initial_answers) == 3 * config.crowd_size and len(crowd_positions) == 3
                    and direct and selection and controller):
                raise RuntimeError(f"Completed question {question.id} has incomplete artifacts")

            first_answers = [
                next(answer for answer in initial_answers
                     if answer.provider == provider and answer.sample_index == 1)
                for provider in PROVIDERS
            ]
            first_positions = [aggregate_provider_crowd(
                question, provider, first_answers, config.crowd_seed, "initial"
            ) for provider in PROVIDERS]
            first_vote = baseline_label(question, first_positions, config.tie_seed)
            crowd_vote = baseline_label(question, crowd_positions, config.tie_seed)

            procedure_positions = crowd_positions
            if controller.action == "reconsider":
                procedure_positions = read_models(
                    db, "positions", question.id, "reconsideration", ProviderPosition
                )
                if len(procedure_positions) != 3:
                    raise RuntimeError(f"Question {question.id} lacks revised positions")
            procedure_vote = baseline_label(question, procedure_positions, config.tie_seed)
            rows.append({
                "first_vote": first_vote == question.correct_label,
                "crowd_vote": crowd_vote == question.correct_label,
                "jev_alone": direct.selected_answer_label == question.correct_label,
                "selection": selection.selected_answer_label == question.correct_label,
                "procedure_vote": procedure_vote == question.correct_label,
                "delphi": final.selected_answer_label == question.correct_label,
                "reconsider": controller.action == "reconsider",
                "disagreement": len({p.answer_label for p in crowd_positions}) > 1,
                "candidate_available": question.correct_label in {
                    p.answer_label for p in crowd_positions
                },
                "sample_oracle": question.correct_label in {
                    answer.answer_label for answer in initial_answers
                },
                "provider_first": {
                    p.provider: p.answer_label == question.correct_label for p in first_positions
                },
                "provider_crowd": {
                    p.provider: p.answer_label == question.correct_label for p in crowd_positions
                },
            })

    if not rows:
        raise RuntimeError("No completed questions")
    n, expected = len(rows), len(questions)
    missing = expected - n
    evaluable = missing / expected <= spec["maximum_missing_fraction"]
    primary = [int(row["delphi"]) - int(row["crowd_vote"]) for row in rows]
    selection_delta = [int(row["selection"]) - int(row["crowd_vote"]) for row in rows]
    crowd_delta = [int(row["crowd_vote"]) - int(row["first_vote"]) for row in rows]
    p_delta, p_lower, p_upper = interval(primary, spec["bootstrap_draws"], spec["analysis_seed"])
    s_delta, s_lower, s_upper = interval(
        selection_delta, spec["bootstrap_draws"], spec["analysis_seed"] + 1
    )
    c_delta, c_lower, c_upper = interval(
        crowd_delta, spec["bootstrap_draws"], spec["analysis_seed"] + 2
    )
    transitions = Counter(primary)
    disagreement = [row for row in rows if row["disagreement"]]
    available = [row for row in rows if row["candidate_available"]]
    reconsidered = [row for row in rows if row["reconsider"]]
    lines = [
        "JEV CROWD-COUNCIL STUDY — FINAL LOCKED ANALYSIS", "=" * 52,
        f"Freeze: {spec['freeze_id']}", f"Complete: {n}/{expected}",
        f"Primary evaluable: {'YES' if evaluable else 'NO'}", f"Failed calls: {failures}", "",
        "CONDITION ACCURACY",
        f"Three first answers, cross-model vote: {100*mean(r['first_vote'] for r in rows):.2f}%",
        f"Three provider crowds, cross-model vote: {100*mean(r['crowd_vote'] for r in rows):.2f}%",
        f"JEV alone: {100*mean(r['jev_alone'] for r in rows):.2f}%",
        f"JEV selection-only: {100*mean(r['selection'] for r in rows):.2f}%",
        f"Post-controller positions, simple vote: {100*mean(r['procedure_vote'] for r in rows):.2f}%",
        f"Full JEV-controlled Delphi: {100*mean(r['delphi'] for r in rows):.2f}%", "",
        "PRIMARY RESULT",
        f"Full Delphi minus crowd majority: {100*p_delta:+.2f} pp",
        f"Bootstrap 95% interval: [{100*p_lower:+.2f}, {100*p_upper:+.2f}] pp",
        f"Helpful transitions: {transitions[1]}", f"Harmful transitions: {transitions[-1]}", "",
        "SECONDARY DECOMPOSITION",
        f"Own-crowds/cross-model vote minus first-answer vote: {100*c_delta:+.2f} pp "
        f"[{100*c_lower:+.2f}, {100*c_upper:+.2f}]",
        f"JEV selection-only minus crowd majority: {100*s_delta:+.2f} pp "
        f"[{100*s_lower:+.2f}, {100*s_upper:+.2f}]",
        f"JEV requested reconsideration: {len(reconsidered)}/{n}",
        f"Disagreement questions: {len(disagreement)}",
        f"Correct provider position available: {len(available)}/{n}",
        f"Any correct raw sample available: {sum(r['sample_oracle'] for r in rows)}/{n}",
        f"JEV selection accuracy when correct position available: "
        f"{100*mean(r['selection'] for r in available):.2f}%" if available else "No correct positions available",
        "", "PROVIDER FIRST-SAMPLE -> OWN-CROWD ACCURACY",
    ]
    for provider in PROVIDERS:
        first = mean(row["provider_first"][provider] for row in rows)
        crowd = mean(row["provider_crowd"][provider] for row in rows)
        lines.append(f"{provider.title()}: {100*first:.2f}% -> {100*crowd:.2f}% ({100*(crowd-first):+.2f} pp)")
    lines.extend(["", f"Recorded spend: ${spend:.4f}",
                  "No result from a quarantined earlier experiment is pooled here."])
    report = "\n".join(lines) + "\n"
    print(report, end="")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
