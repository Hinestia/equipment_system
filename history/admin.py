from django.contrib import admin
from .models import MovementHistory


@admin.register(MovementHistory)
class MovementHistoryAdmin(admin.ModelAdmin):
    list_display = ("equipment", "event_type", "event_date", "from_employee", "to_employee")
    list_filter = ("event_type",)
    search_fields = ("equipment__inventory_number", "equipment__name")
    readonly_fields = [f.name for f in MovementHistory._meta.fields]

    def has_change_permission(self, request, obj=None):
        # Журнал истории неизменяемый — запрещаем редактирование записей.
        return False

    def has_delete_permission(self, request, obj=None):
        # И удаление тоже — это лог событий, а не редактируемая таблица.
        return False
