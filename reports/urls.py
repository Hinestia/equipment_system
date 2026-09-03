from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("mol/", views.mol_report_list, name="mol_list"),
    path("mol/<int:employee_pk>/", views.mol_report_detail, name="mol_detail"),
    path("export/equipment.xlsx", views.export_equipment_excel, name="export_equipment_excel"),
    path("export/workstations.xlsx", views.export_workstations_excel, name="export_workstations_excel"),
]
