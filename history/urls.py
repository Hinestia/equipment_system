from django.urls import path
from . import views

app_name = "history"

urlpatterns = [
    path("", views.history_list, name="list"),
]
