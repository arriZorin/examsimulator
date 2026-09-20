from django.urls import path

from . import views

app_name = "question_imports"
urlpatterns = [
    path("", views.upload, name="upload"),
    path("confirm/", views.confirm, name="confirm"),
]
