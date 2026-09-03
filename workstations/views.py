from django.contrib import messages
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from .models import Workstation
from employees.models import Department, Employee, Location
from equipment.models import Equipment


def workstation_list(request):
    """Список всех сборок с количеством компонентов и суммарной стоимостью.
    Поддерживает поиск по названию сборки (в т.ч. по её оборудованию/ответственному)
    и фильтр по подразделению (через местонахождение сборки)."""
    workstations = Workstation.objects.select_related(
        "location", "location__department", "responsible_employee"
    ).all()

    query = request.GET.get("q", "").strip()
    if query:
        workstations = workstations.filter(
            Q(name__icontains=query)
            | Q(responsible_employee__full_name__icontains=query)
            | Q(equipment_items__inventory_number__icontains=query)
            | Q(equipment_items__name__icontains=query)
        ).distinct()

    department_id = request.GET.get("department")
    if department_id:
        workstations = workstations.filter(location__department_id=department_id)

    rows = []
    for ws in workstations:
        items = ws.equipment_items.all()
        rows.append({
            "workstation": ws,
            "count": items.count(),
            "total_cost": items.aggregate(total=Sum("purchase_cost"))["total"] or 0,
        })

    context = {
        "rows": rows,
        "departments": Department.objects.all(),
        "query": query,
        "selected_department": department_id or "",
    }
    return render(request, "workstations/workstation_list.html", context)


def workstation_detail(request, pk):
    """Детальная страница сборки: состав компонентов, добавление/удаление."""
    workstation = get_object_or_404(
        Workstation.objects.select_related("location", "responsible_employee"), pk=pk
    )
    components = workstation.equipment_items.select_related("category", "status").all()
    total_cost = components.aggregate(total=Sum("purchase_cost"))["total"] or 0
    # Оборудование, ещё не входящее ни в одну сборку — кандидаты на добавление.
    available_equipment = Equipment.objects.filter(workstation__isnull=True).select_related("category")
    return render(request, "workstations/workstation_detail.html", {
        "workstation": workstation, "components": components, "total_cost": total_cost,
        "available_equipment": available_equipment,
    })


def workstation_create(request):
    """Создание новой сборки (рабочего места / ПК)."""
    locations = Location.objects.all()
    employees = Employee.objects.filter(is_active=True)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if not name:
            messages.error(request, "Укажите название сборки.")
        else:
            ws = Workstation.objects.create(
                name=name,
                location_id=request.POST.get("location") or None,
                responsible_employee_id=request.POST.get("responsible_employee") or None,
                notes=request.POST.get("notes", "").strip(),
            )
            messages.success(request, f"Сборка «{ws.name}» создана. Теперь добавьте в неё оборудование.")
            return redirect("workstations:detail", pk=ws.pk)

    return render(request, "workstations/workstation_form.html", {
        "locations": locations, "employees": employees,
    })


def workstation_add_component(request, pk):
    """Добавить одну или несколько единиц оборудования в сборку."""
    workstation = get_object_or_404(Workstation, pk=pk)
    if request.method == "POST":
        equipment_ids = request.POST.getlist("equipment")
        if not equipment_ids:
            messages.warning(request, "Не выбрано ни одной единицы оборудования.")
        else:
            updated = Equipment.objects.filter(pk__in=equipment_ids, workstation__isnull=True).update(
                workstation=workstation
            )
            # Заодно синхронизируем местонахождение/ответственного у добавленных единиц
            # со сборкой, если у сборки они заданы — чтобы реестр не расходился со сборкой.
            if workstation.location_id or workstation.responsible_employee_id:
                items = Equipment.objects.filter(pk__in=equipment_ids)
                for eq in items:
                    changed_fields = []
                    if workstation.location_id and eq.current_location_id != workstation.location_id:
                        eq.current_location_id = workstation.location_id
                        changed_fields.append("current_location")
                    if workstation.responsible_employee_id and eq.responsible_employee_id != workstation.responsible_employee_id:
                        eq.responsible_employee_id = workstation.responsible_employee_id
                        changed_fields.append("responsible_employee")
                    if changed_fields:
                        eq.save(update_fields=changed_fields + ["updated_at"])
            messages.success(request, f"Добавлено единиц оборудования: {updated}.")
    return redirect("workstations:detail", pk=workstation.pk)


def workstation_remove_component(request, pk, equipment_pk):
    """Убрать единицу оборудования из сборки (сама единица остаётся в реестре)."""
    workstation = get_object_or_404(Workstation, pk=pk)
    Equipment.objects.filter(pk=equipment_pk, workstation=workstation).update(workstation=None)
    messages.success(request, "Оборудование исключено из сборки.")
    return redirect("workstations:detail", pk=workstation.pk)


def workstation_delete(request, pk):
    """Расформировать сборку — оборудование остаётся в реестре, просто теряет привязку."""
    workstation = get_object_or_404(Workstation, pk=pk)
    if request.method == "POST":
        name = workstation.name
        workstation.equipment_items.update(workstation=None)
        workstation.delete()
        messages.success(request, f"Сборка «{name}» расформирована. Оборудование осталось в реестре.")
        return redirect("workstations:list")
    return render(request, "workstations/workstation_confirm_delete.html", {"workstation": workstation})
