from django.contrib import admin

from .models import ImportBatch


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "uploaded_by", "status", "question_count", "created_at")
    list_filter = ("status",)
