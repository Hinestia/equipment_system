from django.contrib import admin
from .models import Department, Location, Employee


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "parent_department")
    search_fields = ("name", "code")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "building", "floor")
    list_filter = ("department",)
    search_fields = ("name", "building")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "position", "department", "is_mol", "is_active")
    list_filter = ("department", "is_mol", "is_active")
    search_fields = ("full_name", "position", "email", "phone")
