from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from exams.models import ExamQuestion, Option, Question

from .models import ImportBatch


@transaction.atomic
def commit_import(*, items, user, filename, exam=None):
    batch = ImportBatch.objects.create(
        uploaded_by=user, exam=exam, original_filename=filename, question_count=len(items)
    )
    next_position = (
        (exam.exam_questions.order_by("-position").values_list("position", flat=True).first() or 0)
        + 1
        if exam
        else 1
    )
    for offset, item in enumerate(items):
        question = Question.objects.create(
            text=item["text"], explanation=item.get("explanation", ""), created_by=user
        )
        for position, text in enumerate(item["options"], 1):
            Option.objects.create(
                question=question,
                text=text,
                position=position,
                is_correct=position == item["correct_index"],
            )
        question.validate_options()
        if exam:
            ExamQuestion.objects.create(
                exam=exam,
                question=question,
                position=next_position + offset,
                points=Decimal("1.00"),
            )
    batch.status = ImportBatch.Status.COMPLETED
    batch.completed_at = timezone.now()
    batch.save(update_fields=["status", "completed_at"])
    return batch
