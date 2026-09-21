from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from exams.models import Exam, Question

from .extractors import ExtractionError, extract_text
from .forms import ImportUploadForm
from .parser import parse_questions
from .services import commit_import

SESSION_KEY = "question_import_preview"


def require_staff(request):
    if not request.user.is_staff:
        raise PermissionDenied


@login_required
def upload(request):
    require_staff(request)
    form = ImportUploadForm(request.POST or None, request.FILES or None)
    preview = None
    duplicate_warnings = []
    if request.method == "POST" and form.is_valid():
        file = form.cleaned_data["file"]
        try:
            result = parse_questions(extract_text(file))
        except ExtractionError as error:
            form.add_error("file", str(error))
        else:
            preview = result
            if not result.errors:

                def normalize(value):
                    return " ".join(value.split()).casefold()

                existing = {
                    normalize(text) for text in Question.objects.values_list("text", flat=True)
                }
                duplicate_warnings = [
                    question.text
                    for question in result.questions
                    if normalize(question.text) in existing
                ]
                payload = {
                    "filename": file.name,
                    "category": form.cleaned_data["category"],
                    "exam_id": form.cleaned_data["exam"].pk if form.cleaned_data["exam"] else None,
                    "items": [q.to_dict() for q in result.questions],
                }
                request.session[SESSION_KEY] = payload
            else:
                request.session.pop(SESSION_KEY, None)
    return render(
        request,
        "question_imports/upload.html",
        {"form": form, "preview": preview, "duplicate_warnings": duplicate_warnings},
    )


@login_required
@require_POST
def confirm(request):
    require_staff(request)
    payload = request.session.get(SESSION_KEY)
    if not payload:
        messages.error(request, "No valid import preview is available.")
        return redirect("question_imports:upload")
    exam = (
        Exam.objects.filter(pk=payload.get("exam_id")).first() if payload.get("exam_id") else None
    )
    batch = commit_import(
        items=payload["items"],
        user=request.user,
        filename=payload["filename"],
        category=payload["category"],
        exam=exam,
    )
    request.session.pop(SESSION_KEY, None)
    messages.success(
        request,
        f'Imported {batch.question_count} question(s) into exam "{batch.exam.title}".',
    )
    return redirect("question_imports:upload")
