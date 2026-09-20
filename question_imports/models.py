from django.conf import settings
from django.db import models

from exams.models import Exam


class ImportBatch(models.Model):
    class Status(models.TextChoices):
        PREVIEWED = "PREVIEWED", "Previewed"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    exam = models.ForeignKey(Exam, null=True, blank=True, on_delete=models.SET_NULL)
    original_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PREVIEWED)
    question_count = models.PositiveIntegerField(default=0)
    error_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
