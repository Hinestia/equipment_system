import io

from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from openpyxl import Workbook
from openpyxl.styles import Font

from employees.models import Employee
from equipment.models import Equipment, EquipmentStatus, EquipmentCategory
from history.models import MovementHistory


def dashboard(request):
    """Главная страница со сводными показателями по всему парку оборудования."""
    total_equipment = Equipment.objects.count()

    by_status = (
        Equipment.objects.values("status__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    by_category = (
        Equipment.objects.values("category__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    total_cost = Equipment.objects.aggregate(total=Sum("purchase_cost"))["total"] or 0

    recent_events = MovementHistory.objects.select_related(
        "equipment", "from_employee", "to_employee", "from_location", "to_location"
    ).order_by("-event_date")[:8]

    mol_count = Employee.objects.filter(is_mol=True, is_active=True).count()

    context = {
        "total_equipment": total_equipment,
        "by_status": by_status,
        "by_category": by_category,
        "total_cost": total_cost,
        "recent_events": recent_events,
        "mol_count": mol_count,
    }
    return render(request, "reports/dashboard.html", context)


def mol_report_list(request):
    """Список материально ответственных лиц со сводкой по закреплённому оборудованию."""
    mol_employees = Employee.objects.filter(is_mol=True).select_related("department")
    rows = []
    for emp in mol_employees:
        qs = Equipment.objects.filter(responsible_employee=emp)
        rows.append({
            "employee": emp,
            "count": qs.count(),
            "total_cost": qs.aggregate(total=Sum("purchase_cost"))["total"] or 0,
        })
    return render(request, "reports/mol_report_list.html", {"rows": rows})


def mol_report_detail(request, employee_pk):
    """Детальный отчёт по конкретному материально ответственному лицу."""
    employee = get_object_or_404(Employee, pk=employee_pk)
    equipment_items = Equipment.objects.filter(responsible_employee=employee).select_related(
        "category", "status", "current_location"
    )
    total_cost = equipment_items.aggregate(total=Sum("purchase_cost"))["total"] or 0
    return render(request, "reports/mol_report_detail.html", {
        "employee": employee, "equipment_items": equipment_items, "total_cost": total_cost,
    })


def export_equipment_excel(request):
    """
    Экспорт реестра оборудования в Excel с учётом тех же фильтров,
    что применены на странице реестра (передаются в query-параметрах).
    """
    items = Equipment.objects.select_related(
        "category", "status", "current_location", "responsible_employee"
    ).all()

    query = request.GET.get("q", "").strip()
    if query:
        from django.db.models import Q
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

    wb = Workbook()
    ws = wb.active
    ws.title = "Реестр оборудования"

    headers = [
        "Инв. номер", "Серийный номер", "Наименование", "Модель", "Категория",
        "Статус", "Местонахождение", "Ответственный", "Дата поступления",
        "Балансовая стоимость", "Примечания",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for item in items:
        ws.append([
            item.inventory_number,
            item.serial_number,
            item.name,
            item.model,
            str(item.category) if item.category else "",
            str(item.status) if item.status else "",
            str(item.current_location) if item.current_location else "",
            str(item.responsible_employee) if item.responsible_employee else "",
            item.purchase_date.strftime("%d.%m.%Y") if item.purchase_date else "",
            float(item.purchase_cost) if item.purchase_cost else "",
            item.notes,
        ])

    for column_cells in ws.columns:
        length = max((len(str(cell.value)) for cell in column_cells if cell.value), default=10)
        ws.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 40)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="reestr_oborudovaniya.xlsx"'
    return response
