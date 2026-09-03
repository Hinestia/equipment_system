from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.http import FileResponse

from .models import Document, DocumentEquipment, DocumentType
from .services import generator, label_generator

from employees.models import Department, Employee, Location
from equipment.models import Equipment, EquipmentStatus
from history.models import MovementEventType, MovementHistory
from workstations.models import Workstation

# Соответствие кода акта -> тип события в истории, фиксируемый при формировании акта.
ACT_EVENT_TYPES = {
    "act_transfer": MovementEventType.TRANSFER,
    "act_move": MovementEventType.MOVE,
    "act_return": MovementEventType.RETURN,
    "act_write_off": MovementEventType.WRITE_OFF,
}

ACT_LABELS = {
    "act_transfer": "Акт приёма-передачи",
    "act_move": "Акт внутреннего перемещения",
    "act_return": "Акт возврата",
    "act_write_off": "Акт списания",
}


def _next_number(doc_type, pk):
    prefix = doc_type.number_prefix or doc_type.code.upper()
    return f"{prefix}-{pk:04d}"


def document_list(request):
    """Реестр всех сформированных документов."""
    documents = Document.objects.select_related("document_type").prefetch_related("items__equipment")
    document_type_id = request.GET.get("document_type")
    if document_type_id:
        documents = documents.filter(document_type_id=document_type_id)
    return render(request, "documents/document_list.html", {
        "documents": documents,
        "document_types": DocumentType.objects.all(),
        "selected_type": document_type_id or "",
    })


def document_detail(request, pk):
    document = get_object_or_404(Document.objects.select_related("document_type"), pk=pk)
    items = document.items.select_related("equipment").all()
    return render(request, "documents/document_detail.html", {"document": document, "items": items})


def act_menu(request):
    """Страница выбора типа акта для формирования."""
    act_types = DocumentType.objects.filter(code__in=ACT_EVENT_TYPES.keys())
    return render(request, "documents/act_menu.html", {"act_types": act_types})


