"""Condition G: JEV's own answer as one anonymised candidate.

JEV's answer from condition D becomes a position with one vote and no rationale,
shaped like any council position so nothing marks it as the judge's. If it
matches a council answer, it joins that candidate's support, because
candidates are grouped by answer label.
"""

from __future__ import annotations

from arbiter_study.models import Arbitration, ProviderPosition

SEAT = "seat"


def seat_position(direct: Arbitration, stage: str = "initial") -> ProviderPosition:
    label = direct.selected_answer_label
    return ProviderPosition(
        position_id=f"{SEAT}-{stage}-position", provider=SEAT, stage=stage,
        answer_label=label, label_counts={label: 1},
        samples=[{"answer_label": label, "confidence": None, "rationale": "", "evidence": []}],
    )
