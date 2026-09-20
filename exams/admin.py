from django.contrib import admin

from .forms import OptionInlineFormSet
from .models import Answer, Attempt, Exam, ExamQuestion, Option, Question


class OptionInline(admin.TabularInline):
    model = Option
    formset = OptionInlineFormSet
    extra = 4
    min_num = 4


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("text",)
    inlines = (OptionInline,)


class ExamQuestionInline(admin.TabularInline):
    model = ExamQuestion
    extra = 1


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("title", "duration_minutes", "is_published")
    list_filter = ("is_published",)
    inlines = (ExamQuestionInline,)


admin.site.register(Attempt)
admin.site.register(Answer)
