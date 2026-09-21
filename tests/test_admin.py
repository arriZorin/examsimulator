import pytest
from django.contrib import admin
from django.contrib.auth.models import User
from django.urls import reverse

from exams.models import Answer, Exam, ExamCategory, Option, Question
from exams.services import save_answer, start_attempt


@pytest.mark.django_db
def test_answers_are_shown_inside_attempt_admin_instead_of_separate_admin(admin_client):
    student = User.objects.create_user("admin-review-student")
    question = Question.objects.create(
        text="Choose the greeting.", category=Question.Category.EXPRESSION
    )
    for position, text in enumerate(["Hello", "Table", "Blue", "Seven"], 1):
        Option.objects.create(
            question=question,
            text=text,
            position=position,
            is_correct=position == 1,
        )
    exam = Exam.objects.create(title="Expressions", is_published=True)
    ExamCategory.objects.create(
        exam=exam, category=Question.Category.EXPRESSION, question_count=1
    )
    attempt = start_attempt(exam, student)
    attempt_question = attempt.attempt_questions.get()
    save_answer(attempt, attempt_question, attempt_question.options.get(position=1))

    response = admin_client.get(reverse("admin:exams_attempt_change", args=[attempt.pk]))

    assert response.status_code == 200
    assert b"Answers" in response.content
    assert b"Choose the greeting." in response.content
    assert b"Hello" in response.content
    assert Answer not in admin.site._registry
