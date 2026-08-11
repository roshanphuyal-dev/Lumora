"""Pure unit tests for `app.services.quiz_attempt_service._grade_objective` /
`_normalize` -- the deterministic (no-AI-call) half of grading (ADR 0011).

These are plain functions over an in-memory `Question` instance (never persisted), so no
DB session is needed -- exhaustive per-question-type coverage including case/whitespace
edge cases and malformed-answer-shape defensive branches.
"""

from app.models.quiz import Question, QuestionType, QuizDifficulty
from app.services.quiz_attempt_service import _grade_objective, _normalize


def _question(question_type: QuestionType, correct_answer: object) -> Question:
    return Question(
        quiz_id=None,
        position=0,
        question_type=question_type,
        prompt="Q?",
        type_data={},
        correct_answer=correct_answer,
        reference_answer=None,
        explanation="Because.",
        citation=None,
        difficulty=QuizDifficulty.MEDIUM,
    )


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------


def test_normalize_trims_whitespace_and_lowercases() -> None:
    assert _normalize("  Paris  ") == "paris"
    assert _normalize("PARIS") == "paris"
    assert _normalize("paris") == "paris"


def test_normalize_stringifies_non_str_input() -> None:
    assert _normalize(42) == "42"
    assert _normalize(True) == "true"


# ---------------------------------------------------------------------------
# mcq
# ---------------------------------------------------------------------------


def test_grade_objective_mcq_exact_match() -> None:
    question = _question(QuestionType.MCQ, "Mitochondria")
    assert _grade_objective(question, "Mitochondria") is True


def test_grade_objective_mcq_case_insensitive() -> None:
    question = _question(QuestionType.MCQ, "Mitochondria")
    assert _grade_objective(question, "mitochondria") is True
    assert _grade_objective(question, "MITOCHONDRIA") is True


def test_grade_objective_mcq_whitespace_insensitive() -> None:
    question = _question(QuestionType.MCQ, "Mitochondria")
    assert _grade_objective(question, "  Mitochondria  ") is True


def test_grade_objective_mcq_wrong_answer() -> None:
    question = _question(QuestionType.MCQ, "Mitochondria")
    assert _grade_objective(question, "Nucleus") is False


def test_grade_objective_mcq_missing_answer_is_false() -> None:
    question = _question(QuestionType.MCQ, "Mitochondria")
    assert _grade_objective(question, None) is False


def test_grade_objective_mcq_null_correct_answer_is_false() -> None:
    question = _question(QuestionType.MCQ, None)
    assert _grade_objective(question, "Mitochondria") is False


def test_grade_objective_mcq_non_str_student_answer_is_false() -> None:
    question = _question(QuestionType.MCQ, "Mitochondria")
    assert _grade_objective(question, ["Mitochondria"]) is False


# ---------------------------------------------------------------------------
# true_false
# ---------------------------------------------------------------------------


def test_grade_objective_true_false_match() -> None:
    question = _question(QuestionType.TRUE_FALSE, "true")
    assert _grade_objective(question, "true") is True
    assert _grade_objective(question, "True") is True
    assert _grade_objective(question, " TRUE ") is True


def test_grade_objective_true_false_mismatch() -> None:
    question = _question(QuestionType.TRUE_FALSE, "true")
    assert _grade_objective(question, "false") is False


# ---------------------------------------------------------------------------
# assertion_reason
# ---------------------------------------------------------------------------


def test_grade_objective_assertion_reason_match() -> None:
    question = _question(QuestionType.ASSERTION_REASON, "both_true_reason_correct")
    assert _grade_objective(question, "both_true_reason_correct") is True
    assert _grade_objective(question, "Both_True_Reason_Correct") is True


def test_grade_objective_assertion_reason_mismatch() -> None:
    question = _question(QuestionType.ASSERTION_REASON, "both_true_reason_correct")
    assert _grade_objective(question, "both_true_reason_incorrect") is False


# ---------------------------------------------------------------------------
# fill_blank
# ---------------------------------------------------------------------------


def test_grade_objective_fill_blank_list_all_correct() -> None:
    question = _question(QuestionType.FILL_BLANK, ["nucleus", "ribosome"])
    assert _grade_objective(question, ["nucleus", "ribosome"]) is True


def test_grade_objective_fill_blank_list_case_and_whitespace_insensitive() -> None:
    question = _question(QuestionType.FILL_BLANK, ["nucleus", "ribosome"])
    assert _grade_objective(question, ["  Nucleus", "RIBOSOME  "]) is True


def test_grade_objective_fill_blank_list_one_wrong() -> None:
    question = _question(QuestionType.FILL_BLANK, ["nucleus", "ribosome"])
    assert _grade_objective(question, ["nucleus", "mitochondria"]) is False


def test_grade_objective_fill_blank_list_length_mismatch_is_false() -> None:
    question = _question(QuestionType.FILL_BLANK, ["nucleus", "ribosome"])
    assert _grade_objective(question, ["nucleus"]) is False


def test_grade_objective_fill_blank_single_string_shape() -> None:
    question = _question(QuestionType.FILL_BLANK, "nucleus")
    assert _grade_objective(question, "Nucleus") is True
    assert _grade_objective(question, "ribosome") is False


def test_grade_objective_fill_blank_shape_mismatch_is_false() -> None:
    # correct_answer is a list but the student answer is a bare string.
    question = _question(QuestionType.FILL_BLANK, ["nucleus"])
    assert _grade_objective(question, "nucleus") is False


# ---------------------------------------------------------------------------
# matching
# ---------------------------------------------------------------------------


def _pairs(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    return [{"left": left, "right": right} for left, right in pairs]


def test_grade_objective_matching_all_correct_regardless_of_order() -> None:
    question = _question(
        QuestionType.MATCHING, _pairs(("Nucleus", "Stores DNA"), ("Ribosome", "Makes protein"))
    )
    student_answer = _pairs(("Ribosome", "Makes protein"), ("Nucleus", "Stores DNA"))
    assert _grade_objective(question, student_answer) is True


def test_grade_objective_matching_case_and_whitespace_insensitive() -> None:
    question = _question(QuestionType.MATCHING, _pairs(("Nucleus", "Stores DNA")))
    student_answer = _pairs(("  nucleus", "STORES DNA  "))
    assert _grade_objective(question, student_answer) is True


def test_grade_objective_matching_wrong_pairing() -> None:
    question = _question(
        QuestionType.MATCHING, _pairs(("Nucleus", "Stores DNA"), ("Ribosome", "Makes protein"))
    )
    student_answer = _pairs(("Nucleus", "Makes protein"), ("Ribosome", "Stores DNA"))
    assert _grade_objective(question, student_answer) is False


def test_grade_objective_matching_partial_set_is_false() -> None:
    question = _question(
        QuestionType.MATCHING, _pairs(("Nucleus", "Stores DNA"), ("Ribosome", "Makes protein"))
    )
    student_answer = _pairs(("Nucleus", "Stores DNA"))
    assert _grade_objective(question, student_answer) is False


def test_grade_objective_matching_malformed_pair_missing_key_is_false() -> None:
    question = _question(QuestionType.MATCHING, _pairs(("Nucleus", "Stores DNA")))
    assert _grade_objective(question, [{"left": "Nucleus"}]) is False


def test_grade_objective_matching_non_list_student_answer_is_false() -> None:
    question = _question(QuestionType.MATCHING, _pairs(("Nucleus", "Stores DNA")))
    assert _grade_objective(question, "Nucleus=Stores DNA") is False
