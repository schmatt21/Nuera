"""The Socratic tutor.

A Socratic tutor does not give the answer. It asks a question, listens,
and only narrows the question down in stages when the learner is stuck.

How it works in this version:
    * The tutor is driven by a LanguageModel. The default model is
      rule-based: it picks the next question and the next hint from the
      question bank, and checks answers against expected keywords.
      That keeps the demo runnable with no API key.
    * A real language model can be plugged in later by implementing
      the same LanguageModel interface. The tutor itself does not need
      to change; only the model does. See LanguageModel below.
    * Hints come in three stages and never contain the full answer.
      Stage 1 reframes the question, stage 2 breaks it into a smaller
      step, stage 3 gives a worked fragment with one piece missing.
    * Mastery moves a little on every attempt, and more on a first-try
      correct answer than on a correct answer after hints.

Checking an answer is deliberately simple: the learner's answer is
lowercased and checked for any of the expected keywords. That is a
limitation, and it is stated as one in the README. A language model
would check meaning rather than keywords.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from neura.curriculum import Question
from neura.store import LearnerStore

MAX_HINTS = 3


class LanguageModel:
    """Interface for any model that can pick questions and check answers.

    The tutor only ever calls these two methods, so swapping the
    rule-based model for a hosted model means writing a new class
    with these methods, not rewriting the tutor.
    """

    def check(self, question: Question, answer: str) -> bool:
        raise NotImplementedError

    def hint(self, question: Question, hints_used: int) -> str:
        raise NotImplementedError


class RuleBasedModel(LanguageModel):
    """A model that needs no API key. It uses the question bank."""

    def check(self, question: Question, answer: str) -> bool:
        text = answer.strip().lower()
        if not text:
            return False
        return any(expected.lower() in text for expected in question.expected)

    def hint(self, question: Question, hints_used: int) -> str:
        index = min(hints_used, len(question.hints) - 1)
        return question.hints[index]


@dataclass
class TutorResult:
    question_id: str
    topic: str
    correct: bool
    hints_used: int
    mastery_after: float


@dataclass
class SocraticTutor:
    """Runs one question at a time, with staged hints and memory updates."""

    store: LearnerStore
    learner_id: int
    model: LanguageModel = field(default_factory=RuleBasedModel)

    def ask(self, question: Question, answers: list[str]) -> TutorResult:
        """Ask one question, taking answers in order.

        In the CLI, answers come from the learner typing. In tests and
        in the demo, they are passed in as a list, one per attempt.
        A hint is given after each wrong answer, up to MAX_HINTS.
        """
        hints_used = 0
        correct = False

        for answer in answers:
            if self.model.check(question, answer):
                correct = True
                break
            hints_used += 1
            self.store.record_mistake(
                self.learner_id, question.topic, question.id, answer
            )
            if hints_used >= MAX_HINTS:
                break

        self.store.record_attempt(
            self.learner_id, question.topic, question.id,
            correct, hints_used,
        )

        if correct and hints_used == 0:
            delta = 0.15
        elif correct:
            delta = 0.08
        else:
            delta = -0.05

        mastery_after = self.store.update_mastery(
            self.learner_id, question.topic, delta
        )
        return TutorResult(
            question_id=question.id,
            topic=question.topic,
            correct=correct,
            hints_used=hints_used,
            mastery_after=mastery_after,
        )

    def next_hint(self, question: Question, hints_used: int) -> str:
        return self.model.hint(question, hints_used)
