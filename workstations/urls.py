from django.urls import path
from . import views

app_name = "workstations"

urlpatterns = [
    path("", views.workstation_list, name="list"),
    path("add/", views.workstation_create, name="create"),
    path("<int:pk>/", views.workstation_detail, name="detail"),
    path("<int:pk>/edit/", views.workstation_edit, name="edit"),
    path("<int:pk>/add-component/", views.workstation_add_component, name="add_component"),
    path("<int:pk>/remove-component/<int:equipment_pk>/", views.workstation_remove_component, name="remove_component"),
    path("<int:pk>/delete/", views.workstation_delete, name="delete"),
]
