from pathlib import Path

from django.db import transaction
from django.utils import timezone

from exams.models import Exam, ExamCategory, Option, Question

from .models import ImportBatch


@transaction.atomic
def commit_import(*, items, user, filename, category, exam=None):
    if exam is None:
        title = Path(filename).stem.replace("_", " ").replace("-", " ").strip().title()
        exam = Exam.objects.create(
            title=(title or "Imported Questions")[:200],
            is_published=True,
            created_by=user,
        )
    batch = ImportBatch.objects.create(
        uploaded_by=user, exam=exam, original_filename=filename, question_count=len(items)
    )
    for item in items:
        question = Question.objects.create(
            text=item["text"],
            explanation=item.get("explanation", ""),
            category=category,
            created_by=user,
        )
        for position, text in enumerate(item["options"], 1):
            Option.objects.create(
                question=question,
                text=text,
                position=position,
                is_correct=position == item["correct_index"],
            )
        question.validate_options()
    setting, created = ExamCategory.objects.get_or_create(
        exam=exam, category=category, defaults={"question_count": len(items)}
    )
    if not created:
        setting.question_count += len(items)
        setting.save(update_fields=["question_count"])
    batch.status = ImportBatch.Status.COMPLETED
    batch.completed_at = timezone.now()
    batch.save(update_fields=["status", "completed_at"])
    return batch
