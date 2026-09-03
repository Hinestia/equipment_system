from django.urls import path
from . import views

app_name = "documents"

urlpatterns = [
    path("", views.document_list, name="list"),
    path("<int:pk>/", views.document_detail, name="detail"),
    path("acts/", views.act_menu, name="act_menu"),
    path("act/<str:code>/create/", views.create_act, name="create_act"),
    path("ledger/<str:code>/create/", views.create_ledger, name="create_ledger"),
    path("list/employee/<int:employee_pk>/create/", views.create_list_by_employee, name="create_list_employee"),
    path("list/location/<int:location_pk>/create/", views.create_list_by_location, name="create_list_location"),
    path("list/department/<int:department_pk>/create/", views.create_list_by_department, name="create_list_department"),
    path("card/<int:equipment_pk>/create/", views.create_card, name="create_card"),
    path("label/<int:equipment_pk>/create/", views.create_label, name="create_label"),
    path("labels/sheet/", views.create_label_sheet, name="create_label_sheet"),
    path("workstation-act/<int:workstation_pk>/create/", views.create_workstation_assembly_act, name="create_workstation_act"),
]
