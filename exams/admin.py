from django.contrib import admin

from .forms import OptionInlineFormSet
from .models import Answer, Attempt, Exam, ExamCategory, Option, Question


class OptionInline(admin.TabularInline):
    model = Option
    formset = OptionInlineFormSet
    extra = 4
    min_num = 4


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "category", "is_active", "created_at")
    list_filter = ("category", "is_active")
    search_fields = ("text",)
    inlines = (OptionInline,)


class ExamCategoryInline(admin.TabularInline):
    model = ExamCategory
    extra = 1


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("title", "duration_minutes", "is_published")
    list_filter = ("is_published",)
    inlines = (ExamCategoryInline,)


admin.site.register(Attempt)
admin.site.register(Answer)
