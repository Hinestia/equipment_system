from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q

from .models import Equipment, EquipmentCategory, EquipmentStatus
from employees.models import Employee, Location
from history.models import MovementHistory, MovementEventType


def equipment_list(request):
    """Реестр оборудования со поиском и фильтрацией."""
    items = Equipment.objects.select_related(
        "category", "status", "current_location", "responsible_employee"
    ).all()

    query = request.GET.get("q", "").strip()
    if query:
        items = items.filter(
            Q(inventory_number__icontains=query)
            | Q(serial_number__icontains=query)
            | Q(name__icontains=query)
            | Q(model__icontains=query)
        )

    category_id = request.GET.get("category")
    if category_id:
        items = items.filter(category_id=category_id)

    status_id = request.GET.get("status")
    if status_id:
        items = items.filter(status_id=status_id)

    location_id = request.GET.get("location")
    if location_id:
        items = items.filter(current_location_id=location_id)

    employee_id = request.GET.get("employee")
    if employee_id:
        items = items.filter(responsible_employee_id=employee_id)

    context = {
        "items": items,
        "categories": EquipmentCategory.objects.all(),
        "statuses": EquipmentStatus.objects.all(),
        "locations": Location.objects.all(),
        "employees": Employee.objects.filter(is_active=True),
        "query": query,
        "selected_category": category_id or "",
        "selected_status": status_id or "",
        "selected_location": location_id or "",
        "selected_employee": employee_id or "",
        "total_count": items.count(),
    }
    return render(request, "equipment/equipment_list.html", context)


def equipment_detail(request, pk):
    """Карточка единицы оборудования с историей эксплуатации."""
    item = get_object_or_404(
        Equipment.objects.select_related(
            "category", "status", "current_location", "responsible_employee"
        ),
        pk=pk,
    )
    events = item.movement_events.select_related(
        "from_employee", "to_employee", "from_location", "to_location"
    ).all()
    return render(request, "equipment/equipment_detail.html", {"item": item, "events": events})


def equipment_create(request):
    """Добавление новой единицы оборудования (постановка на учёт)."""
    categories = EquipmentCategory.objects.all()
    statuses = EquipmentStatus.objects.all()
    locations = Location.objects.all()
    employees = Employee.objects.filter(is_active=True)

    if request.method == "POST":
        inventory_number = request.POST.get("inventory_number", "").strip()
        name = request.POST.get("name", "").strip()

        if not inventory_number or not name:
            messages.error(request, "Инвентарный номер и наименование обязательны.")
        else:
            item = Equipment.objects.create(
                inventory_number=inventory_number,
                serial_number=request.POST.get("serial_number", "").strip(),
                name=name,
                model=request.POST.get("model", "").strip(),
                category_id=request.POST.get("category") or None,
                specifications=request.POST.get("specifications", "").strip(),
                purchase_date=request.POST.get("purchase_date") or None,
                purchase_cost=request.POST.get("purchase_cost") or None,
                status_id=request.POST.get("status") or None,
                current_location_id=request.POST.get("current_location") or None,
                responsible_employee_id=request.POST.get("responsible_employee") or None,
                notes=request.POST.get("notes", "").strip(),
            )
            # Фиксируем первичную постановку на учёт в истории.
            MovementHistory.objects.create(
                equipment=item,
                event_type=MovementEventType.RECEIPT,
                to_employee=item.responsible_employee,
                to_location=item.current_location,
                comment="Первичная постановка на учёт",
            )
            messages.success(request, f"Оборудование «{item.name}» добавлено в реестр.")
            return redirect("equipment:detail", pk=item.pk)

    return render(request, "equipment/equipment_form.html", {
        "categories": categories, "statuses": statuses,
        "locations": locations, "employees": employees,
    })


def equipment_status_change(request, pk):
    """Изменить статус оборудования (например, отправить в ремонт) с фиксацией в истории."""
    item = get_object_or_404(Equipment, pk=pk)
    statuses = EquipmentStatus.objects.all()

    if request.method == "POST":
        new_status_id = request.POST.get("status") or None
        comment = request.POST.get("comment", "").strip()

        old_status = item.status
        if str(old_status.pk if old_status else None) == str(new_status_id or ""):
            messages.warning(request, "Статус не изменился.")
            return redirect("equipment:detail", pk=item.pk)

        item.status_id = new_status_id
        item.save(update_fields=["status", "updated_at"])

        new_status_name = (
            EquipmentStatus.objects.filter(pk=new_status_id).values_list("name", flat=True).first()
            if new_status_id else ""
        )
        # Определяем тип события по названию нового статуса, чтобы журнал был информативнее.
        if new_status_name and "ремонт" in new_status_name.lower():
            event_type = MovementEventType.REPAIR
        elif old_status and "ремонт" in old_status.name.lower():
            event_type = MovementEventType.RETURN_FROM_REPAIR
        else:
            event_type = MovementEventType.STATUS_CHANGE

        MovementHistory.objects.create(
            equipment=item,
            event_type=event_type,
            comment=comment or f"Статус изменён: «{old_status or '—'}» → «{item.status or '—'}»",
        )
        messages.success(request, "Статус обновлён.")
        return redirect("equipment:detail", pk=item.pk)

    return render(request, "equipment/equipment_status_change.html", {
        "item": item, "statuses": statuses,
    })


def equipment_transfer(request, pk):
    """Передать оборудование другому сотруднику и/или переместить в другое помещение."""
    item = get_object_or_404(Equipment, pk=pk)
    employees = Employee.objects.filter(is_active=True)
    locations = Location.objects.all()

    if request.method == "POST":
        new_employee_id = request.POST.get("to_employee") or None
        new_location_id = request.POST.get("to_location") or None
        comment = request.POST.get("comment", "").strip()

        old_employee = item.responsible_employee
        old_location = item.current_location

        old_employee_id = old_employee.pk if old_employee else None
        old_location_id = old_location.pk if old_location else None

        employee_changed = str(old_employee_id) != str(new_employee_id or "")
        location_changed = str(old_location_id) != str(new_location_id or "")

        if not employee_changed and not location_changed:
            messages.warning(request, "Не указано ни новое ответственное лицо, ни новое местонахождение.")
            return redirect("equipment:detail", pk=item.pk)

        item.responsible_employee_id = new_employee_id
        item.current_location_id = new_location_id
        item.save(update_fields=["responsible_employee", "current_location", "updated_at"])

        if employee_changed:
            event_type = MovementEventType.TRANSFER
        else:
            event_type = MovementEventType.MOVE

        MovementHistory.objects.create(
            equipment=item,
            event_type=event_type,
            from_employee=old_employee,
            to_employee_id=new_employee_id,
            from_location=old_location,
            to_location_id=new_location_id,
            comment=comment,
        )
        messages.success(request, "Перемещение зафиксировано.")
        return redirect("equipment:detail", pk=item.pk)

    return render(request, "equipment/equipment_transfer.html", {
        "item": item, "employees": employees, "locations": locations,
    })
