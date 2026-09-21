from django.contrib import admin

from .forms import OptionInlineFormSet
from .models import Answer, Attempt, AttemptQuestion, Exam, ExamCategory, Option, Question


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


class AttemptQuestionInline(admin.TabularInline):
    model = AttemptQuestion
    fields = ("position", "question_text", "selected_answer", "answer_result")
    readonly_fields = fields
    extra = 0
    can_delete = False
    verbose_name = "Answer"
    verbose_name_plural = "Answers"

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("answer__selected_option")

    @admin.display(description="Selected answer")
    def selected_answer(self, obj):
        try:
            selected_option = obj.answer.selected_option
        except Answer.DoesNotExist:
            return "Unanswered"
        return selected_option.option_text if selected_option else "Unanswered"

    @admin.display(boolean=True, description="Correct")
    def answer_result(self, obj):
        try:
            return obj.answer.is_correct
        except Answer.DoesNotExist:
            return None


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("exam", "student", "status", "score", "started_at")
    list_filter = ("status", "exam")
    search_fields = ("student__username", "exam__title")
    inlines = (AttemptQuestionInline,)
