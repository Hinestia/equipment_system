from django.contrib import admin
from .models import Workstation


@admin.register(Workstation)
class WorkstationAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "responsible_employee", "created_at")
    list_filter = ("location",)
    search_fields = ("name",)
