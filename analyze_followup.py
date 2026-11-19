"""Locked analysis of the frozen follow-up study.

Refuses to run until every question is finished (or has terminally failed), so
no accuracy can be seen part-way through the run.
"""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
from collections import Counter
from pathlib import Path
from statistics import mean

from arbiter_study.core import PROVIDERS, baseline_label
from arbiter_study.models import Arbitration, DelphiAssessment, ModelAnswer, ProviderPosition
from followup_study.pipeline import FINAL_STAGES
from followup_study.spec import load_questions, load_spec, require_frozen


# Which stage prefixes each condition depends on, for deciding whether a gap is terminal.
DEPENDS_ON = {
    "jev_alone": ("jev_alone",),
    "small": ("small:",),
    "matched": ("matched:",),
    "seat": ("seat:", "matched:initial", "jev_alone"),
}


def interval(values: list[int], draws: int, seed: int) -> tuple[float, float, float]:
    """Mean with a paired question-bootstrap 95% percentile interval (same method as the first study)."""
    generator = random.Random(seed)
    estimates = sorted(mean(generator.choice(values) for _ in values) for _ in range(draws))
    return mean(values), estimates[int(.025 * draws)], estimates[int(.975 * draws) - 1]


def decision(db: sqlite3.Connection, qid: str, stage: str, model: type):
    row = db.execute("SELECT payload FROM decisions WHERE question_id=? AND stage=?", (qid, stage)).fetchone()
    return model.model_validate_json(row[0]) if row else None


def rows_of(db: sqlite3.Connection, table: str, qid: str, stage: str, model: type) -> list:
    return [model.model_validate_json(r[0]) for r in db.execute(
        f"SELECT payload FROM {table} WHERE question_id=? AND stage=?", (qid, stage))]


def terminal(db: sqlite3.Connection, qid: str, condition: str, max_attempts: int) -> bool:
    for prefix in DEPENDS_ON[condition]:
        exhausted = db.execute(
            "SELECT 1 FROM calls WHERE question_id=? AND (stage=? OR stage LIKE ?) "
            "GROUP BY stage, member_id HAVING SUM(success)=0 AND COUNT(*)>=? LIMIT 1",
            (qid, prefix, prefix + "%" if prefix.endswith(":") else prefix, max_attempts)).fetchone()
        if exhausted:
            return True
    return False


