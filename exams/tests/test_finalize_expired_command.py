from datetime import timedelta
from io import StringIO

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.utils import timezone

from exams.models import Attempt, Exam


@pytest.mark.django_db
def test_finalize_expired_attempts_is_bounded_and_repeatable():
    student = User.objects.create_user("expired")
    exam = Exam.objects.create(title="Expired exam", duration_minutes=1, is_published=True)
    overdue = Attempt.objects.create(
        exam=exam,
        student=student,
        expires_at=timezone.now() - timedelta(minutes=1),
    )
    output = StringIO()
    call_command("finalize_expired_attempts", limit=1, stdout=output)
    overdue.refresh_from_db()
    assert overdue.status == Attempt.Status.EXPIRED
    assert "Finalized 1" in output.getvalue()
    output = StringIO()
    call_command("finalize_expired_attempts", stdout=output)
    assert "Finalized 0" in output.getvalue()
