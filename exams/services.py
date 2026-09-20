from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Answer, Attempt, AttemptOption, AttemptQuestion


@transaction.atomic
def start_attempt(exam, student):
    now = timezone.now()
    if not exam.is_available(now):
        raise ValidationError("This exam is not available.")
    existing = Attempt.objects.filter(
        exam=exam, student=student, status=Attempt.Status.IN_PROGRESS
    ).first()
    if existing:
        if existing.expires_at <= now:
            finalize_attempt(existing, expired=True)
        else:
            return existing
    completed = (
        Attempt.objects.filter(exam=exam, student=student)
        .exclude(status=Attempt.Status.IN_PROGRESS)
        .count()
    )
    if completed >= exam.max_attempts:
        raise ValidationError("Maximum attempts reached.")
    items = list(
        exam.exam_questions.select_related("question").prefetch_related("question__options")
    )
    if not items:
        raise ValidationError("This exam has no questions.")
    for item in items:
        item.question.validate_options()
    attempt = Attempt.objects.create(
        exam=exam,
        student=student,
        started_at=now,
        expires_at=now + timedelta(minutes=exam.duration_minutes),
    )
    for item in items:
        aq = AttemptQuestion.objects.create(
            attempt=attempt,
            source_question=item.question,
            position=item.position,
            points=item.points,
            question_text=item.question.text,
            explanation=item.question.explanation,
        )
        for option in item.question.options.all():
            AttemptOption.objects.create(
                attempt_question=aq,
                source_option=option,
                position=option.position,
                option_text=option.text,
                is_correct_snapshot=option.is_correct,
            )
    return attempt


def save_answer(attempt, attempt_question, selected_option):
    now = timezone.now()
    if attempt.status != Attempt.Status.IN_PROGRESS or now >= attempt.expires_at:
        finalize_attempt(attempt, expired=True)
        raise ValidationError("The exam time has expired.")
    if (
        attempt_question.attempt_id != attempt.id
        or selected_option.attempt_question_id != attempt_question.id
    ):
        raise PermissionDenied("Invalid question or option.")
    answer, _ = Answer.objects.update_or_create(
        attempt_question=attempt_question, defaults={"selected_option": selected_option}
    )
    return answer


@transaction.atomic
def finalize_attempt(attempt, expired=False):
    attempt = Attempt.objects.select_for_update().get(pk=attempt.pk)
    if attempt.status != Attempt.Status.IN_PROGRESS:
        return attempt
    now = timezone.now()
    expired = expired or now >= attempt.expires_at
    questions = list(
        attempt.attempt_questions.prefetch_related("options", "answer__selected_option")
    )
    score = Decimal("0")
    correct = incorrect = unanswered = 0
    maximum = sum((q.points for q in questions), Decimal("0"))
    for question in questions:
        try:
            answer = question.answer
        except Answer.DoesNotExist:
            answer = None
        if not answer or not answer.selected_option:
            unanswered += 1
            continue
        answer.is_correct = answer.selected_option.is_correct_snapshot
        answer.save(update_fields=["is_correct"])
        if answer.is_correct:
            correct += 1
            score += question.points
        else:
            incorrect += 1
    percentage = (
        (score * 100 / maximum).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if maximum
        else Decimal("0")
    )
    attempt.status = Attempt.Status.EXPIRED if expired else Attempt.Status.SUBMITTED
    attempt.submitted_at = now
    attempt.score = score
    attempt.maximum_score = maximum
    attempt.percentage = percentage
    attempt.correct_count = correct
    attempt.incorrect_count = incorrect
    attempt.unanswered_count = unanswered
    attempt.save()
    return attempt
