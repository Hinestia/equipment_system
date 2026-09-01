from django.urls import path
from . import views

app_name = "equipment"

urlpatterns = [
    path("", views.equipment_list, name="list"),
    path("add/", views.equipment_create, name="create"),
    path("<int:pk>/", views.equipment_detail, name="detail"),
    path("<int:pk>/edit/", views.equipment_edit, name="edit"),
    path("<int:pk>/transfer/", views.equipment_transfer, name="transfer"),
    path("<int:pk>/status/", views.equipment_status_change, name="status_change"),
]
