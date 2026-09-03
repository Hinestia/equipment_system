import io
from datetime import date, timedelta

from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from openpyxl import Workbook
from openpyxl.styles import Font

from employees.models import Employee
from equipment.models import Equipment, EquipmentStatus, EquipmentCategory
from history.models import MovementHistory
from workstations.models import Workstation
from .services.chart_builder import build_movement_chart, last_n_months_labels, gauge_arc_endpoint


def dashboard(request):
    """Главная страница со сводными показателями по всему парку оборудования."""
    total_equipment = Equipment.objects.count()

    by_status = (
        Equipment.objects.values("status__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    by_category_cost = (
        Equipment.objects.values("category__name")
        .annotate(count=Count("id"), total=Sum("purchase_cost"))
        .order_by("-total")[:4]
    )
    total_cost = Equipment.objects.aggregate(total=Sum("purchase_cost"))["total"] or 0

    recent_events = MovementHistory.objects.select_related(
        "equipment", "from_employee", "to_employee", "from_location", "to_location"
    ).order_by("-event_date")[:6]

    mol_count = Employee.objects.filter(is_mol=True, is_active=True).count()
    workstation_count = Workstation.objects.count()

    # ---- Карточки материально ответственных лиц (топ-3 по стоимости закреплённого) ----
    today = date.today()
    month_start = date(today.year, today.month, 1)
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = date(prev_month_end.year, prev_month_end.month, 1)

    mol_cards = []
    mol_employees = (
        Employee.objects.filter(is_mol=True, is_active=True)
        .annotate(eq_count=Count("equipment_items"), eq_cost=Sum("equipment_items__purchase_cost"))
        .order_by("-eq_cost")[:3]
    )
    max_cost = max((e.eq_cost or 0 for e in mol_employees), default=0) or 1
    for emp in mol_employees:
        eq_qs = Equipment.objects.filter(responsible_employee=emp)
        eq_count = eq_qs.count()
        in_use = eq_qs.filter(status__name__icontains="эксплуатац").count()
        utilization = round((in_use / eq_count) * 100) if eq_count else 0

        events_this_month = MovementHistory.objects.filter(
            Q(from_employee=emp) | Q(to_employee=emp), event_date__gte=month_start
        ).count()
        events_prev_month = MovementHistory.objects.filter(
            Q(from_employee=emp) | Q(to_employee=emp),
            event_date__gte=prev_month_start, event_date__lt=month_start,
        ).count()

        mol_cards.append({
            "employee": emp,
            "count": eq_count,
            "acts_this_month": events_this_month,
            "total_cost": emp.eq_cost or 0,
            "bar_pct": round(((emp.eq_cost or 0) / max_cost) * 100) if max_cost else 0,
            "trend_up": events_this_month >= events_prev_month,
        })

    # ---- График "Движение оборудования" за последние 9 месяцев ----
    months = last_n_months_labels(9, today=today)
    monthly_counts = []
    for year, month, label in months:
        next_month = date(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
        count = MovementHistory.objects.filter(
            event_date__gte=date(year, month, 1), event_date__lt=next_month
        ).count()
        monthly_counts.append({"label": label, "count": count})
    chart = build_movement_chart(monthly_counts)

    # ---- Заполненность карточек оборудования (насколько заполнены ключевые поля) ----
    if total_equipment:
        complete_count = Equipment.objects.exclude(
            Q(serial_number="") | Q(model="") | Q(purchase_date__isnull=True) |
            Q(purchase_cost__isnull=True) | Q(specifications="")
        ).count()
        completeness_pct = round((complete_count / total_equipment) * 100, 2)
    else:
        completeness_pct = 0

    gauge_x, gauge_y = gauge_arc_endpoint(completeness_pct)

    context = {
        "total_equipment": total_equipment,
        "by_status": by_status,
        "by_category_cost": by_category_cost,
        "total_cost": total_cost,
        "workstation_count": workstation_count,
        "recent_events": recent_events,
        "mol_count": mol_count,
        "mol_cards": mol_cards,
        "chart": chart,
        "completeness_pct": completeness_pct,
        "gauge_x": gauge_x,
        "gauge_y": gauge_y,
        "today": today,
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
