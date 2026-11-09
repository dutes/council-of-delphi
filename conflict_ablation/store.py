from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from conflict_ablation.models import ArbiterDecision


class ConflictStore:
    def __init__(self, path: str | Path, freeze_hash: str):
        self.db = sqlite3.connect(path)
        with self.db:
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS decisions (
                    question_id TEXT NOT NULL, stage_index INTEGER NOT NULL,
                    arbiter TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(question_id,stage_index,arbiter));
                CREATE TABLE IF NOT EXISTS calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, question_id TEXT NOT NULL,
                    stage_index INTEGER NOT NULL, arbiter TEXT NOT NULL,
                    success INTEGER NOT NULL, cost REAL, error TEXT);
            """)
            old = self.db.execute("SELECT value FROM meta WHERE key='freeze_hash'").fetchone()
            if old and old[0] != freeze_hash:
                raise RuntimeError("Database belongs to another freeze")
            self.db.execute("INSERT OR IGNORE INTO meta VALUES ('freeze_hash',?)", (freeze_hash,))

    def decision(self, question_id: str, stage: int, arbiter: str) -> ArbiterDecision | None:
        row = self.db.execute("SELECT payload FROM decisions WHERE question_id=? AND stage_index=? AND arbiter=?",
                              (question_id, stage, arbiter)).fetchone()
        return ArbiterDecision.model_validate_json(row[0]) if row else None

    def save(self, question_id: str, decision: ArbiterDecision) -> None:
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO decisions VALUES (?,?,?,?)", (
                question_id, decision.stage_index, decision.arbiter, decision.model_dump_json()))
            self.db.execute("INSERT INTO calls(question_id,stage_index,arbiter,success,cost) VALUES (?,?,?,?,?)", (
                question_id, decision.stage_index, decision.arbiter, 1, decision.estimated_cost_usd))

    def failure(self, question_id: str, stage: int, arbiter: str, error: Exception) -> None:
        message = f"{type(error).__name__}: {error}"
        raw = getattr(error, "raw", None)
        if raw is not None:
            message += " | raw=" + json.dumps(raw)[:1500]
        with self.db:
            self.db.execute("INSERT INTO calls(question_id,stage_index,arbiter,success,error) VALUES (?,?,?,0,?)",
                            (question_id, stage, arbiter, message))

    def attempts(self, question_id: str, stage: int, arbiter: str) -> int:
        return self.db.execute("SELECT COUNT(*) FROM calls WHERE question_id=? AND stage_index=? AND arbiter=?",
                               (question_id, stage, arbiter)).fetchone()[0]

    def complete_count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM (SELECT question_id FROM decisions GROUP BY question_id HAVING COUNT(*)=12)").fetchone()[0]

    def failures(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM calls WHERE success=0").fetchone()[0]

    def cost(self) -> float:
        return float(self.db.execute("SELECT COALESCE(SUM(cost),0) FROM calls").fetchone()[0])

    def __enter__(self): return self
    def __exit__(self, *_): self.db.close()

