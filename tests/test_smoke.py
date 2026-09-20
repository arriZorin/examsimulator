import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


@pytest.mark.django_db
def test_home_page_and_registration_flow(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Exam Simulation" in response.content

    response = client.post(
        reverse("accounts:register"),
        {
            "username": "student1",
            "email": "student@example.com",
            "full_name": "Test Student",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        },
    )
    assert response.status_code == 302
    user = get_user_model().objects.get(username="student1")
    assert user.student_profile.full_name == "Test Student"
