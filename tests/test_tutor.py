"""Tests for the Socratic tutor: hints, mastery, and no answer given.

AQA example: solve x^2 - 5x + 6 = 0. The larger root is 3.
A first answer of 2 is wrong — that is the smaller root — and the
tutor should hint, not give the answer away.
"""

import tempfile
import unittest
from pathlib import Path

from neura.curriculum import Question
from neura.store import LearnerStore
from neura.tutor import RuleBasedModel, SocraticTutor

QUESTION = Question(
    id="alg1",
    topic="b_algebra_functions",
    prompt="Solve x^2 - 5x + 6 = 0. What is the larger root?",
    expected=("3",),
    hints=(
        "Factorise – which two numbers multiply to 6 and add to -5?",
        "(x-2)(x-3)=0, so x=2 or x=3.",
        "The roots are 2 and 3. Which is larger?",
    ),
    worked_fragment="x^2-5x+6 = (x-2)(x-3) = 0, so x=2 or x=3. The larger root is 3.",
    common_mistakes=("Giving only one root",),
)


class TestRuleBasedModel(unittest.TestCase):
    def test_correct_answer_matches_keyword(self):
        self.assertTrue(RuleBasedModel().check(QUESTION, "3"))

    def test_wrong_answer_does_not_match(self):
        self.assertFalse(RuleBasedModel().check(QUESTION, "2"))

    def test_empty_answer_is_wrong(self):
        self.assertFalse(RuleBasedModel().check(QUESTION, "   "))

    def test_hint_is_staged(self):
        model = RuleBasedModel()
        self.assertIn("Factorise", model.hint(QUESTION, 0))
        self.assertIn("(x-2)(x-3)", model.hint(QUESTION, 1))


class TestSocraticTutor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = LearnerStore(Path(self.tmp.name) / "test.db")
        self.learner_id = self.store.get_or_create_learner("Alex")
        self.tutor = SocraticTutor(self.store, self.learner_id)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_first_try_correct_raises_mastery_most(self):
        result = self.tutor.ask(QUESTION, ["3"])
        self.assertTrue(result.correct)
        self.assertEqual(result.hints_used, 0)
        self.assertAlmostEqual(result.mastery_after, 0.15)

    def test_correct_after_hint_raises_mastery_less(self):
        result = self.tutor.ask(QUESTION, ["2", "3"])
        self.assertTrue(result.correct)
        self.assertEqual(result.hints_used, 1)
        self.assertAlmostEqual(result.mastery_after, 0.08)

    def test_three_wrong_answers_lowers_mastery(self):
        result = self.tutor.ask(QUESTION, ["1", "2", "4"])
        self.assertFalse(result.correct)
        self.assertEqual(result.hints_used, 3)
        self.assertAlmostEqual(result.mastery_after, 0.0)

    def test_mistakes_are_remembered(self):
        self.tutor.ask(QUESTION, ["2", "3"])
        mistakes = self.store.recent_mistakes(self.learner_id, "b_algebra_functions")
        self.assertEqual(len(mistakes), 1)
        self.assertEqual(mistakes[0]["answer"], "2")


if __name__ == "__main__":
    unittest.main()
