from django.core.management.base import BaseCommand
from django.utils import timezone

from exams.models import Attempt
from exams.services import finalize_attempt


class Command(BaseCommand):
    help = "Finalize overdue in-progress attempts"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=500)

    def handle(self, *args, **options):
        attempts = Attempt.objects.filter(
            status=Attempt.Status.IN_PROGRESS, expires_at__lte=timezone.now()
        )[: options["limit"]]
        count = 0
        for attempt in attempts:
            finalize_attempt(attempt, expired=True)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Finalized {count} expired attempt(s)."))