def create_act(request, code):
    """
    Универсальная форма формирования акта (приёма-передачи/перемещения/возврата/списания).
    При сохранении: создаёт Document + DocumentEquipment, выполняет соответствующее
    изменение состояния оборудования и пишет событие в историю со ссылкой на документ,
    затем генерирует .docx-файл.
    """
    if code not in ACT_EVENT_TYPES:
        messages.error(request, "Неизвестный тип акта.")
        return redirect("documents:list")

    doc_type = get_object_or_404(DocumentType, code=code)
    equipment_items = Equipment.objects.select_related(
        "category", "status", "current_location", "responsible_employee"
    ).all()
    employees = Employee.objects.filter(is_active=True)
    locations = Location.objects.all()
    label = ACT_LABELS[code]

    if request.method == "POST":
        equipment_ids = request.POST.getlist("equipment")
        to_employee_id = request.POST.get("to_employee") or None
        to_location_id = request.POST.get("to_location") or None
        reason = request.POST.get("reason", "").strip()
        comment = request.POST.get("comment", "").strip()

        error = None
        if not equipment_ids:
            error = "Выберите хотя бы одну единицу оборудования."
        elif code == "act_write_off" and not reason:
            error = "Для акта списания укажите причину списания."
        elif code in ("act_transfer",) and not to_employee_id:
            error = "Укажите сотрудника, которому передаётся оборудование."

        if error:
            messages.error(request, error)
            return render(request, "documents/act_form.html", {
                "doc_type": doc_type, "label": label, "code": code,
                "equipment_items": equipment_items, "employees": employees, "locations": locations,
            })

        document = Document.objects.create(
            document_type=doc_type,
            to_employee_id=to_employee_id,
            to_location_id=to_location_id,
            reason=reason,
            comment=comment,
        )
        document.number = _next_number(doc_type, document.pk)
        document.save(update_fields=["number"])

        selected_equipment = list(Equipment.objects.filter(pk__in=equipment_ids))
        event_type = ACT_EVENT_TYPES[code]

        # Поля "от кого"/"откуда" в шапке акта берутся из ТЕКУЩЕГО состояния
        # первой выбранной единицы оборудования (до того, как оно изменится) —
        # это то, кто фактически "передаёт" на момент оформления акта.
        # Если в акт включено несколько единиц с разными предыдущими держателями/
        # местонахождением, в шапке будет отражено состояние первой из них —
        # для типового случая (акт на партию от одного держателя) этого достаточно.
        if selected_equipment and code in ("act_transfer", "act_return"):
            document.from_employee_id = selected_equipment[0].responsible_employee_id
        if selected_equipment and code in ("act_transfer", "act_move"):
            document.from_location_id = selected_equipment[0].current_location_id
        if document.from_employee_id or document.from_location_id:
            document.save(update_fields=["from_employee", "from_location"])

        for eq in selected_equipment:
            DocumentEquipment.objects.create(document=document, equipment=eq)

            old_employee = eq.responsible_employee
            old_location = eq.current_location

            if code == "act_transfer":
                eq.responsible_employee_id = to_employee_id
                if to_location_id:
                    eq.current_location_id = to_location_id
                eq.save(update_fields=["responsible_employee", "current_location", "updated_at"])
                MovementHistory.objects.create(
                    equipment=eq, event_type=event_type, document=document,
                    from_employee=old_employee, to_employee_id=to_employee_id,
                    from_location=old_location, to_location_id=to_location_id or (old_location.pk if old_location else None),
                    comment=comment,
                )
            elif code == "act_move":
                eq.current_location_id = to_location_id
                eq.save(update_fields=["current_location", "updated_at"])
                MovementHistory.objects.create(
                    equipment=eq, event_type=event_type, document=document,
                    from_location=old_location, to_location_id=to_location_id,
                    comment=comment,
                )
            elif code == "act_return":
                eq.responsible_employee = None
                if to_location_id:
                    eq.current_location_id = to_location_id
                eq.save(update_fields=["responsible_employee", "current_location", "updated_at"])
                MovementHistory.objects.create(
                    equipment=eq, event_type=event_type, document=document,
                    from_employee=old_employee, to_location_id=to_location_id,
                    comment=comment or reason,
                )
            elif code == "act_write_off":
                written_off_status, _ = EquipmentStatus.objects.get_or_create(name="Списано")
                eq.status = written_off_status
                eq.save(update_fields=["status", "updated_at"])
                MovementHistory.objects.create(
                    equipment=eq, event_type=event_type, document=document,
                    comment=comment or reason,
                )

        generator.generate_document_file(document)
        messages.success(request, f"{label} №{document.number} сформирован — файл готов к скачиванию.")
        return redirect("documents:detail", pk=document.pk)

    return render(request, "documents/act_form.html", {
        "doc_type": doc_type, "label": label, "code": code,
        "equipment_items": equipment_items, "employees": employees, "locations": locations,
    })


def _create_statement_document(doc_type_code, title, equipment_qs, **extra_fields):
    doc_type = get_object_or_404(DocumentType, code=doc_type_code)
    document = Document.objects.create(document_type=doc_type, **extra_fields)
    document.number = _next_number(doc_type, document.pk)
    document.save(update_fields=["number"])
    for eq in equipment_qs:
        DocumentEquipment.objects.create(document=document, equipment=eq)
    generator.generate_document_file(document, title=title)
    return document


def create_ledger(request, code):
    """Ведомость оборудования (весь реестр) или инвентаризационная ведомость (тот же состав)."""
    doc_type = get_object_or_404(DocumentType, code=code)
    equipment_qs = Equipment.objects.select_related(
        "category", "status", "current_location", "responsible_employee"
    ).all()
    document = _create_statement_document(code, doc_type.name, equipment_qs)
    messages.success(request, f"{doc_type.name} №{document.number} сформирована.")
    return redirect("documents:detail", pk=document.pk)


def create_list_by_employee(request, employee_pk):
    employee = get_object_or_404(Employee, pk=employee_pk)
    equipment_qs = Equipment.objects.filter(responsible_employee=employee).select_related(
        "category", "status", "current_location", "responsible_employee"
    )
    document = _create_statement_document(
        "list_employee", f"Список оборудования сотрудника: {employee.full_name}",
        equipment_qs, to_employee=employee,
    )
    messages.success(request, f"Список оборудования сотрудника «{employee.full_name}» сформирован.")
    return redirect("documents:detail", pk=document.pk)


def create_list_by_location(request, location_pk):
    location = get_object_or_404(Location, pk=location_pk)
    equipment_qs = Equipment.objects.filter(current_location=location).select_related(
        "category", "status", "current_location", "responsible_employee"
    )
    document = _create_statement_document(
        "list_location", f"Список оборудования кабинета: {location.name}",
        equipment_qs, to_location=location,
    )
    messages.success(request, f"Список оборудования кабинета «{location.name}» сформирован.")
    return redirect("documents:detail", pk=document.pk)


