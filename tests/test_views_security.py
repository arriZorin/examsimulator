from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from exams.models import Attempt, Exam, ExamCategory, Option, Question
from exams.services import finalize_attempt, start_attempt


def exam_with_question(**kwargs):
    question = Question.objects.create(
        text="Capital of France?", category=Question.Category.VOCABULARY
    )
    for index, text in enumerate(["Paris", "Rome", "Lima", "Oslo"], 1):
        Option.objects.create(question=question, text=text, position=index, is_correct=index == 1)
    exam = Exam.objects.create(
        title=kwargs.pop("title", "Geography"), duration_minutes=10, **kwargs
    )
    ExamCategory.objects.create(
        exam=exam, category=Question.Category.VOCABULARY, question_count=1
    )
    return exam


@pytest.mark.django_db
def test_catalog_only_lists_current_published_exams(client):
    current = exam_with_question(title="Current", is_published=True)
    exam_with_question(title="Draft", is_published=False)
    exam_with_question(
        title="Future",
        is_published=True,
        available_from=timezone.now() + timedelta(days=1),
    )
    response = client.get(reverse("exams:list"))
    assert current.title.encode() in response.content
    assert b"Draft" not in response.content
    assert b"Future" not in response.content


@pytest.mark.django_db
def test_start_is_login_post_and_csrf_protected():
    exam = exam_with_question(is_published=True)
    student = User.objects.create_user("student")
    assert Client().post(reverse("exams:start", args=[exam.pk])).status_code == 302
    client = Client(enforce_csrf_checks=True)
    client.force_login(student)
    assert client.get(reverse("exams:start", args=[exam.pk])).status_code == 405
    assert client.post(reverse("exams:start", args=[exam.pk])).status_code == 403


@pytest.mark.django_db
def test_attempt_pages_are_owner_scoped_and_hide_evaluation_when_disabled(client):
    owner = User.objects.create_user("owner")
    other = User.objects.create_user("other")
    exam = exam_with_question(is_published=True, show_evaluation=False)
    attempt = start_attempt(exam, owner)
    finalize_attempt(attempt)
    client.force_login(other)
    for name in ("take", "result", "evaluation"):
        assert client.get(reverse(f"exams:{name}", args=[attempt.pk])).status_code == 404
    client.force_login(owner)
    assert client.get(reverse("exams:evaluation", args=[attempt.pk])).status_code == 404


@pytest.mark.django_db
def test_registration_creates_profile_and_logs_student_in(client):
    response = client.post(
        reverse("accounts:register"),
        {
            "username": "newstudent",
            "email": "new@example.com",
            "full_name": "New Student",
            "password1": "A-long-password-2026!",
            "password2": "A-long-password-2026!",
        },
    )
    assert response.status_code == 302
    user = User.objects.get(username="newstudent")
    assert user.student_profile.full_name == "New Student"
    assert client.get(reverse("accounts:dashboard")).status_code == 200


@pytest.mark.django_db
def test_dashboard_does_not_leak_other_students_attempts(client):
    student = User.objects.create_user("one")
    other = User.objects.create_user("two")
    first = start_attempt(exam_with_question(title="Mine", is_published=True), student)
    start_attempt(exam_with_question(title="Secret", is_published=True), other)
    client.force_login(student)
    response = client.get(reverse("accounts:dashboard"))
    assert first.exam.title.encode() in response.content
    assert b"Secret" not in response.content


@pytest.mark.django_db
def test_complete_student_journey_through_http_views(client):
    student = User.objects.create_user("journey")
    exam = exam_with_question(is_published=True)
    client.force_login(student)

    response = client.post(reverse("exams:start", args=[exam.pk]))
    attempt = Attempt.objects.get(student=student, exam=exam)
    assert response.url == reverse("exams:take", args=[attempt.pk])

    take_response = client.get(response.url)
    assert b"Capital of France?" in take_response.content
    assert b"Paris" in take_response.content
    assert b"is_correct" not in take_response.content

    question = attempt.attempt_questions.get()
    correct = question.options.get(position=1)
    answer_response = client.post(
        reverse("exams:answer", args=[attempt.pk]),
        {"question_id": question.pk, "option_id": correct.pk},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert answer_response.json() == {"ok": True}

    response = client.post(reverse("exams:submit", args=[attempt.pk]))
    assert response.url == reverse("exams:result", args=[attempt.pk])
    assert b"100.00%" in client.get(response.url).content
    evaluation = client.get(reverse("exams:evaluation", args=[attempt.pk]))
    assert evaluation.status_code == 200
    assert b"correct answer" in evaluation.content
