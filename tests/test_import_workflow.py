import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from exams.models import Question

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
        reverse("question_imports:upload"), {"file": SimpleUploadedFile("q.txt", CONTENT)}
    )
    assert response.status_code == 200
    assert b"Sky color" in response.content
    response = client.post(reverse("question_imports:confirm"))
    assert response.status_code == 302
    assert Question.objects.filter(text="Sky color?").count() == 1


@pytest.mark.django_db
def test_non_staff_cannot_import(client):
    user = User.objects.create_user("student", password="Pass12345!")
    client.force_login(user)
    assert client.get(reverse("question_imports:upload")).status_code == 403
