# Neura

A Socratic tutor for AQA A Level Mathematics 7357 that remembers
where you are weak, and starts there.

Most tutors ask questions in the order the course was written. Neura
does the opposite: it diagnoses first, finds the weakest prerequisite,
and attacks that before it touches the topic you thought you were
struggling with. It does not give the answer. It asks, hints in stages,
and remembers what happened for next time.

All practice questions are original practice questions in the style
of AQA. None are presented as past paper questions.

## The AQA course it tutors

AQA A Level Mathematics, specification 7357. The subject content is
nineteen lettered topics, A to S:

- **Pure, A to J:** Proof, Algebra and functions, Coordinate geometry,
  Sequences and series, Trigonometry, Exponentials and logarithms,
  Differentiation, Integration, Numerical methods, Vectors.
- **Statistics, K to O:** Statistical sampling, Data presentation and
  interpretation, Probability, Statistical distributions, Statistical
  hypothesis testing.
- **Mechanics, P to S:** Quantities and units in mechanics, Kinematics,
  Forces and Newton's laws, Moments.

Assessment is three written papers, each 2 hours and 100 marks, each
one third of the A-level:

- **Paper 1:** Pure only, topics A to I.
- **Paper 2:** Paper 1 content plus Vectors (J) and Mechanics (P to S).
- **Paper 3:** Paper 1 content plus Statistics (K to O).

Topics A to I are therefore examined on all three papers as Paper 1
content. In `data/curriculum.json` each topic records its primary
paper in `paper`, and every paper it can appear on in `papers`.

## How to run

No API key is needed. Python 3.10 or later, standard library only.

```bash
python -m neura.cli demo
python -m neura.cli diagnose --name Alex
python -m neura.cli tutor --name Alex --topic b_algebra_functions
python -m neura.cli profile --name Alex
```

Tests:

```bash
python -m unittest discover -s tests -v
```

## What it does

1. **Diagnose.** One short question per topic that has questions yet:
   currently Proof, Algebra and functions, Coordinate geometry,
   Sequences and series, Trigonometry, and Exponentials and logarithms.
2. **Pick the real gap.** If differentiation is weak because algebra
   is weak — for example, quadratics — Neura starts with algebra.
   A topic is only studied once its prerequisites are above the pass
   threshold. This is tested directly: weak quadratics blocks
   differentiation in `tests/test_diagnosis.py`.
3. **Teach Socratically.** A question is asked. A wrong answer gets a
   hint, not the answer. Hint 1 reframes the question, hint 2 breaks
   it into a smaller step, hint 3 gives a worked fragment with one
   piece missing. After three wrong answers the tutor stops, records
   the mistake, and asks the learner to revisit the concept.
4. **Remember.** Mastery scores, mistakes, attempts, and session
   summaries are stored in SQLite (`neura.db`), so the next session
   starts from the learner's real state.

## Architecture

```
                  +------------------+
                  |  CLI (neura/cli)  |
                  |  diagnose/tutor/  |
                  |  profile/demo     |
                  +--------+---------+
                           |
        +------------------+------------------+
        |                  |                  |
+-------v--------+  +------v-------+  +-------v--------+
| tutor          |  | diagnosis    |  | curriculum     |
| SocraticTutor  |  | find weakest |  | topics, prereqs|
| hints, mastery |  | prerequisite |  | questions      |
+-------+--------+  +--------------+  +-------+--------+
        |                                  |
        +------------------+------------------+
                           |
                  +--------v---------+
                  | store            |
                  | SQLite: learner, |
                  | mastery, mistakes|
                  | sessions, attempts|
                  +------------------+
```

Data files in `data/` are separate from code, so the curriculum and
questions can change without changing the tutor:

- `data/curriculum.json` — 19 AQA topics A to S, with prerequisites,
  primary paper, and a short description
- `data/questions.json` — 18 practice questions, 3 per topic for
  topics A to F, each with expected keywords, 3 staged hints, a
  worked fragment, and common mistakes

Module map:

| Module | Job |
| --- | --- |
| `neura/store.py` | Persistent memory in SQLite |
| `neura/curriculum.py` | Loads topics and questions from JSON |
| `neura/diagnosis.py` | Scores a diagnostic and picks the next topic |
| `neura/tutor.py` | Socratic loop, hints, and the model interface |
| `neura/cli.py` | Command line: diagnose, tutor, profile, demo |

## Design decisions

- **Prerequisites first.** A weak score on a later topic is often a
  symptom. The diagnostic walks back to the weakest prerequisite
  before choosing what to teach. That is the whole point of the
  project, and it is tested in `tests/test_diagnosis.py`.
- **Rule-based model by default.** The tutor is driven by a
  `LanguageModel` interface in `neura/tutor.py`. The default
  implementation, `RuleBasedModel`, checks answers against expected
  keywords and picks hints from the question bank. It needs no API
  key, no network, and no cost, which keeps the demo runnable
  anywhere. A hosted model can be added later by implementing the
  same two methods, `check` and `hint`, without changing the tutor.
- **SQLite, not a file of notes.** Mastery and mistakes need to survive
  between sessions and be queryable, for example "what did this
  learner get wrong in algebra last week?" A single SQLite file does
  that with no server and no extra dependency.
- **Small mastery steps.** A first-try correct answer adds 0.15, a
  correct answer after hints adds 0.08, and three wrong answers
  subtract 0.05. Scores are clamped to 0 to 1. The numbers are
  deliberately modest: one good answer should not claim a topic is
  mastered.
- **Curriculum as data.** Topics and questions live in JSON. Adding
  a topic means adding an entry and its questions, not editing the
  tutor logic.
- **Questions are single-answer where possible.** Keyword checking
  cannot reliably check two-part answers, so questions are written
  to ask for one value — the larger root, the y-coordinate, the
  coefficient — and the worked fragment shows the full working.

## Limitations

- Answer checking is keyword-based, not meaning-based. A correct
  answer phrased in an unexpected way can be marked wrong, and a
  lucky keyword can be marked right. A language model would fix
  this; the interface for one is already in place.
- The question bank covers only topics A to F so far: 18 questions,
  3 per topic. Topics G to S have curriculum entries and
  prerequisites, but no questions yet. That is deliberate: the bank
  grows one topic at a time, in the daily plan, with every answer
  checked.
- Mastery is a single number per topic. It does not track
  sub-skills inside a topic, such as quadratics versus surds inside
  Algebra and functions.
- There is no web interface. The CLI is the whole product for now.

## What to build next

See `DAILY_PLAN.md` for the day-by-day plan to 11 January 2027.
In order: questions for Differentiation, Integration, Numerical
methods and Vectors, then Statistics K to O, then Mechanics P to S,
with a hosted language model behind the `LanguageModel` interface
once the bank is large enough to evaluate it properly.
