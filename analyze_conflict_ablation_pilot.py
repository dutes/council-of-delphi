"""Evaluate the frozen engineering gates for the conflicting-evidence pilot."""

from __future__ import annotations

import argparse
import sqlite3
from collections import Counter
from pathlib import Path

from conflict_ablation.models import ArbiterDecision
from run_conflict_ablation_pilot import IMPLEMENTATION_FILES
from run_conflict_ablation import load_frozen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/conflict_ablation_pilot_v1.json")
    parser.add_argument("--db", default="results/conflict-ablation-pilot-v1.sqlite3")
    parser.add_argument("--output", default="results/conflict-ablation-pilot-analysis-v1.txt")
    args = parser.parse_args()
    spec, _, questions, freeze_hash = load_frozen(Path(args.config), IMPLEMENTATION_FILES)
    db = sqlite3.connect(args.db)
    stored = db.execute("SELECT value FROM meta WHERE key='freeze_hash'").fetchone()
    if not stored or stored[0] != freeze_hash: raise RuntimeError("Wrong freeze database")
    correct = Counter(); totals = Counter(); complete = 0; positions = Counter()
    for question in questions:
        decisions = {(stage, arbiter): ArbiterDecision.model_validate_json(payload)
                     for stage, arbiter, payload in db.execute(
                         "SELECT stage_index,arbiter,payload FROM decisions WHERE question_id=?", (question.id,))}
        complete += len(decisions) == 12
        for stage in question.stages:
            winner = next(c for c in stage.candidates if c.is_correct)
            positions[winner.candidate_id] += 1
            for arbiter in ("hash_tie","keyword_rule","openai","jev"):
                decision = decisions.get((stage.stage_index, arbiter))
                if decision:
                    totals[arbiter] += 1
                    correct[arbiter] += decision.selected_candidate_id == winner.candidate_id
    gates = {
        "complete_at_least_29": complete >= 29,
        "openai_at_least_81_of_90": correct["openai"] >= 81,
        "jev_at_least_81_of_90": correct["jev"] >= 81,
        "positions_exactly_30_each": positions == {"C1":30,"C2":30,"C3":30},
    }
    lines = ["CONFLICTING-EVIDENCE ABLATION PILOT", f"Freeze: {spec['freeze_id']}",
             "Pilot is excluded from confirmatory inference.", "", f"Complete: {complete}/30"]
    lines += [f"{name}: {correct[name]}/{totals[name]}" for name in ("hash_tie","keyword_rule","openai","jev")]
    lines += ["", "ENGINEERING GATES"] + [f"{'PASS' if value else 'FAIL'}: {name}" for name,value in gates.items()]
    lines += ["", f"OVERALL: {'PASS' if all(gates.values()) else 'FAIL'}",
              f"Failed calls: {db.execute('SELECT COUNT(*) FROM calls WHERE success=0').fetchone()[0]}",
              f"Recorded spend: ${db.execute('SELECT COALESCE(SUM(cost),0) FROM calls').fetchone()[0]:.4f}"]
    report = "\n".join(lines)+"\n"; Path(args.output).write_text(report,encoding="utf-8"); print(report,end="")
    db.close(); return 0


if __name__ == "__main__": raise SystemExit(main())

