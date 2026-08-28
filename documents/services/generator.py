"""
Единый движок генерации печатных документов.
Не пишите отдельный код под каждый тип акта — добавляйте новый тип
через ACT_TEMPLATES / build_templates.py и используйте generate_document_file.
"""
import io
import os

from django.core.files.base import ContentFile
from docxtpl import DocxTemplate

TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "doc_templates"
)

# Коды типов документов (DocumentType.code) -> файл шаблона .docx
ACT_TEMPLATES = {
    "act_transfer": "transfer_act.docx",
    "act_move": "movement_act.docx",
    "act_return": "return_act.docx",
    "act_write_off": "write_off_act.docx",
}
STATEMENT_TEMPLATE = "statement.docx"
CARD_TEMPLATE = "equipment_card.docx"


def _fmt_date(value):
    if not value:
        return ""
    return value.strftime("%d.%m.%Y")


def _build_act_context(document):
    items = []
    for idx, doc_item in enumerate(
        document.items.select_related("equipment").all(), start=1
    ):
        items.append({
            "index": idx,
            "inventory_number": doc_item.equipment.inventory_number,
            "name": doc_item.equipment.name,
            "serial_number": doc_item.equipment.serial_number,
            "quantity": doc_item.quantity,
        })
    return {
        "number": document.number or str(document.pk),
        "date": _fmt_date(document.date_created),
        "from_employee": str(document.from_employee) if document.from_employee else "",
        "to_employee": str(document.to_employee) if document.to_employee else "",
        "from_location": str(document.from_location) if document.from_location else "",
        "to_location": str(document.to_location) if document.to_location else "",
        "reason": document.reason,
        "comment": document.comment,
        "items": items,
    }


def _build_statement_context(document, title):
    items = []
    doc_items = document.items.select_related(
        "equipment__category", "equipment__status",
        "equipment__current_location", "equipment__responsible_employee",
    ).all()
    for idx, doc_item in enumerate(doc_items, start=1):
        eq = doc_item.equipment
        items.append({
            "index": idx,
            "inventory_number": eq.inventory_number,
            "name": eq.name,
            "category": str(eq.category) if eq.category else "",
            "status": str(eq.status) if eq.status else "",
            "location": str(eq.current_location) if eq.current_location else "",
            "employee": str(eq.responsible_employee) if eq.responsible_employee else "",
        })
    return {
        "title": title,
        "date": _fmt_date(document.date_created),
        "total_count": len(items),
        "items": items,
    }


def generate_document_file(document, title=None):
    """
    Рендерит нужный шаблон по типу документа (document.document_type.code)
    и сохраняет результат в document.file. Возвращает document.
    """
    code = document.document_type.code

    if code in ACT_TEMPLATES:
        template_path = os.path.join(TEMPLATE_DIR, ACT_TEMPLATES[code])
        context = _build_act_context(document)
    else:
        template_path = os.path.join(TEMPLATE_DIR, STATEMENT_TEMPLATE)
        context = _build_statement_context(document, title or document.document_type.name)

    tpl = DocxTemplate(template_path)
    tpl.render(context)

    buffer = io.BytesIO()
    tpl.save(buffer)
    buffer.seek(0)

    filename = f"{code}_{document.pk}.docx"
    document.generated_file.save(filename, ContentFile(buffer.read()), save=True)
    return document


def render_equipment_card(equipment):
    """
    Формирует карточку единицы имущества «на лету» (без сохранения как Document —
    это разовый печатный вывод, а не документ, который нужно хранить в реестре документов).
    Возвращает BytesIO с содержимым .docx.
    """
    tpl = DocxTemplate(os.path.join(TEMPLATE_DIR, CARD_TEMPLATE))

    history_rows = []
    events = equipment.movement_events.select_related(
        "from_employee", "to_employee", "from_location", "to_location"
    ).all()
    for event in events:
        target_parts = [str(x) for x in (event.to_employee, event.to_location) if x]
        history_rows.append({
            "date": event.event_date.strftime("%d.%m.%Y %H:%M"),
            "type": event.get_event_type_display(),
            "target": ", ".join(target_parts) if target_parts else "—",
            "comment": event.comment,
        })

    context = {
        "inventory_number": equipment.inventory_number,
        "serial_number": equipment.serial_number,
        "name": equipment.name,
        "model": equipment.model,
        "category": str(equipment.category) if equipment.category else "",
        "specifications": equipment.specifications,
        "purchase_date": _fmt_date(equipment.purchase_date),
        "purchase_cost": str(equipment.purchase_cost) if equipment.purchase_cost else "",
        "status": str(equipment.status) if equipment.status else "",
        "location": str(equipment.current_location) if equipment.current_location else "",
        "employee": str(equipment.responsible_employee) if equipment.responsible_employee else "",
        "notes": equipment.notes,
        "history": history_rows,
    }
    tpl.render(context)

    buffer = io.BytesIO()
    tpl.save(buffer)
    buffer.seek(0)
    return buffer
