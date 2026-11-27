"""Tests for the SQLite learner memory."""

import tempfile
import unittest
from pathlib import Path

from neura.store import LearnerStore


class TestLearnerStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = LearnerStore(Path(self.tmp.name) / "test.db")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_learner_is_created_once(self):
        first = self.store.get_or_create_learner("Alex")
        second = self.store.get_or_create_learner("Alex")
        self.assertEqual(first, second)

    def test_mastery_is_clamped_to_zero_and_one(self):
        learner_id = self.store.get_or_create_learner("Alex")
        self.assertEqual(self.store.update_mastery(learner_id, "b_algebra_functions", 2.0), 1.0)
        self.assertEqual(self.store.update_mastery(learner_id, "b_algebra_functions", -5.0), 0.0)

    def test_mastery_persists_across_reopen(self):
        learner_id = self.store.get_or_create_learner("Alex")
        self.store.update_mastery(learner_id, "e_trigonometry", 0.4)
        path = self.store.path
        self.store.close()
        reopened = LearnerStore(path)
        try:
            mastery = reopened.get_mastery(learner_id)
            self.assertAlmostEqual(mastery["e_trigonometry"], 0.4)
        finally:
            reopened.close()

    def test_mistakes_are_recorded_and_read_back(self):
        learner_id = self.store.get_or_create_learner("Alex")
        self.store.record_mistake(learner_id, "b_algebra_functions", "alg1", "4")
        mistakes = self.store.recent_mistakes(learner_id, "b_algebra_functions")
        self.assertEqual(len(mistakes), 1)
        self.assertEqual(mistakes[0]["answer"], "4")
        self.assertEqual(mistakes[0]["question_id"], "alg1")

    def test_session_count_grows(self):
        learner_id = self.store.get_or_create_learner("Alex")
        self.assertEqual(self.store.session_count(learner_id), 0)
        self.store.record_session(learner_id, "b_algebra_functions", {"correct": 1})
        self.assertEqual(self.store.session_count(learner_id), 1)


if __name__ == "__main__":
    unittest.main()
