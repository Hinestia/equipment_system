from django.contrib import admin
from .models import EquipmentCategory, EquipmentStatus, Equipment


@admin.register(EquipmentCategory)
class EquipmentCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(EquipmentStatus)
class EquipmentStatusAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = (
        "inventory_number", "name", "category", "status",
        "current_location", "responsible_employee",
    )
    list_filter = ("category", "status", "current_location")
    search_fields = ("inventory_number", "serial_number", "name", "model")
