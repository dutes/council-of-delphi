from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from active_delphi.models import ActiveOutcome, JEVAction
from arbiter_study.models import ModelAnswer


class ActiveStore:
    def __init__(self, path: str | Path, freeze_hash: str):
        self.db = sqlite3.connect(path)
        with self.db:
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS retrievals (
                    question_id TEXT NOT NULL, stage_index INTEGER NOT NULL,
                    attempt INTEGER NOT NULL, provider TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(question_id,stage_index,attempt,provider));
                CREATE TABLE IF NOT EXISTS actions (
                    question_id TEXT NOT NULL, stage_index INTEGER NOT NULL,
                    attempt INTEGER NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(question_id,stage_index,attempt));
                CREATE TABLE IF NOT EXISTS outcomes (
                    question_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, question_id TEXT NOT NULL,
                    stage TEXT NOT NULL, member_id TEXT, success INTEGER NOT NULL,
                    cost REAL, error TEXT);
            """)
            old = self.db.execute("SELECT value FROM meta WHERE key='freeze_hash'").fetchone()
            if old and old[0] != freeze_hash:
                raise RuntimeError("Database belongs to another freeze")
            self.db.execute("INSERT OR IGNORE INTO meta VALUES ('freeze_hash',?)", (freeze_hash,))

    def retrievals(self, question_id: str, stage: int, attempt: int) -> list[ModelAnswer]:
        return [ModelAnswer.model_validate_json(row[0]) for row in self.db.execute(
            "SELECT payload FROM retrievals WHERE question_id=? AND stage_index=? AND attempt=? ORDER BY provider",
            (question_id, stage, attempt),
        )]

    def save_retrieval(self, question_id: str, stage: int, attempt: int, answer: ModelAnswer) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO retrievals VALUES (?,?,?,?,?)", (
                question_id, stage, attempt, answer.provider, answer.model_dump_json(),
            ))
            self.db.execute("INSERT INTO calls(question_id,stage,member_id,success,cost) VALUES (?,?,?,1,?)", (
                question_id, f"retrieve_{stage}_{attempt}", answer.provider, answer.estimated_cost_usd,
            ))

    def action(self, question_id: str, stage: int, attempt: int) -> JEVAction | None:
        row = self.db.execute(
            "SELECT payload FROM actions WHERE question_id=? AND stage_index=? AND attempt=?",
            (question_id, stage, attempt),
        ).fetchone()
        return JEVAction.model_validate_json(row[0]) if row else None

    def save_action(self, question_id: str, action: JEVAction) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO actions VALUES (?,?,?,?)", (
                question_id, action.stage_index, action.attempt, action.model_dump_json(),
            ))
            self.db.execute("INSERT INTO calls(question_id,stage,member_id,success,cost) VALUES (?,?,NULL,1,?)", (
                question_id, f"jev_{action.stage_index}_{action.attempt}", action.estimated_cost_usd,
            ))

    def outcome(self, question_id: str) -> ActiveOutcome | None:
        row = self.db.execute("SELECT payload FROM outcomes WHERE question_id=?", (question_id,)).fetchone()
        return ActiveOutcome.model_validate_json(row[0]) if row else None

    def save_outcome(self, question_id: str, outcome: ActiveOutcome) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO outcomes VALUES (?,?)", (question_id, outcome.model_dump_json()))

    def save_failure(self, question_id: str, stage: str, member_id: str | None, error: Exception) -> None:
        message = f"{type(error).__name__}: {error}"
        raw = getattr(error, "raw", None)
        if raw is not None:
            message += " | raw=" + json.dumps(raw)[:1500]
        with self.db:
            self.db.execute(
                "INSERT INTO calls(question_id,stage,member_id,success,error) VALUES (?,?,?,0,?)",
                (question_id, stage, member_id, message),
            )

    def complete_count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]

    def cost(self) -> float:
        return float(self.db.execute("SELECT COALESCE(SUM(cost),0) FROM calls").fetchone()[0])

    def failures(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM calls WHERE success=0").fetchone()[0]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.db.close()

