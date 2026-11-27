"""Persistent learner memory, stored in SQLite.

This is the part of Neura that remembers. Everything the tutor learns
about a learner lives here, so a new session starts where the last one
ended instead of starting from zero.

Tables:
    learners   one row per person, with a display name
    mastery    one row per learner per topic, a score from 0.0 to 1.0
    mistakes   one row per wrong answer, with the question and the topic
    sessions   one row per tutoring session, with a short summary
    attempts   one row per answer given, right or wrong

Only the standard library is used. The database file is created on
first use, in the location passed to LearnerStore.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS learners (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS mastery (
    learner_id INTEGER NOT NULL,
    topic TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 0.0,
    updated_at REAL NOT NULL,
    PRIMARY KEY (learner_id, topic),
    FOREIGN KEY (learner_id) REFERENCES learners(id)
);
CREATE TABLE IF NOT EXISTS mistakes (
    id INTEGER PRIMARY KEY,
    learner_id INTEGER NOT NULL,
    topic TEXT NOT NULL,
    question_id TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY (learner_id) REFERENCES learners(id)
);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    learner_id INTEGER NOT NULL,
    topic TEXT NOT NULL,
    summary TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY (learner_id) REFERENCES learners(id)
);
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY,
    learner_id INTEGER NOT NULL,
    topic TEXT NOT NULL,
    question_id TEXT NOT NULL,
    correct INTEGER NOT NULL,
    hints_used INTEGER NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY (learner_id) REFERENCES learners(id)
);
"""


class LearnerStore:
    """A small wrapper around a SQLite file for one learner's memory."""

    def __init__(self, path: str | Path = "neura.db") -> None:
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def get_or_create_learner(self, name: str) -> int:
        """Return the id for a learner, creating them if needed."""
        row = self.conn.execute(
            "SELECT id FROM learners WHERE name = ?", (name,)
        ).fetchone()
        if row is not None:
            return int(row["id"])
        cur = self.conn.execute(
            "INSERT INTO learners (name, created_at) VALUES (?, ?)",
            (name, time.time()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def get_mastery(self, learner_id: int) -> dict[str, float]:
        rows = self.conn.execute(
            "SELECT topic, score FROM mastery WHERE learner_id = ?",
            (learner_id,),
        ).fetchall()
        return {row["topic"]: float(row["score"]) for row in rows}

    def update_mastery(self, learner_id: int, topic: str, delta: float) -> float:
        """Move a mastery score by delta, clamped to the range 0 to 1."""
        mastery = self.get_mastery(learner_id)
        new_score = min(1.0, max(0.0, mastery.get(topic, 0.0) + delta))
        self.conn.execute(
            """
            INSERT INTO mastery (learner_id, topic, score, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(learner_id, topic)
            DO UPDATE SET score = excluded.score, updated_at = excluded.updated_at
            """,
            (learner_id, topic, new_score, time.time()),
        )
        self.conn.commit()
        return new_score

    def set_mastery(self, learner_id: int, topic: str, score: float) -> float:
        return self.update_mastery(
            learner_id, topic, score - self.get_mastery(learner_id).get(topic, 0.0)
        )

    def record_attempt(
        self, learner_id: int, topic: str, question_id: str,
        correct: bool, hints_used: int,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO attempts
                (learner_id, topic, question_id, correct, hints_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (learner_id, topic, question_id, int(correct), hints_used, time.time()),
        )
        self.conn.commit()

    def record_mistake(
        self, learner_id: int, topic: str, question_id: str, answer: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO mistakes (learner_id, topic, question_id, answer, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (learner_id, topic, question_id, answer, time.time()),
        )
        self.conn.commit()

    def record_session(self, learner_id: int, topic: str, summary: dict) -> None:
        self.conn.execute(
            """
            INSERT INTO sessions (learner_id, topic, summary, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (learner_id, topic, json.dumps(summary), time.time()),
        )
        self.conn.commit()

    def recent_mistakes(self, learner_id: int, topic: str | None = None,
                        limit: int = 10) -> list[dict]:
        if topic is None:
            rows = self.conn.execute(
                """
                SELECT topic, question_id, answer, created_at FROM mistakes
                WHERE learner_id = ? ORDER BY created_at DESC LIMIT ?
                """,
                (learner_id, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT topic, question_id, answer, created_at FROM mistakes
                WHERE learner_id = ? AND topic = ? ORDER BY created_at DESC LIMIT ?
                """,
                (learner_id, topic, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def session_count(self, learner_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM sessions WHERE learner_id = ?",
            (learner_id,),
        ).fetchone()
        return int(row["n"])
