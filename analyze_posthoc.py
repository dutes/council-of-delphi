"""Post-hoc comparison for the frozen crowd-to-council JEV study.

This was added after the locked analysis and was NOT pre-registered. It asks a
question the locked report shows the inputs for but doesn't test directly: does
the full JEV-controlled Delphi procedure beat JEV answering on its own?

It lives in its own file so the frozen implementation hash (which covers
analyze_study.py) is untouched. It reads the stored results only and makes no
API calls.
"""

from __future__ import annotations

import argparse
import sqlite3
from collections import Counter
from pathlib import Path
from statistics import mean

from analyze_study import interval, read_models
from arbiter_study.models import Arbitration
from run_study import load_frozen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/study_v1.json")
    parser.add_argument("--db", default="results/arbiter-study-v5.sqlite3")
    parser.add_argument("--output", default="results/posthoc-analysis-v5.txt")
    args = parser.parse_args()

    spec, _config, questions, freeze_hash = load_frozen(Path(args.config))
    deltas = []
    alone_correct = []
    delphi_correct = []
    with sqlite3.connect(Path(args.db).resolve().as_uri() + "?mode=ro", uri=True) as db:
        stored = db.execute("SELECT value FROM meta WHERE key='freeze_hash'").fetchone()
        if not stored or stored[0] != freeze_hash:
            raise RuntimeError("Database is not from this freeze")
        for question in questions:
            final = read_models(db, "decisions", question.id, "delphi_final", Arbitration)
            if final is None:
                continue  # incomplete questions are excluded, as in the locked analysis
            direct = read_models(db, "decisions", question.id, "jev_alone", Arbitration)
            if direct is None:
                raise RuntimeError(f"Completed question {question.id} lacks a JEV-alone answer")
            alone = direct.selected_answer_label == question.correct_label
            delphi = final.selected_answer_label == question.correct_label
            alone_correct.append(alone)
            delphi_correct.append(delphi)
            deltas.append(int(alone) - int(delphi))

    if not deltas:
        raise RuntimeError("No completed questions")
    delta, lower, upper = interval(deltas, spec["bootstrap_draws"], spec["analysis_seed"] + 3)
    transitions = Counter(deltas)
    lines = [
        "JEV CROWD-COUNCIL STUDY - POST-HOC COMPARISON (NOT PRE-REGISTERED)",
        "=" * 66,
        f"Freeze: {spec['freeze_id']}",
        f"Questions compared: {len(deltas)}/{len(questions)}",
        "",
        f"JEV alone: {100*mean(alone_correct):.2f}%",
        f"Full JEV-controlled Delphi: {100*mean(delphi_correct):.2f}%",
        f"JEV alone minus full Delphi: {100*delta:+.2f} pp",
        f"Bootstrap 95% interval: [{100*lower:+.2f}, {100*upper:+.2f}] pp",
        f"JEV alone right, Delphi wrong: {transitions[1]}",
        f"Delphi right, JEV alone wrong: {transitions[-1]}",
    ]
    report = "\n".join(lines) + "\n"
    print(report, end="")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
