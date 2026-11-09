"""Analyze the frozen engineering gates for the active Delphi pilot."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path

from active_delphi.models import ActiveOutcome, ActiveQuestion, JEVAction


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/active_delphi_pilot_v1.json")
    parser.add_argument("--db", default="results/active-delphi-pilot-v1.sqlite3")
    parser.add_argument("--output", default="results/active-delphi-pilot-analysis-v1.txt")
    args = parser.parse_args()
    spec = json.loads(Path(args.config).read_text(encoding="utf-8"))
    questions = [ActiveQuestion.model_validate_json(line) for line in Path(
        spec["dataset_path"]
    ).read_text(encoding="utf-8").splitlines() if line]
    by_id = {question.id: question for question in questions}
    db = sqlite3.connect(args.db)
    outcomes = {
        qid: ActiveOutcome.model_validate_json(payload)
        for qid, payload in db.execute("SELECT question_id,payload FROM outcomes")
    }
    actions = [
        (qid, JEVAction.model_validate_json(payload))
        for qid, payload in db.execute("SELECT question_id,payload FROM actions")
    ]
    complete = sum(outcome.status == "complete" for outcome in outcomes.values())
    correct = sum(
        outcome.selected_answer_label == by_id[qid].correct_label
        for qid, outcome in outcomes.items()
    )
    accepted = [(qid, action) for qid, action in actions if action.accepted_evidence_id]
    valid = sum(action.accepted_evidence_id in action.candidate_ids for _, action in accepted)
    precision = valid / len(accepted) if accepted else 0.0
    support_accepts = sum(
        bool(by_id[qid].fact(action.accepted_evidence_id).is_support)
        for qid, action in accepted
    )
    ownership = Counter()
    for question in questions:
        ownership.update((relation, provider) for relation, provider in question.link_owners.items())
    gates = {
        "terminal_outcomes_at_least_29": len(outcomes) >= 29,
        "complete_paths_at_least_27": complete >= 27,
        "correct_answers_at_least_27": correct >= 27,
        "ownership_max_five_per_position": max(ownership.values()) <= 5,
        "accepted_citation_validity_at_least_95pct": precision >= 0.95,
    }
    lines = [
        "ACTIVE DELPHI CLASSIFIER PILOT - ENGINEERING ANALYSIS",
        f"Freeze: {spec['freeze_id']}",
        "Pilot data are excluded from later confirmatory inference.", "",
        f"Terminal outcomes: {len(outcomes)}/{len(questions)}",
        f"Complete three-link paths: {complete}/{len(questions)} ({complete/len(questions):.2%})",
        f"Correct final answers: {correct}/{len(questions)} ({correct/len(questions):.2%})",
        f"Accepted evidence actions: {len(accepted)}",
        f"Accepted citation validity: {valid}/{len(accepted)} ({precision:.2%})" if accepted else "Accepted citation validity: n/a",
        f"Accepted true support links (diagnostic): {support_accepts}/{len(accepted)}" if accepted else "Accepted true support links: n/a",
        f"Recorded spend: ${db.execute('SELECT COALESCE(SUM(cost),0) FROM calls').fetchone()[0]:.4f}",
        f"Failed calls: {db.execute('SELECT COUNT(*) FROM calls WHERE success=0').fetchone()[0]}", "",
        "FROZEN ENGINEERING GATES",
    ]
    lines.extend(f"{'PASS' if passed else 'FAIL'}: {name}" for name, passed in gates.items())
    lines.extend(["", f"OVERALL: {'PASS' if all(gates.values()) else 'FAIL'}"])
    output = "\n".join(lines) + "\n"
    Path(args.output).write_text(output, encoding="utf-8")
    print(output)
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

