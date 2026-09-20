from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Attempt, AttemptOption, AttemptQuestion, Exam
from .selectors import available_exams
from .services import finalize_attempt, save_answer, start_attempt


def exam_list(request):
    return render(request, "exams/exam_list.html", {"exams": available_exams()})


@login_required
def exam_detail(request, pk):
    exam = get_object_or_404(available_exams(), pk=pk)
    return render(request, "exams/exam_detail.html", {"exam": exam})


@login_required
@require_POST
def start(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    try:
        attempt = start_attempt(exam, request.user)
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
        return redirect("exams:detail", pk=pk)
    return redirect("exams:take", pk=attempt.pk)


def owned_attempt(user, pk):
    return get_object_or_404(Attempt, pk=pk, student=user)


@login_required
def take(request, pk):
    attempt = owned_attempt(request.user, pk)
    if attempt.status != Attempt.Status.IN_PROGRESS:
        return redirect("exams:result", pk=pk)
    if timezone.now() >= attempt.expires_at:
        finalize_attempt(attempt, expired=True)
        return redirect("exams:result", pk=pk)
    questions = attempt.attempt_questions.prefetch_related("options", "answer__selected_option")
    return render(request, "exams/take_exam.html", {"attempt": attempt, "questions": questions})


@login_required
@require_POST
def answer(request, pk):
    attempt = owned_attempt(request.user, pk)
    question = get_object_or_404(
        AttemptQuestion, pk=request.POST.get("question_id"), attempt=attempt
    )
    option = get_object_or_404(
        AttemptOption, pk=request.POST.get("option_id"), attempt_question=question
    )
    try:
        save_answer(attempt, question, option)
    except ValidationError as error:
        return JsonResponse({"ok": False, "error": error.messages[0]}, status=409)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    return redirect("exams:take", pk=pk)


@login_required
@require_POST
def submit(request, pk):
    attempt = owned_attempt(request.user, pk)
    finalize_attempt(attempt)
    return redirect("exams:result", pk=pk)


@login_required
def result(request, pk):
    attempt = owned_attempt(request.user, pk)
    if attempt.status == Attempt.Status.IN_PROGRESS:
        if timezone.now() >= attempt.expires_at:
            attempt = finalize_attempt(attempt, expired=True)
        else:
            return redirect("exams:take", pk=pk)
    return render(request, "exams/result.html", {"attempt": attempt})


@login_required
def evaluation(request, pk):
    attempt = owned_attempt(request.user, pk)
    if attempt.status == Attempt.Status.IN_PROGRESS or not attempt.exam.show_evaluation:
        raise Http404
    questions = attempt.attempt_questions.prefetch_related("options", "answer__selected_option")
    return render(request, "exams/evaluation.html", {"attempt": attempt, "questions": questions})
