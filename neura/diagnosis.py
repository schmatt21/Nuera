"""Diagnosis: find where a learner is weak, starting with prerequisites.

The idea is simple. A learner can look weak on data analysis when the
real gap is earlier, in data structures or SQL. Testing the later topic
first wastes time and gives a misleading score, so Neura tests every
topic briefly, then picks the weakest prerequisite first.

Rules:
    1. A score below 0.5 on a topic means "needs work".
    2. If a topic needs work and one of its prerequisites also needs
       work, the prerequisite comes first.
    3. If nothing needs work, the lowest-scoring topic is next for
       revision, so the learner keeps the weakest area fresh.
"""

from __future__ import annotations

from neura.curriculum import Topic, all_prerequisites

PASS_THRESHOLD = 0.5


def score_answers(correct: list[bool]) -> float:
    """Turn a list of right/wrong answers into a score from 0 to 1."""
    if not correct:
        return 0.0
    return sum(1 for item in correct if item) / len(correct)


def find_next_topic(topics: list[Topic], mastery: dict[str, float]) -> str:
    """Return the id of the topic to study next.

    The weakest topic wins, unless a prerequisite of that topic is
    weaker still, in which case that prerequisite wins.
    """
    scores = {t.id: mastery.get(t.id, 0.0) for t in topics}
    weakest = min(scores, key=lambda topic_id: scores[topic_id])

    # Walk back through the prerequisites of the weakest topic.
    # If any prerequisite also needs work, that prerequisite is the
    # real starting point, even if the weakest topic scores lower.
    chain = all_prerequisites(topics, weakest)
    if chain:
        weakest_prereq = min(chain, key=lambda topic_id: scores.get(topic_id, 0.0))
        if scores.get(weakest_prereq, 0.0) < PASS_THRESHOLD:
            return weakest_prereq

    return weakest


def needs_work(topics: list[Topic], mastery: dict[str, float]) -> list[str]:
    """Topics below the pass threshold, weakest first."""
    return sorted(
        [t.id for t in topics if mastery.get(t.id, 0.0) < PASS_THRESHOLD],
        key=lambda topic_id: mastery.get(topic_id, 0.0),
    )


def diagnose_summary(topics: list[Topic], mastery: dict[str, float]) -> dict:
    """A plain summary the CLI can print and the store can save."""
    return {
        "scores": {t.id: round(mastery.get(t.id, 0.0), 2) for t in topics},
        "needs_work": needs_work(topics, mastery),
        "next_topic": find_next_topic(topics, mastery),
    }
