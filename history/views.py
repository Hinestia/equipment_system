from django.db.models import Q
from django.shortcuts import render

from .models import MovementHistory, MovementEventType
from employees.models import Employee, Location
from equipment.models import Equipment


def history_list(request):
    """Общий журнал всех событий по всему оборудованию, с фильтрами."""
    events = MovementHistory.objects.select_related(
        "equipment", "from_employee", "to_employee", "from_location", "to_location"
    ).all()

    event_type = request.GET.get("event_type")
    if event_type:
        events = events.filter(event_type=event_type)

    equipment_id = request.GET.get("equipment")
    if equipment_id:
        events = events.filter(equipment_id=equipment_id)

    employee_id = request.GET.get("employee")
    if employee_id:
        events = events.filter(
            Q(from_employee_id=employee_id) | Q(to_employee_id=employee_id)
        )

    location_id = request.GET.get("location")
    if location_id:
        events = events.filter(
            Q(from_location_id=location_id) | Q(to_location_id=location_id)
        )

    date_from = request.GET.get("date_from")
    if date_from:
        events = events.filter(event_date__date__gte=date_from)

    date_to = request.GET.get("date_to")
    if date_to:
        events = events.filter(event_date__date__lte=date_to)

    events = events.distinct().order_by("-event_date")

    context = {
        "events": events,
        "event_types": MovementEventType.choices,
        "equipment_items": Equipment.objects.all(),
        "employees": Employee.objects.filter(is_active=True),
        "locations": Location.objects.all(),
        "selected_event_type": event_type or "",
        "selected_equipment": equipment_id or "",
        "selected_employee": employee_id or "",
        "selected_location": location_id or "",
        "date_from": date_from or "",
        "date_to": date_to or "",
        "total_count": events.count(),
    }
    return render(request, "history/history_list.html", context)
