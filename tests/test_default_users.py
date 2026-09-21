import pytest
from django.contrib.auth import authenticate
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_default_admin_user_is_created_by_migrations():
    admin = authenticate(username="admin", password="admin123")

    assert admin is not None
    assert admin.is_staff
    assert admin.is_superuser
    assert admin.is_active


@pytest.mark.django_db
def test_default_regular_user_is_created_by_migrations():
    user = authenticate(username="user", password="user123")

    assert user is not None
    assert user.is_active
    assert not user.is_staff
    assert not user.is_superuser
    assert User.objects.filter(username="user").exists()
