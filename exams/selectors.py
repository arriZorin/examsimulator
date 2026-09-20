from django.db.models import Q
from django.utils import timezone

from .models import Exam


def available_exams():
    now = timezone.now()
    return (
        Exam.objects.filter(is_published=True)
        .filter(Q(available_from__isnull=True) | Q(available_from__lte=now))
        .filter(Q(available_until__isnull=True) | Q(available_until__gte=now))
        .order_by("title")
    )
