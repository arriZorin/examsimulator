from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from exams.models import Exam, ExamQuestion, Option, Question
from exams.services import finalize_attempt, save_answer, start_attempt


def build_exam(*, title="Math", duration=15, **kwargs):
    question = Question.objects.create(text="2 + 2?", explanation="Basic addition")
    for position, text in enumerate(["3", "5", "4", "6"], 1):
        Option.objects.create(
            question=question,
            text=text,
            position=position,
            is_correct=position == 3,
        )
    question.validate_options()
    exam = Exam.objects.create(
        title=title,
        duration_minutes=duration,
        is_published=True,
        **kwargs,
    )
    ExamQuestion.objects.create(exam=exam, question=question, position=1, points=2)
    return exam


@pytest.mark.django_db
def test_student_can_complete_exam_and_see_history(client):
    student = User.objects.create_user("learner", password="Pass12345!")
    exam = build_exam()
    client.force_login(student)
    attempt = start_attempt(exam, student)
    assert attempt.expires_at == attempt.started_at + timedelta(minutes=15)
    attempt_question = attempt.attempt_questions.get()
    save_answer(attempt, attempt_question, attempt_question.options.get(position=3))
    finalize_attempt(attempt)
    attempt.refresh_from_db()
    assert attempt.score == Decimal("2.00")
    assert attempt.percentage == Decimal("100.00")
    assert client.get(reverse("exams:result", args=[attempt.pk])).status_code == 200
    assert b"100.00%" in client.get(reverse("accounts:dashboard")).content


@pytest.mark.django_db
def test_question_requires_four_options_and_one_correct():
    question = Question.objects.create(text="Invalid")
    for index in range(3):
        Option.objects.create(
            question=question, text=str(index), position=index + 1, is_correct=index == 0
        )
    with pytest.raises(ValidationError):
        question.validate_options()


@pytest.mark.django_db
def test_attempt_reuses_active_attempt_and_enforces_limit():
    student = User.objects.create_user("repeat")
    exam = build_exam(max_attempts=1)
    first = start_attempt(exam, student)
    assert start_attempt(exam, student).pk == first.pk
    finalize_attempt(first)
    with pytest.raises(ValidationError, match="Maximum"):
        start_attempt(exam, student)


@pytest.mark.django_db
def test_unavailable_and_empty_exams_cannot_start():
    student = User.objects.create_user("blocked")
    future = build_exam(available_from=timezone.now() + timedelta(days=1))
    with pytest.raises(ValidationError, match="available"):
        start_attempt(future, student)
    empty = Exam.objects.create(title="Empty", duration_minutes=5, is_published=True)
    with pytest.raises(ValidationError, match="questions"):
        start_attempt(empty, student)


@pytest.mark.django_db
def test_expired_attempt_is_finalized_before_answer_is_saved():
    student = User.objects.create_user("late")
    attempt = start_attempt(build_exam(), student)
    attempt.expires_at = timezone.now() - timedelta(seconds=1)
    attempt.save(update_fields=["expires_at"])
    question = attempt.attempt_questions.get()
    with pytest.raises(ValidationError, match="expired"):
        save_answer(attempt, question, question.options.get(position=3))
    attempt.refresh_from_db()
    assert attempt.status == attempt.Status.EXPIRED