def analyse(spec: dict, freeze_hash: str, db_path: str) -> str:
    questions = load_questions(spec["dataset_path"], spec["dataset_sha256"], spec["question_count"])
    max_attempts = spec["max_attempts_per_stage"]
    draws, seed = spec["bootstrap_draws"], spec["analysis_seed"]
    rows: list[dict] = []
    with sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True) as db:
        stored = db.execute("SELECT value FROM meta WHERE key='freeze_hash'").fetchone()
        if not stored or stored[0] != freeze_hash:
            raise RuntimeError("Database is not from this freeze")
        failures = db.execute("SELECT COUNT(*) FROM calls WHERE success=0").fetchone()[0]
        spend = float(db.execute("SELECT COALESCE(SUM(cost),0) FROM calls").fetchone()[0])
        cap_row = db.execute("SELECT value FROM meta WHERE key='cap_amendments'").fetchone()
        cap_amendments = json.loads(cap_row[0]) if cap_row else []
        spend_by = dict(db.execute(
            "SELECT CASE WHEN instr(stage, ':') > 0 THEN substr(stage, 1, instr(stage, ':') - 1) "
            "ELSE stage END, COALESCE(SUM(cost),0) FROM calls GROUP BY 1").fetchall())
        for q in questions:
            truth = q.correct_label
            row: dict = {"id": q.id}
            for name, stage in FINAL_STAGES.items():
                final = decision(db, q.id, stage, Arbitration)
                if final is None and not terminal(db, q.id, name, max_attempts):
                    raise RuntimeError("The study is still in progress; the analysis is locked")
                row[name] = None if final is None else final.selected_answer_label == truth
                row[name + "_label"] = None if final is None else final.selected_answer_label
            matched_positions = rows_of(db, "positions", q.id, "matched:initial", ProviderPosition)
            row["matched_vote"] = (baseline_label(q, matched_positions, spec["tie_seed"]) == truth
                                   if len(matched_positions) == 3 else None)
            row["matched_available"] = (truth in {p.answer_label for p in matched_positions}
                                        if len(matched_positions) == 3 else None)
            for arm in ("small", "matched"):
                answers = rows_of(db, "answers", q.id, f"{arm}:initial", ModelAnswer)
                row[f"{arm}_first"] = {a.provider: a.answer_label == truth for a in answers if a.sample_index == 1}
                positions = rows_of(db, "positions", q.id, f"{arm}:initial", ProviderPosition)
                row[f"{arm}_crowd"] = {p.provider: p.answer_label == truth for p in positions}
            for prefix in ("small", "matched", "seat"):
                controller = decision(db, q.id, f"{prefix}:controller", DelphiAssessment)
                row[f"{prefix}_reconsider"] = None if controller is None else controller.action == "reconsider"
                row[f"{prefix}_controller_right"] = (None if controller is None
                                                     else controller.selected_answer_label == truth)
            direct = decision(db, q.id, "jev_alone", Arbitration)
            row["seat_kept"] = (None if direct is None or row["seat_label"] is None
                                else row["seat_label"] == direct.selected_answer_label)
            rows.append(row)

    n = len(questions)

    def paired(a: str, b: str) -> tuple[list[int], int]:
        values = [int(r[a]) - int(r[b]) for r in rows if r[a] is not None and r[b] is not None]
        return values, n - len(values)

    def acc(key: str) -> str:
        values = [r[key] for r in rows if r[key] is not None]
        return f"{100 * mean(values):.2f}% (n={len(values)})" if values else "n/a"

    def line(label: str, values: list[int], dropped: int, offset: int) -> list[str]:
        if not values:
            return [f"{label}: no complete pairs"]
        delta, lower, upper = interval(values, draws, seed + offset)
        moves = Counter(values)
        return [f"{label}: {100 * delta:+.2f} pp  [95% CI {100 * lower:+.2f}, {100 * upper:+.2f}]",
                f"    first right, second wrong: {moves[1]} | second right, first wrong: {moves[-1]}"
                f" | pairs: {len(values)} | dropped: {dropped}"]

    primary, primary_dropped = paired("jev_alone", "matched")
    evaluable = primary_dropped / n <= spec["maximum_missing_fraction"]
    lines = [
        "FOLLOW-UP STUDY - LOCKED ANALYSIS", "=" * 40,
        f"Freeze: {spec['freeze_id']}", f"Questions: {n}",
        f"Primary evaluable: {'YES' if evaluable else 'NO'} ({primary_dropped} questions missing)",
        f"Failed calls: {failures}", "",
        "ACCURACY",
        f"D  JEV alone: {acc('jev_alone')}",
        f"F  Delphi, original small council: {acc('small')}",
        f"F  Delphi, strength-matched council: {acc('matched')}",
        f"G  Delphi, matched council plus JEV as a candidate: {acc('seat')}",
        f"C  Matched council, simple majority: {acc('matched_vote')}", "",
        "PRIMARY (pre-registered)",
        *line("JEV alone minus matched-council Delphi", primary, primary_dropped, 0), "",
        "KEY SECONDARY",
        *line("JEV alone minus small-council Delphi (replication)", *paired("jev_alone", "small"), 1),
        *line("JEV-as-candidate Delphi minus JEV alone", *paired("seat", "jev_alone"), 2),
        *line("Matched-council Delphi minus matched majority", *paired("matched", "matched_vote"), 3),
        *line("Matched-council Delphi minus small-council Delphi (does strength help?)",
              *paired("matched", "small"), 4),
        "", "PROCESS",
    ]
    for prefix in ("small", "matched", "seat"):
        asked = [r for r in rows if r[f"{prefix}_reconsider"] is not None]
        recon = [r for r in asked if r[f"{prefix}_reconsider"]]
        flipped_wrong = [r for r in recon if r[f"{prefix}_controller_right"] and r[prefix] is False]
        flipped_right = [r for r in recon if r[f"{prefix}_controller_right"] is False and r[prefix]]
        lines.append(f"{prefix}: reconsideration on {len(recon)}/{len(asked)}; "
                     f"right-to-wrong {len(flipped_wrong)}, wrong-to-right {len(flipped_right)}")
    available = [r for r in rows if r["matched_available"] and r["matched"] is not None]
    lines += [
        f"Matched council: a correct candidate existed on "
        f"{sum(1 for r in rows if r['matched_available'])}/{n}",
        f"Matched Delphi accuracy when a correct candidate existed: "
        + (f"{100 * mean(r['matched'] for r in available):.2f}%" if available else "n/a"),
        f"G: final answer equals JEV's own answer on "
        f"{sum(1 for r in rows if r['seat_kept'])}/{sum(1 for r in rows if r['seat_kept'] is not None)}",
        "", "COUNCIL MODELS: FIRST SAMPLE -> OWN CROWD",
    ]
    for arm in ("small", "matched"):
        for provider in PROVIDERS:
            first = [r[f"{arm}_first"][provider] for r in rows if provider in r[f"{arm}_first"]]
            crowd = [r[f"{arm}_crowd"][provider] for r in rows if provider in r[f"{arm}_crowd"]]
            if first and crowd:
                lines.append(f"{arm} {provider} {spec['arms'][arm][provider]}: "
                             f"{100 * mean(first):.2f}% -> {100 * mean(crowd):.2f}%")
    lines += ["", f"Recorded spend: ${spend:.4f} (frozen cap ${spec['max_recorded_cost_usd']:.2f})"]
    for amendment in cap_amendments:
        lines.append(f"Cap raised on {amendment['date']} from ${amendment['previous_cap_usd']:.2f} to "
                     f"${amendment['new_cap_usd']:.2f} at ${amendment['spend_at_amendment_usd']:.2f} spent: "
                     f"{amendment['reason']}")
    lines += ["By condition: " + ", ".join(f"{k} ${v:.4f}" for k, v in sorted(spend_by.items()))]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/followup_v1.json")
    parser.add_argument("--db", default="results/followup-v1.sqlite3")
    parser.add_argument("--output", default="results/followup-analysis-v1.txt")
    args = parser.parse_args()
    spec, freeze_hash = load_spec(args.config)
    require_frozen(spec)
    report = analyse(spec, freeze_hash, args.db)
    print(report, end="")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(report, encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        raise SystemExit(f"Stopped: {error}") from None
