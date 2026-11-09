"""Exploratory diagnostics; not part of the frozen evidence-study analysis."""

import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

from arbiter_study.models import ModelAnswer
from evidence_study.models import EvidenceDecision, EvidenceQuestion


questions = {
    q.id: q for q in (
        EvidenceQuestion.model_validate_json(line)
        for line in Path("data/evidence_partitioned_300.jsonl").read_text(encoding="utf-8").splitlines()
    )
}
db = sqlite3.connect("results/evidence-study-v1.sqlite3")
provider_support = Counter()
provider_correct = Counter()
reported_support_count = Counter()
selected = {name: Counter() for name in ("question_only", "report_synthesis", "raw_evidence")}
raw_unique_citations = Counter()

for question_id, question in questions.items():
    reports = [ModelAnswer.model_validate_json(row[0]) for row in db.execute(
        "SELECT payload FROM specialists WHERE question_id=?", (question_id,)
    )]
    reported_support = set()
    for report in reports:
        ids = set()
        for item in report.evidence:
            match = re.match(r"\s*(E\d{2})\s*:", item)
            if match:
                ids.add(match.group(1))
        own_support = {f.evidence_id for f in question.facts_for(report.provider) if f.is_support}
        provider_support[report.provider] += bool(ids & own_support)
        provider_correct[report.provider] += report.answer_label == question.correct_label
        reported_support |= ids & set(question.support_ids)
    reported_support_count[len(reported_support)] += 1
    for condition in selected:
        row = db.execute(
            "SELECT payload FROM decisions WHERE question_id=? AND condition=?",
            (question_id, condition),
        ).fetchone()
        decision = EvidenceDecision.model_validate_json(row[0])
        selected[condition][decision.selected_answer_label] += 1
        if condition == "raw_evidence":
            raw_unique_citations[len(decision.cited_evidence_ids)] += 1

result = {
    "provider_support_recall_counts_of_300": dict(provider_support),
    "provider_answer_correct_counts_of_300": dict(provider_correct),
    "questions_by_number_of_support_links_in_reports": dict(sorted(reported_support_count.items())),
    "selected_label_counts": {name: dict(counts) for name, counts in selected.items()},
    "raw_evidence_unique_citation_count_distribution": dict(sorted(raw_unique_citations.items())),
}
print(json.dumps(result, indent=2, sort_keys=True))
