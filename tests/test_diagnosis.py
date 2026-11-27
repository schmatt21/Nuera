"""Tests for diagnosis: the weakest prerequisite must come first.

AQA A Level Mathematics 7357. The key case is a learner who looks
weak on differentiation, when the real gap is algebra: quadratics
in topic B. Neura must send them back to B first.
"""

import unittest

from neura.curriculum import Topic, load_curriculum, load_questions
from neura.diagnosis import find_next_topic, needs_work, score_answers

# A small AQA subset, with the same prerequisite shape as the full
# curriculum: differentiation depends on algebra, coordinate geometry,
# trigonometry and exponentials/logs.
TOPICS = [
    Topic("a_proof", "A: Proof", "", ("b_algebra_functions",)),
    Topic("b_algebra_functions", "B: Algebra and functions", "", ()),
    Topic("c_coordinate_geometry", "C: Coordinate geometry", "", ("b_algebra_functions",)),
    Topic("e_trigonometry", "E: Trigonometry", "", ("b_algebra_functions", "c_coordinate_geometry")),
    Topic("f_exponentials_logarithms", "F: Exponentials and logarithms", "", ("b_algebra_functions",)),
    Topic("g_differentiation", "G: Differentiation", "", ("b_algebra_functions", "c_coordinate_geometry", "e_trigonometry", "f_exponentials_logarithms")),
    Topic("h_integration", "H: Integration", "", ("g_differentiation", "b_algebra_functions")),
]


class TestScoreAnswers(unittest.TestCase):
    def test_all_correct(self):
        self.assertEqual(score_answers([True, True]), 1.0)

    def test_half_correct(self):
        self.assertEqual(score_answers([True, False]), 0.5)

    def test_empty(self):
        self.assertEqual(score_answers([]), 0.0)


class TestFindNextTopic(unittest.TestCase):
    def test_weakest_prerequisite_wins(self):
        # Integration looks weakest, but its prerequisite
        # differentiation is weaker still, so that comes first.
        mastery = {
            "a_proof": 0.9,
            "b_algebra_functions": 0.8,
            "c_coordinate_geometry": 0.8,
            "e_trigonometry": 0.8,
            "f_exponentials_logarithms": 0.8,
            "g_differentiation": 0.1,
            "h_integration": 0.0,
        }
        self.assertEqual(find_next_topic(TOPICS, mastery), "g_differentiation")

    def test_weak_quadratics_blocks_differentiation(self):
        # Differentiation looks weakest, but it depends on algebra.
        # Algebra (quadratics, surds, indices) is weak, so algebra
        # comes first, even though differentiation scores lower.
        mastery = {
            "a_proof": 0.9,
            "b_algebra_functions": 0.2,
            "c_coordinate_geometry": 0.8,
            "e_trigonometry": 0.8,
            "f_exponentials_logarithms": 0.8,
            "g_differentiation": 0.0,
            "h_integration": 0.9,
        }
        self.assertEqual(find_next_topic(TOPICS, mastery), "b_algebra_functions")

    def test_no_prerequisite_gap(self):
        mastery = {
            "a_proof": 0.9,
            "b_algebra_functions": 0.9,
            "c_coordinate_geometry": 0.9,
            "e_trigonometry": 0.9,
            "f_exponentials_logarithms": 0.2,
            "g_differentiation": 0.8,
            "h_integration": 0.8,
        }
        self.assertEqual(find_next_topic(TOPICS, mastery), "f_exponentials_logarithms")

    def test_everything_unknown_starts_at_the_start(self):
        # Proof depends on algebra, so a learner who knows nothing
        # starts with algebra, not with proof.
        self.assertEqual(find_next_topic(TOPICS, {}), "b_algebra_functions")


class TestNeedsWork(unittest.TestCase):
    def test_only_below_threshold(self):
        mastery = {
            "a_proof": 0.9,
            "b_algebra_functions": 0.3,
            "c_coordinate_geometry": 0.9,
            "e_trigonometry": 0.9,
            "f_exponentials_logarithms": 0.4,
            "g_differentiation": 0.9,
            "h_integration": 0.9,
        }
        self.assertEqual(
            needs_work(TOPICS, mastery),
            ["b_algebra_functions", "f_exponentials_logarithms"],
        )


class TestAqaCurriculum(unittest.TestCase):
    def test_full_curriculum_has_nineteen_topics_a_to_s(self):
        topics = load_curriculum()
        self.assertEqual(len(topics), 19)
        ids = [t.id for t in topics]
        self.assertEqual(ids[0], "a_proof")
        self.assertEqual(ids[-1], "s_moments")
        self.assertIn("g_differentiation", ids)
        self.assertIn("j_vectors", ids)
        self.assertIn("o_hypothesis_testing", ids)

    def test_paper_allocation(self):
        topics = {t.id: t for t in load_curriculum()}
        self.assertEqual(topics["a_proof"].paper, 1)
        self.assertEqual(topics["g_differentiation"].paper, 1)
        self.assertEqual(topics["j_vectors"].paper, 2)
        self.assertEqual(topics["k_statistical_sampling"].paper, 3)
        self.assertEqual(topics["q_kinematics"].paper, 2)
        self.assertEqual(topics["o_hypothesis_testing"].paper, 3)

    def test_no_topic_depends_on_itself(self):
        from neura.curriculum import all_prerequisites

        topics = load_curriculum()
        for topic in topics:
            self.assertNotIn(topic.id, all_prerequisites(topics, topic.id))

    def test_questions_cover_first_six_pure_topics(self):
        questions = load_questions()
        by_topic = {}
        for q in questions:
            by_topic.setdefault(q.topic, []).append(q)
        for topic_id in [
            "a_proof",
            "b_algebra_functions",
            "c_coordinate_geometry",
            "d_sequences_series",
            "e_trigonometry",
            "f_exponentials_logarithms",
        ]:
            self.assertIn(topic_id, by_topic)
            self.assertGreaterEqual(len(by_topic[topic_id]), 2)
            for q in by_topic[topic_id]:
                self.assertEqual(len(q.hints), 3)
                self.assertTrue(q.worked_fragment)
                self.assertTrue(q.common_mistakes)


if __name__ == "__main__":
    unittest.main()
