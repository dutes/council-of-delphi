"""Locked paired analysis for the active Delphi confirmatory study."""

from __future__ import annotations

import argparse
import random
import sqlite3
from pathlib import Path
from statistics import mean

from active_delphi.models import ActiveOutcome
from analyze_evidence_study import plurality
from arbiter_study.models import ModelAnswer
from evidence_study.models import EvidenceDecision
from run_active_delphi_confirmatory import load_frozen


def interval(values: list[int], draws: int, seed: int):
    rng = random.Random(seed)
    estimates = sorted(mean(rng.choice(values) for _ in values) for _ in range(draws))
    return mean(values), estimates[int(.025 * draws)], estimates[int(.975 * draws) - 1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/active_delphi_confirmatory_v1.json")
    parser.add_argument("--baseline-db", default="results/active-confirmatory-baselines-v1.sqlite3")
    parser.add_argument("--active-db", default="results/active-confirmatory-controller-v1.sqlite3")
    parser.add_argument("--output", default="results/active-delphi-confirmatory-analysis-v1.txt")
    args = parser.parse_args()
    spec, _, questions, freeze_hash = load_frozen(Path(args.config))
    bdb = sqlite3.connect(Path(args.baseline_db).resolve().as_uri()+"?mode=ro", uri=True)
    adb = sqlite3.connect(Path(args.active_db).resolve().as_uri()+"?mode=ro", uri=True)
    for db in (bdb, adb):
        row = db.execute("SELECT value FROM meta WHERE key='freeze_hash'").fetchone()
        if not row or row[0] != freeze_hash:
            raise RuntimeError("Database does not belong to this freeze")
    rows = []
    for question in questions:
        reports = [ModelAnswer.model_validate_json(row[0]) for row in bdb.execute(
            "SELECT payload FROM specialists WHERE question_id=? ORDER BY provider", (question.id,)
        )]
        decisions = {condition: EvidenceDecision.model_validate_json(payload) for condition, payload in bdb.execute(
            "SELECT condition,payload FROM decisions WHERE question_id=?", (question.id,)
        )}
        outrow = adb.execute("SELECT payload FROM outcomes WHERE question_id=?", (question.id,)).fetchone()
        if len(reports) != 3 or len(decisions) != 3 or not outrow:
            continue
        active = ActiveOutcome.model_validate_json(outrow[0])
        rows.append({
            "question": decisions["question_only"].selected_answer_label == question.correct_label,
            "vote": plurality(question.id, [r.answer_label for r in reports], spec["vote_seed"]) == question.correct_label,
            "reports": decisions["report_synthesis"].selected_answer_label == question.correct_label,
            "raw": decisions["raw_evidence"].selected_answer_label == question.correct_label,
            "active": active.selected_answer_label == question.correct_label,
            "path": active.status == "complete" and len(active.accepted_evidence_ids) == 3,
            "support": set(active.accepted_evidence_ids) == set(question.support_ids),
        })
    n = len(rows)
    if not n:
        raise RuntimeError("No complete paired questions")
    evaluable = (len(questions)-n)/len(questions) <= spec["maximum_missing_fraction"]
    effects = {
        "PRIMARY active minus one-round reports": [int(r["active"])-int(r["reports"]) for r in rows],
        "Active minus specialist vote": [int(r["active"])-int(r["vote"]) for r in rows],
        "Active minus question-only": [int(r["active"])-int(r["question"]) for r in rows],
        "Raw evidence minus active": [int(r["raw"])-int(r["active"]) for r in rows],
    }
    lines = [
        "ACTIVE DELPHI CONFIRMATORY STUDY - LOCKED ANALYSIS", "="*55,
        f"Freeze: {spec['freeze_id']}", f"Complete paired questions: {n}/{len(questions)}",
        f"Primary evaluable: {'YES' if evaluable else 'NO'}", "", "ANSWER ACCURACY",
    ]
    for key, label in [("question","JEV question-only"),("vote","Specialist vote"),
                       ("reports","One-round JEV synthesis"),("active","Active JEV-classified retrieval"),
                       ("raw","JEV all raw evidence")]:
        lines.append(f"{label}: {100*mean(r[key] for r in rows):.2f}%")
    lines.extend(["", "PAIRED EFFECTS"])
    for index, (name, values) in enumerate(effects.items()):
        est, low, high = interval(values, spec["bootstrap_draws"], spec["analysis_seed"]+index)
        lines.append(f"{name}: {100*est:+.2f} pp [{100*low:+.2f}, {100*high:+.2f}]")
    lines.extend([
        "", "ACTIVE-PROCESS AUDIT",
        f"Complete three-link path: {sum(r['path'] for r in rows)}/{n} ({100*mean(r['path'] for r in rows):.2f}%)",
        f"Accepted path exactly equals true support: {sum(r['support'] for r in rows)}/{n} ({100*mean(r['support'] for r in rows):.2f}%)",
        "", f"Failed calls: {bdb.execute('SELECT COUNT(*) FROM calls WHERE success=0').fetchone()[0] + adb.execute('SELECT COUNT(*) FROM calls WHERE success=0').fetchone()[0]}",
        f"Recorded spend: ${bdb.execute('SELECT COALESCE(SUM(cost),0) FROM calls').fetchone()[0] + adb.execute('SELECT COALESCE(SUM(cost),0) FROM calls').fetchone()[0]:.4f}",
    ])
    report = "\n".join(lines)+"\n"
    Path(args.output).write_text(report, encoding="utf-8")
    print(report, end="")
    bdb.close(); adb.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

