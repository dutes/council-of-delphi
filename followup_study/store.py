"""SQLite storage for the follow-up study.

Unlike the first study's store, every answer, position and decision is filed
under an explicit stage key such as ``matched:initial`` or ``seat:final``, so
several councils can share one database without colliding.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from arbiter_study.models import ModelAnswer, ProviderPosition, Question


T = TypeVar("T", bound=BaseModel)


class FollowupStore:
    def __init__(self, path: str | Path, freeze_hash: str, questions: list[Question]):
        self.connection = sqlite3.connect(path)
        with self.connection:
            self.connection.executescript("""
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS questions (id TEXT PRIMARY KEY, payload_hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS answers (
                    question_id TEXT NOT NULL, stage TEXT NOT NULL, member_id TEXT NOT NULL,
                    payload TEXT NOT NULL, PRIMARY KEY(question_id, stage, member_id)
                );
                CREATE TABLE IF NOT EXISTS positions (
                    question_id TEXT NOT NULL, stage TEXT NOT NULL, provider TEXT NOT NULL,
                    payload TEXT NOT NULL, PRIMARY KEY(question_id, stage, provider)
                );
                CREATE TABLE IF NOT EXISTS decisions (
                    question_id TEXT NOT NULL, stage TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(question_id, stage)
                );
                CREATE TABLE IF NOT EXISTS calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, question_id TEXT NOT NULL,
                    stage TEXT NOT NULL, member_id TEXT, success INTEGER NOT NULL,
                    cost REAL, error TEXT
                );
            """)
            existing = self.connection.execute(
                "SELECT value FROM meta WHERE key='freeze_hash'").fetchone()
            if existing and existing[0] != freeze_hash:
                raise RuntimeError("Database belongs to a different freeze")
            self.connection.execute("INSERT OR IGNORE INTO meta VALUES ('freeze_hash',?)", (freeze_hash,))
            for question in questions:
                digest = hashlib.sha256(question.model_dump_json().encode()).hexdigest()
                self.connection.execute("INSERT OR IGNORE INTO questions VALUES (?,?)",
                                        (question.id, digest))
        count = self.connection.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        if count != len(questions):
            raise RuntimeError("Database question plan differs from the freeze")

    # Reads
    def answers(self, question_id: str, stage: str) -> list[ModelAnswer]:
        found = [ModelAnswer.model_validate_json(row[0]) for row in self.connection.execute(
            "SELECT payload FROM answers WHERE question_id=? AND stage=?", (question_id, stage))]
        return sorted(found, key=lambda answer: (answer.provider, answer.sample_index))

    def positions(self, question_id: str, stage: str) -> list[ProviderPosition]:
        return [ProviderPosition.model_validate_json(row[0]) for row in self.connection.execute(
            "SELECT payload FROM positions WHERE question_id=? AND stage=? ORDER BY provider",
            (question_id, stage))]

    def decision(self, question_id: str, stage: str, model: type[T]) -> T | None:
        row = self.connection.execute(
            "SELECT payload FROM decisions WHERE question_id=? AND stage=?",
            (question_id, stage)).fetchone()
        return model.model_validate_json(row[0]) if row else None

    def attempts(self, question_id: str, stage: str, member_id: str | None = None) -> int:
        if member_id is None:
            return self.connection.execute(
                "SELECT COUNT(*) FROM calls WHERE question_id=? AND stage=? AND member_id IS NULL",
                (question_id, stage)).fetchone()[0]
        return self.connection.execute(
            "SELECT COUNT(*) FROM calls WHERE question_id=? AND stage=? AND member_id=?",
            (question_id, stage, member_id)).fetchone()[0]

    # Writes
    def save_answer(self, question_id: str, stage: str, answer: ModelAnswer) -> None:
        with self.connection:
            self.connection.execute("INSERT INTO answers VALUES (?,?,?,?)",
                                    (question_id, stage, answer.member_id, answer.model_dump_json()))
            self.connection.execute(
                "INSERT INTO calls(question_id,stage,member_id,success,cost) VALUES (?,?,?,1,?)",
                (question_id, stage, answer.member_id, answer.estimated_cost_usd))

    def save_positions(self, question_id: str, stage: str, positions: list[ProviderPosition]) -> None:
        with self.connection:
            for position in positions:
                self.connection.execute("INSERT OR REPLACE INTO positions VALUES (?,?,?,?)",
                                        (question_id, stage, position.provider, position.model_dump_json()))

    def save_decision(self, question_id: str, stage: str, result: BaseModel, *, billable: bool = True) -> None:
        cost = getattr(result, "estimated_cost_usd", None) if billable else 0
        with self.connection:
            self.connection.execute("INSERT INTO decisions VALUES (?,?,?)",
                                    (question_id, stage, result.model_dump_json()))
            if billable:
                self.connection.execute(
                    "INSERT INTO calls(question_id,stage,member_id,success,cost) VALUES (?,?,NULL,1,?)",
                    (question_id, stage, cost))

    def save_failure(self, question_id: str, stage: str, member_id: str | None, error: Exception) -> None:
        raw = getattr(error, "raw", None)
        message = f"{type(error).__name__}: {error}"
        if raw is not None:
            message += " | raw=" + json.dumps(raw)[:2000]
        with self.connection:
            self.connection.execute(
                "INSERT INTO calls(question_id,stage,member_id,success,error) VALUES (?,?,?,0,?)",
                (question_id, stage, member_id, message))

    # Totals
    def cost(self) -> float:
        return float(self.connection.execute("SELECT COALESCE(SUM(cost),0) FROM calls").fetchone()[0])

    def failures(self) -> int:
        return self.connection.execute("SELECT COUNT(*) FROM calls WHERE success=0").fetchone()[0]

    def complete_count(self, stage: str) -> int:
        return self.connection.execute(
            "SELECT COUNT(*) FROM decisions WHERE stage=?", (stage,)).fetchone()[0]

    def close(self) -> None:
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()
