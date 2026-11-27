"""Command line interface for Neura.

Usage:
    python -m neura.cli profile --name Alex
    python -m neura.cli diagnose --name Alex
    python -m neura.cli tutor --name Alex --topic b_algebra_functions
    python -m neura.cli demo

Neura tutors AQA A Level Mathematics 7357. The tutor is interactive:
it asks a question, you answer, and it only gives a hint when you are
wrong. It never prints the answer first. Type "quit" to stop a session
at any point.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from neura.curriculum import load_curriculum, load_questions, questions_for_topic
from neura.diagnosis import diagnose_summary
from neura.store import LearnerStore
from neura.tutor import MAX_HINTS, RuleBasedModel, SocraticTutor

DEFAULT_DB = Path("neura.db")


def _load(name: str, db: Path) -> tuple[LearnerStore, int]:
    store = LearnerStore(db)
    learner_id = store.get_or_create_learner(name)
    return store, learner_id


def cmd_profile(args: argparse.Namespace) -> int:
    store, learner_id = _load(args.name, args.db)
    try:
        mastery = store.get_mastery(learner_id)
        topics = load_curriculum()
        print(f"Learner: {args.name}")
        print(f"Sessions so far: {store.session_count(learner_id)}")
        print("Mastery:")
        for topic in topics:
            score = mastery.get(topic.id, 0.0)
            bar = "#" * int(score * 20)
            print(f"  {topic.title:<25} {score:.2f} {bar}")
        mistakes = store.recent_mistakes(learner_id, limit=5)
        if mistakes:
            print("Recent mistakes:")
            for mistake in mistakes:
                print(f"  {mistake['topic']}: {mistake['question_id']}")
        return 0
    finally:
        store.close()


def cmd_diagnose(args: argparse.Namespace) -> int:
    store, learner_id = _load(args.name, args.db)
    try:
        topics = load_curriculum()
        questions = load_questions()
        model = RuleBasedModel()
        print("Short diagnostic. Answer each question; type quit to stop.\n")
        for topic in topics:
            topic_questions = questions_for_topic(questions, topic.id)
            if not topic_questions:
                continue
            question = topic_questions[0]
            print(f"[{topic.title}]")
            print(question.prompt)
            answer = input("> ").strip()
            if answer.lower() == "quit":
                break
            correct = model.check(question, answer)
            store.record_attempt(learner_id, topic.id, question.id, correct, 0)
            if not correct:
                store.record_mistake(learner_id, topic.id, question.id, answer)
            store.set_mastery(learner_id, topic.id, 1.0 if correct else 0.2)
            print("Correct." if correct else "Not yet. We will come back to this.")
            print()
        summary = diagnose_summary(topics, store.get_mastery(learner_id))
        print("Diagnostic summary:")
        for topic_id, score in summary["scores"].items():
            print(f"  {topic_id}: {score:.2f}")
        print(f"Next topic to study: {summary['next_topic']}")
        store.record_session(learner_id, summary["next_topic"], summary)
        return 0
    finally:
        store.close()


def cmd_tutor(args: argparse.Namespace) -> int:
    store, learner_id = _load(args.name, args.db)
    try:
        topics = load_curriculum()
        questions = load_questions()
        topic_questions = questions_for_topic(questions, args.topic)
        if not topic_questions:
            print(f"No questions for topic '{args.topic}'.")
            print("Available topics:", ", ".join(t.id for t in topics))
            return 1
        tutor = SocraticTutor(store, learner_id)
        correct_count = 0
        for question in topic_questions:
            print(f"\n{question.prompt}\n")
            hints_used = 0
            correct = False
            while hints_used <= MAX_HINTS:
                answer = input("> ").strip()
                if answer.lower() == "quit":
                    print("Session saved. Come back any time.")
                    return 0
                if tutor.model.check(question, answer):
                    correct = True
                    break
                hints_used += 1
                store.record_mistake(learner_id, question.topic, question.id, answer)
                if hints_used >= MAX_HINTS:
                    print("That one needs a proper look at the concept first.")
                    print("Try the topic again after reading the notes, and")
                    print("we will revisit this exact question.")
                    break
                print(f"Hint: {tutor.next_hint(question, hints_used - 1)}")
            store.record_attempt(
                learner_id, question.topic, question.id, correct, hints_used
            )
            delta = 0.15 if correct and hints_used == 0 else 0.08 if correct else -0.05
            mastery = store.update_mastery(learner_id, question.topic, delta)
            if correct:
                correct_count += 1
                print(f"Correct. Mastery for this topic is now {mastery:.2f}.")
            else:
                print(f"Mastery for this topic is now {mastery:.2f}.")
        store.record_session(
            learner_id,
            args.topic,
            {"questions": len(topic_questions), "correct": correct_count},
        )
        print(f"\nDone. {correct_count} of {len(topic_questions)} correct.")
        return 0
    finally:
        store.close()


def cmd_demo(args: argparse.Namespace) -> int:
    """A scripted, non-interactive session, so the loop can be seen quickly."""
    store, learner_id = _load("demo", args.db)
    try:
        questions = load_questions()
        tutor = SocraticTutor(store, learner_id)
        question = questions_for_topic(questions, "b_algebra_functions")[0]
        print("Demo: Socratic tutor, AQA A Level Maths — Algebra and functions")
        print(f"Question: {question.prompt}\n")
        print("Learner answers '2' (wrong — that is the smaller root).")
        result = tutor.ask(question, ["2", "3"])
        print(f"Hint given, then correct. Hints used: {result.hints_used}")
        print(f"Correct: {result.correct}, mastery now {result.mastery_after:.2f}")
        print("\nThe tutor never printed the answer. It only asked,")
        print("hinted, and recorded what happened.")
        return 0
    finally:
        store.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="neura", description="Socratic tutor")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB,
                        help="SQLite file for learner memory")
    sub = parser.add_subparsers(dest="command", required=True)

    # --db and --name are accepted after the subcommand too, so both
    # "neura --db x.db tutor" and "neura tutor --db x.db" work.
    # SUPPRESS keeps the top-level value when they are not repeated.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", type=Path, default=argparse.SUPPRESS)
    common.add_argument("--name", default=argparse.SUPPRESS)

    for name in ("profile", "diagnose", "demo"):
        cmd = sub.add_parser(name, parents=[common])
        cmd.set_defaults(func=globals()[f"cmd_{name}"])

    tutor_cmd = sub.add_parser("tutor", parents=[common])
    tutor_cmd.add_argument("--topic", default="b_algebra_functions")
    tutor_cmd.set_defaults(func=cmd_tutor)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
