"""Locked analysis for the evidence-partitioned JEV study."""

from __future__ import annotations

import argparse
import hashlib
import random
import re
import sqlite3
from pathlib import Path
from statistics import mean

from arbiter_study.models import ModelAnswer
from evidence_study.models import EvidenceDecision
from run_evidence_study import CONDITIONS, load_frozen


def plurality(question_id: str, labels: list[str], seed: int) -> str:
    counts = {label: labels.count(label) for label in set(labels)}
    best = max(counts.values())
    tied = [label for label, count in counts.items() if count == best]
    return min(tied, key=lambda label: hashlib.sha256(
        f"vote:{seed}:{question_id}:{label}".encode()
    ).hexdigest())


def ci(values: list[int], draws: int, seed: int):
    rng = random.Random(seed)
    estimates = sorted(mean(rng.choice(values) for _ in values) for _ in range(draws))
    return mean(values), estimates[int(.025 * draws)], estimates[int(.975 * draws) - 1]


def cited_ids(answer: ModelAnswer) -> set[str]:
    result = set()
    for item in answer.evidence:
        match = re.match(r"\s*(E\d{2})\s*:", item)
        if match:
            result.add(match.group(1))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/evidence_study_v1.json")
    parser.add_argument("--db", default="results/evidence-study-v1.sqlite3")
    parser.add_argument("--output", default="results/evidence-final-analysis-v1.txt")
    args = parser.parse_args()
    spec, _, questions, freeze_hash = load_frozen(Path(args.config))
    rows = []
    with sqlite3.connect(Path(args.db).resolve().as_uri() + "?mode=ro", uri=True) as db:
        stored = db.execute("SELECT value FROM meta WHERE key='freeze_hash'").fetchone()
        if not stored or stored[0] != freeze_hash:
            raise RuntimeError("Database does not belong to this freeze")
        failures = db.execute("SELECT COUNT(*) FROM calls WHERE success=0").fetchone()[0]
        spend = float(db.execute("SELECT COALESCE(SUM(cost),0) FROM calls").fetchone()[0])
        for question in questions:
            specialists = [ModelAnswer.model_validate_json(row[0]) for row in db.execute(
                "SELECT payload FROM specialists WHERE question_id=? ORDER BY provider", (question.id,)
            )]
            decisions = {}
            for condition in CONDITIONS:
                row = db.execute(
                    "SELECT payload FROM decisions WHERE question_id=? AND condition=?",
                    (question.id, condition),
                ).fetchone()
                if row:
                    decisions[condition] = EvidenceDecision.model_validate_json(row[0])
            if len(specialists) != 3 or len(decisions) != 3:
                missing_providers = {
                    "openai", "anthropic", "mistral"
                } - {answer.provider for answer in specialists}
                specialists_terminal = bool(missing_providers) and all(
                    db.execute(
                        "SELECT COUNT(*) FROM calls WHERE question_id=? AND stage='specialist' AND member_id=?",
                        (question.id, provider),
                    ).fetchone()[0] >= spec["max_attempts_per_stage"]
                    for provider in missing_providers
                )
                missing_conditions = set(CONDITIONS) - set(decisions)
                decisions_terminal = len(specialists) == 3 and bool(missing_conditions) and all(
                    db.execute(
                        "SELECT COUNT(*) FROM calls WHERE question_id=? AND stage=? AND member_id IS NULL",
                        (question.id, condition),
                    ).fetchone()[0] >= spec["max_attempts_per_stage"]
                    for condition in missing_conditions
                )
                if not (specialists_terminal or decisions_terminal):
                    raise RuntimeError("Study is still in progress; final analysis is locked")
                continue
            support = set(question.support_ids)
            all_ids = {fact.evidence_id for fact in question.facts}
            reported = set().union(*(cited_ids(answer) for answer in specialists))
            valid_citations = sum(
                len(cited_ids(answer) & {fact.evidence_id for fact in question.facts_for(answer.provider)})
                for answer in specialists
            )
            total_citations = sum(len(cited_ids(answer)) for answer in specialists)
            own_support_recalled = sum(
                bool(cited_ids(answer) & support) for answer in specialists
            )
            report_decision = decisions["report_synthesis"]
            raw_decision = decisions["raw_evidence"]
            rows.append({
                "question_only": decisions["question_only"].selected_answer_label == question.correct_label,
                "vote": plurality(question.id, [a.answer_label for a in specialists], spec["vote_seed"]) == question.correct_label,
                "reports": report_decision.selected_answer_label == question.correct_label,
                "raw": raw_decision.selected_answer_label == question.correct_label,
                "report_complete": support <= set(report_decision.cited_evidence_ids),
                "raw_complete": support <= set(raw_decision.cited_evidence_ids),
                "report_precision_num": len(set(report_decision.cited_evidence_ids) & support),
                "report_precision_den": len(report_decision.cited_evidence_ids),
                "raw_precision_num": len(set(raw_decision.cited_evidence_ids) & support),
                "raw_precision_den": len(raw_decision.cited_evidence_ids),
                "availability": support <= reported,
                "specialist_valid_num": valid_citations,
                "specialist_valid_den": total_citations,
                "specialist_support_recalled": own_support_recalled,
                "all_citations_exist": set(report_decision.cited_evidence_ids) <= all_ids,
            })
    n = len(rows)
    missing = len(questions) - n
    evaluable = missing / len(questions) <= spec["maximum_missing_fraction"]
    primary = [int(r["reports"]) - int(r["question_only"]) for r in rows]
    versus_vote = [int(r["reports"]) - int(r["vote"]) for r in rows]
    raw_gap = [int(r["raw"]) - int(r["reports"]) for r in rows]
    p = ci(primary, spec["bootstrap_draws"], spec["analysis_seed"])
    v = ci(versus_vote, spec["bootstrap_draws"], spec["analysis_seed"] + 1)
    g = ci(raw_gap, spec["bootstrap_draws"], spec["analysis_seed"] + 2)

    def pct(key):
        return 100 * mean(r[key] for r in rows)

    specialist_den = sum(r["specialist_valid_den"] for r in rows)
    report_den = sum(r["report_precision_den"] for r in rows)
    raw_den = sum(r["raw_precision_den"] for r in rows)
    lines = [
        "EVIDENCE-PARTITIONED JEV STUDY - FINAL LOCKED ANALYSIS", "=" * 59,
        f"Freeze: {spec['freeze_id']}", f"Complete: {n}/{len(questions)}",
        f"Primary evaluable: {'YES' if evaluable else 'NO'}", f"Failed calls: {failures}", "",
        "ANSWER ACCURACY",
        f"JEV question-only: {pct('question_only'):.2f}%",
        f"Evidence-limited specialist vote: {pct('vote'):.2f}%",
        f"JEV report synthesis: {pct('reports'):.2f}%",
        f"JEV all raw evidence: {pct('raw'):.2f}%", "",
        "PAIRED EFFECTS",
        f"PRIMARY reports minus question-only: {100*p[0]:+.2f} pp [{100*p[1]:+.2f}, {100*p[2]:+.2f}]",
        f"Reports minus specialist vote: {100*v[0]:+.2f} pp [{100*v[1]:+.2f}, {100*v[2]:+.2f}]",
        f"Raw evidence minus reports: {100*g[0]:+.2f} pp [{100*g[1]:+.2f}, {100*g[2]:+.2f}]", "",
        "AUDITABILITY",
        f"All support links available in reports: {sum(r['availability'] for r in rows)}/{n} ({pct('availability'):.2f}%)",
        f"Specialist own-support recall: {100*sum(r['specialist_support_recalled'] for r in rows)/(3*n):.2f}%",
        f"Specialist citation validity: {100*sum(r['specialist_valid_num'] for r in rows)/specialist_den:.2f}%" if specialist_den else "Specialist citation validity: unavailable",
        f"JEV report complete-proof rate: {pct('report_complete'):.2f}%",
        f"JEV raw complete-proof rate: {pct('raw_complete'):.2f}%",
        f"JEV report evidence precision: {100*sum(r['report_precision_num'] for r in rows)/report_den:.2f}%" if report_den else "JEV report evidence precision: unavailable",
        f"JEV raw evidence precision: {100*sum(r['raw_precision_num'] for r in rows)/raw_den:.2f}%" if raw_den else "JEV raw evidence precision: unavailable",
        f"Report citations all reference dataset IDs: {sum(r['all_citations_exist'] for r in rows)}/{n}", "",
        f"Recorded spend: ${spend:.4f}",
    ]
    report = "\n".join(lines) + "\n"
    print(report, end="")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
