from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from arbiter_study.models import ModelAnswer
from evidence_study.models import EvidenceDecision


class EvidenceStore:
    def __init__(self, path: str | Path, freeze_hash: str):
        self.db = sqlite3.connect(path)
        with self.db:
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS specialists (
                    question_id TEXT NOT NULL, provider TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(question_id,provider));
                CREATE TABLE IF NOT EXISTS decisions (
                    question_id TEXT NOT NULL, condition TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(question_id,condition));
                CREATE TABLE IF NOT EXISTS calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, question_id TEXT NOT NULL,
                    stage TEXT NOT NULL, member_id TEXT, success INTEGER NOT NULL,
                    cost REAL, error TEXT);
            """)
            old = self.db.execute("SELECT value FROM meta WHERE key='freeze_hash'").fetchone()
            if old and old[0] != freeze_hash:
                raise RuntimeError("Database belongs to another freeze")
            self.db.execute("INSERT OR IGNORE INTO meta VALUES ('freeze_hash',?)", (freeze_hash,))

    def specialist(self, question_id: str, provider: str) -> ModelAnswer | None:
        row = self.db.execute(
            "SELECT payload FROM specialists WHERE question_id=? AND provider=?",
            (question_id, provider),
        ).fetchone()
        return ModelAnswer.model_validate_json(row[0]) if row else None

    def specialists(self, question_id: str) -> list[ModelAnswer]:
        return [ModelAnswer.model_validate_json(row[0]) for row in self.db.execute(
            "SELECT payload FROM specialists WHERE question_id=? ORDER BY provider", (question_id,)
        )]

    def decision(self, question_id: str, condition: str) -> EvidenceDecision | None:
        row = self.db.execute(
            "SELECT payload FROM decisions WHERE question_id=? AND condition=?",
            (question_id, condition),
        ).fetchone()
        return EvidenceDecision.model_validate_json(row[0]) if row else None

    def attempts(self, question_id: str, stage: str, member_id: str | None) -> int:
        return self.db.execute(
            "SELECT COUNT(*) FROM calls WHERE question_id=? AND stage=? AND member_id IS ?",
            (question_id, stage, member_id),
        ).fetchone()[0]

    def save_specialist(self, question_id: str, answer: ModelAnswer) -> None:
        with self.db:
            self.db.execute("INSERT INTO specialists VALUES (?,?,?)", (
                question_id, answer.provider, answer.model_dump_json(),
            ))
            self.db.execute(
                "INSERT INTO calls(question_id,stage,member_id,success,cost) VALUES (?,?,?,1,?)",
                (question_id, "specialist", answer.provider, answer.estimated_cost_usd),
            )

    def save_decision(self, question_id: str, decision: EvidenceDecision) -> None:
        with self.db:
            self.db.execute("INSERT INTO decisions VALUES (?,?,?)", (
                question_id, decision.condition, decision.model_dump_json(),
            ))
            self.db.execute(
                "INSERT INTO calls(question_id,stage,member_id,success,cost) VALUES (?,?,NULL,1,?)",
                (question_id, decision.condition, decision.estimated_cost_usd),
            )

    def save_failure(self, question_id: str, stage: str, member_id: str | None,
                     error: Exception) -> None:
        message = f"{type(error).__name__}: {error}"
        raw = getattr(error, "raw", None)
        if raw is not None:
            message += " | raw=" + json.dumps(raw)[:1500]
        with self.db:
            self.db.execute(
                "INSERT INTO calls(question_id,stage,member_id,success,error) VALUES (?,?,?,0,?)",
                (question_id, stage, member_id, message),
            )

    def complete(self, question_id: str) -> bool:
        specialists = self.db.execute(
            "SELECT COUNT(*) FROM specialists WHERE question_id=?", (question_id,)
        ).fetchone()[0]
        decisions = self.db.execute(
            "SELECT COUNT(*) FROM decisions WHERE question_id=?", (question_id,)
        ).fetchone()[0]
        return specialists == 3 and decisions == 3

    def complete_count(self) -> int:
        return self.db.execute("""
            SELECT COUNT(*) FROM (
                SELECT question_id FROM specialists GROUP BY question_id HAVING COUNT(*)=3
            ) s JOIN (
                SELECT question_id FROM decisions GROUP BY question_id HAVING COUNT(*)=3
            ) d USING(question_id)
        """).fetchone()[0]

    def failures(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM calls WHERE success=0").fetchone()[0]

    def cost(self) -> float:
        return float(self.db.execute("SELECT COALESCE(SUM(cost),0) FROM calls").fetchone()[0])

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.db.close()
