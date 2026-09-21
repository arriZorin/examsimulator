from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Question(models.Model):
    class Category(models.TextChoices):
        VOCABULARY = "vocabulary", "Vocabulary in Context"
        GRAMMAR = "grammar", "Grammar Challenge"
        EXPRESSION = "expression", "Functional Expression"
        READING = "reading", "Reading Comprehension"
        CLOZE = "cloze", "Cloze Test"
        SENTENCE = "sentence", "sentence arrangement and logic"
        SYNONYM_ANTONYM = "synonym_antonym", "Synonym Antonym Formation"
        HOTS = "hots", "HOTS & Olympiad Challenge"

    text = models.TextField()
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.VOCABULARY
    )
    explanation = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="questions_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.text[:80]

    def validate_options(self):
        options = list(self.options.all())
        if len(options) < 4:
            raise ValidationError("A question must have at least four options.")
        if sum(1 for option in options if option.is_correct) != 1:
            raise ValidationError("A question must have exactly one correct option.")


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["question", "position"], name="unique_option_position")
        ]

    def __str__(self):
        return self.text[:80]


class Exam(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=30)
    is_published = models.BooleanField(default=False)
    available_from = models.DateTimeField(null=True, blank=True)
    available_until = models.DateTimeField(null=True, blank=True)
    max_attempts = models.PositiveIntegerField(default=1)
    show_evaluation = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="exams_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.title

    @property
    def total_questions(self):
        return sum(item.question_count for item in self.exam_categories.all())

    def clean(self):
        errors = {}
        if self.duration_minutes < 1:
            errors["duration_minutes"] = "Duration must be positive."
        if self.max_attempts < 1:
            errors["max_attempts"] = "Maximum attempts must be positive."
        if (
            self.available_from
            and self.available_until
            and self.available_from >= self.available_until
        ):
            errors["available_until"] = "End must be after start."
        if errors:
            raise ValidationError(errors)

    def is_available(self, at=None):
        at = at or timezone.now()
        return (
            self.is_published
            and (not self.available_from or self.available_from <= at)
            and (not self.available_until or at <= self.available_until)
        )


class ExamCategory(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="exam_categories")
    category = models.CharField(max_length=20, choices=Question.Category.choices)
    question_count = models.PositiveIntegerField()

    class Meta:
        ordering = ["category"]
        constraints = [
            models.UniqueConstraint(fields=["exam", "category"], name="unique_exam_category"),
            models.CheckConstraint(
                condition=Q(question_count__gt=0), name="positive_exam_category_question_count"
            ),
        ]

    def __str__(self):
        return f"{self.get_category_display()}: {self.question_count}"


class Attempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        SUBMITTED = "SUBMITTED", "Submitted"
        EXPIRED = "EXPIRED", "Expired"

    exam = models.ForeignKey(Exam, on_delete=models.PROTECT, related_name="attempts")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="exam_attempts")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    started_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    maximum_score = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    correct_count = models.PositiveIntegerField(default=0)
    incorrect_count = models.PositiveIntegerField(default=0)
    unanswered_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["student", "-started_at"]),
            models.Index(fields=["exam", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "student"],
                condition=Q(status="IN_PROGRESS"),
                name="one_active_attempt_per_exam",
            )
        ]


class AttemptQuestion(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="attempt_questions")
    source_question = models.ForeignKey(Question, null=True, on_delete=models.SET_NULL)
    position = models.PositiveIntegerField()
    points = models.DecimalField(max_digits=7, decimal_places=2)
    question_text = models.TextField()
    explanation = models.TextField(blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "position"], name="unique_attempt_question_position"
            )
        ]


class AttemptOption(models.Model):
    attempt_question = models.ForeignKey(
        AttemptQuestion, on_delete=models.CASCADE, related_name="options"
    )
    source_option = models.ForeignKey(Option, null=True, on_delete=models.SET_NULL)
    position = models.PositiveIntegerField()
    option_text = models.TextField()
    is_correct_snapshot = models.BooleanField()

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["attempt_question", "position"], name="unique_attempt_option_position"
            )
        ]


class Answer(models.Model):
    attempt_question = models.OneToOneField(
        AttemptQuestion, on_delete=models.CASCADE, related_name="answer"
    )
    selected_option = models.ForeignKey(
        AttemptOption, null=True, blank=True, on_delete=models.SET_NULL
    )
    answered_at = models.DateTimeField(auto_now=True)
    is_correct = models.BooleanField(null=True)
