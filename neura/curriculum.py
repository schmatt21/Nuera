"""Curriculum: topics, their prerequisites, and the question bank.

The curriculum is data, not code. It lives in data/curriculum.json and
data/questions.json so a teacher can change what is taught without
changing the tutor. This module only loads that data and answers
questions about it, such as "what does this topic depend on?"
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Topic:
    id: str
    title: str
    description: str
    prerequisites: tuple[str, ...]
    paper: int = 1
    papers: tuple[int, ...] = (1,)


@dataclass(frozen=True)
class Question:
    id: str
    topic: str
    prompt: str
    expected: tuple[str, ...]
    hints: tuple[str, ...]
    worked_fragment: str = ""
    common_mistakes: tuple[str, ...] = ()


def _data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def load_curriculum(path: str | Path | None = None) -> list[Topic]:
    file = Path(path) if path else _data_dir() / "curriculum.json"
    raw = json.loads(file.read_text(encoding="utf-8"))
    return [
        Topic(
            id=t["id"],
            title=t["title"],
            description=t["description"],
            prerequisites=tuple(t.get("prerequisites", [])),
            paper=int(t.get("paper", 1)),
            papers=tuple(t.get("papers", [t.get("paper", 1)])),
        )
        for t in raw["topics"]
    ]


def load_questions(path: str | Path | None = None) -> list[Question]:
    file = Path(path) if path else _data_dir() / "questions.json"
    raw = json.loads(file.read_text(encoding="utf-8"))
    return [
        Question(
            id=q["id"],
            topic=q["topic"],
            prompt=q["prompt"],
            expected=tuple(q["expected"]),
            hints=tuple(q["hints"]),
            worked_fragment=q.get("worked_fragment", ""),
            common_mistakes=tuple(q.get("common_mistakes", [])),
        )
        for q in raw["questions"]
    ]


def questions_for_topic(questions: list[Question], topic: str) -> list[Question]:
    return [q for q in questions if q.topic == topic]


def prerequisites_of(topics: list[Topic], topic_id: str) -> list[str]:
    for topic in topics:
        if topic.id == topic_id:
            return list(topic.prerequisites)
    return []


def all_prerequisites(topics: list[Topic], topic_id: str) -> list[str]:
    """All prerequisites of a topic, transitively, in dependency order."""
    seen: list[str] = []
    stack = prerequisites_of(topics, topic_id)
    while stack:
        current = stack.pop(0)
        if current in seen:
            continue
        seen.append(current)
        stack.extend(prerequisites_of(topics, current))
    return seen
