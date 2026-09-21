import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from exams.models import Exam, ExamCategory, Question

CONTENT = b"""QUESTION: Sky color?
OPTION: Green
OPTION: Blue
OPTION: Red
OPTION: Yellow
ANSWER: 2
"""


@pytest.mark.django_db
def test_staff_previews_and_confirms_import(client):
    staff = User.objects.create_user("staff", password="Pass12345!", is_staff=True)
    client.force_login(staff)
    response = client.post(
        reverse("question_imports:upload"),
        {
            "file": SimpleUploadedFile("q.txt", CONTENT),
            "category": Question.Category.VOCABULARY,
        },
    )
    assert response.status_code == 200
    assert b"Sky color" in response.content
    response = client.post(reverse("question_imports:confirm"))
    assert response.status_code == 302
    question = Question.objects.get(text="Sky color?")
    exam = Exam.objects.get()
    assert exam.title == "Q"
    assert exam.is_published
    assert exam.created_by == staff
    assert question.category == Question.Category.VOCABULARY
    assert ExamCategory.objects.filter(
        exam=exam, category=Question.Category.VOCABULARY, question_count=1
    ).exists()
    assert b"Q" in client.get(reverse("exams:list")).content


@pytest.mark.django_db
def test_non_staff_cannot_import(client):
    user = User.objects.create_user("student", password="Pass12345!")
    client.force_login(user)
    assert client.get(reverse("question_imports:upload")).status_code == 403
