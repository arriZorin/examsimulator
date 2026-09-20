from pathlib import Path

from django import forms

from exams.models import Exam


class ImportUploadForm(forms.Form):
    file = forms.FileField(help_text="TXT, MD, DOCX, or PDF; maximum 5 MB")
    exam = forms.ModelChoiceField(
        queryset=Exam.objects.all(),
        required=False,
        help_text="Optionally add imported questions to this exam.",
    )

    def clean_file(self):
        upload = self.cleaned_data["file"]
        if upload.size > 5 * 1024 * 1024:
            raise forms.ValidationError("File must be 5 MB or smaller.")
        if Path(upload.name).suffix.lower() not in {".txt", ".md", ".docx", ".pdf"}:
            raise forms.ValidationError("Unsupported file type.")
        return upload
