from django.urls import path

from . import views

app_name = "exams"
urlpatterns = [
    path("exams/", views.exam_list, name="list"),
    path("exams/<int:pk>/", views.exam_detail, name="detail"),
    path("exams/<int:pk>/start/", views.start, name="start"),
    path("attempts/<int:pk>/", views.take, name="take"),
    path("attempts/<int:pk>/answer/", views.answer, name="answer"),
    path("attempts/<int:pk>/submit/", views.submit, name="submit"),
    path("attempts/<int:pk>/result/", views.result, name="result"),
    path("attempts/<int:pk>/evaluation/", views.evaluation, name="evaluation"),
]