def create_list_by_department(request, department_pk):
    department = get_object_or_404(Department, pk=department_pk)
    equipment_qs = Equipment.objects.filter(current_location__department=department).select_related(
        "category", "status", "current_location", "responsible_employee"
    )
    document = _create_statement_document(
        "list_department", f"Список оборудования подразделения: {department.name}",
        equipment_qs,
    )
    messages.success(request, f"Список оборудования подразделения «{department.name}» сформирован.")
    return redirect("documents:detail", pk=document.pk)


def create_card(request, equipment_pk):
    """
    Карточка единицы имущества формируется «на лету» и сразу отдаётся на скачивание —
    в отличие от актов и ведомостей, она не сохраняется как отдельная запись в реестре
    документов (это разовый печатный вывод текущего состояния карточки).
    """
    equipment = get_object_or_404(Equipment, pk=equipment_pk)
    buffer = generator.render_equipment_card(equipment)
    filename = f"karta_{equipment.inventory_number}.docx"
    return FileResponse(buffer, as_attachment=True, filename=filename)


def create_label(request, equipment_pk):
    """
    Маленькая печатная бирка (PDF, 90x50 мм) с QR-кодом инвентарного номера —
    для наклейки на само оборудование. Формируется на лету, не сохраняется
    как документ в реестре.
    """
    equipment = get_object_or_404(Equipment, pk=equipment_pk)
    buffer = label_generator.generate_equipment_label(equipment)
    filename = f"birka_{equipment.inventory_number}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename, content_type="application/pdf")


def create_label_sheet(request):
    """
    Лист А4 с несколькими бирками сразу (сетка 2x5, с переходом на следующую
    страницу, если выбрано больше 10 единиц) — чтобы не скачивать и не печатать
    бирки по одной. Список единиц оборудования передаётся POST-ом с формы
    (чекбоксы на странице реестра) или GET-параметрами ?equipment=1&equipment=2...
    """
    if request.method == "POST":
        equipment_ids = request.POST.getlist("equipment")
    else:
        equipment_ids = request.GET.getlist("equipment")

    if not equipment_ids:
        messages.warning(request, "Не выбрано ни одной единицы оборудования для печати бирок.")
        return redirect("equipment:list")

    equipment_qs = Equipment.objects.filter(pk__in=equipment_ids).select_related("responsible_employee")
    buffer = label_generator.generate_label_sheet(equipment_qs)
    return FileResponse(buffer, as_attachment=True, filename="birki_list_a4.pdf", content_type="application/pdf")


def create_workstation_assembly_act(request, workstation_pk):
    """
    Акт формирования сборки — документирует текущий состав сборки (рабочего
    места/ПК) на момент формирования: какие единицы оборудования в неё входят,
    где она расположена и кто за неё отвечает. Можно формировать повторно в
    любой момент — акт всегда отражает состав сборки на текущий момент.
    """
    workstation = get_object_or_404(Workstation, pk=workstation_pk)
    doc_type = get_object_or_404(DocumentType, code="act_assembly")
    components = list(workstation.equipment_items.all())

    if not components:
        messages.warning(request, "В сборке нет оборудования — акт формировать не из чего.")
        return redirect("workstations:detail", pk=workstation.pk)

    location_str = str(workstation.location) if workstation.location else "—"
    employee_str = str(workstation.responsible_employee) if workstation.responsible_employee else "—"

    document = Document.objects.create(
        document_type=doc_type,
        reason=workstation.name,
        comment=f"Местонахождение: {location_str} · Ответственный: {employee_str}",
    )
    document.number = _next_number(doc_type, document.pk)
    document.save(update_fields=["number"])

    for eq in components:
        DocumentEquipment.objects.create(document=document, equipment=eq)
        MovementHistory.objects.create(
            equipment=eq, event_type=MovementEventType.ASSEMBLY, document=document,
            comment=f"Включено в сборку «{workstation.name}» (акт {document.number})",
        )

    generator.generate_document_file(document)
    messages.success(request, f"Акт формирования сборки №{document.number} сформирован.")
    return redirect("documents:detail", pk=document.pk)
