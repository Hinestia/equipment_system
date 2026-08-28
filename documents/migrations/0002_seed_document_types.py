from django.db import migrations

DOCUMENT_TYPES = [
    {
        "name": "Акт приёма-передачи",
        "code": "act_transfer",
        "template_filename": "transfer_act.docx",
        "number_prefix": "АПП",
    },
    {
        "name": "Акт внутреннего перемещения",
        "code": "act_move",
        "template_filename": "movement_act.docx",
        "number_prefix": "АВП",
    },
    {
        "name": "Акт возврата",
        "code": "act_return",
        "template_filename": "return_act.docx",
        "number_prefix": "АВ",
    },
    {
        "name": "Акт списания",
        "code": "act_write_off",
        "template_filename": "write_off_act.docx",
        "number_prefix": "АС",
    },
    {
        "name": "Ведомость оборудования",
        "code": "ledger_equipment",
        "template_filename": "statement.docx",
        "number_prefix": "ВЕД",
    },
    {
        "name": "Инвентаризационная ведомость",
        "code": "ledger_inventory",
        "template_filename": "statement.docx",
        "number_prefix": "ИНВ",
    },
    {
        "name": "Список оборудования сотрудника",
        "code": "list_employee",
        "template_filename": "statement.docx",
        "number_prefix": "СПС",
    },
    {
        "name": "Список оборудования кабинета",
        "code": "list_location",
        "template_filename": "statement.docx",
        "number_prefix": "СПК",
    },
    {
        "name": "Список оборудования подразделения",
        "code": "list_department",
        "template_filename": "statement.docx",
        "number_prefix": "СПП",
    },
    {
        "name": "Карточка единицы имущества",
        "code": "card",
        "template_filename": "equipment_card.docx",
        "number_prefix": "КАРТ",
    },
]


def seed_document_types(apps, schema_editor):
    DocumentType = apps.get_model("documents", "DocumentType")
    for entry in DOCUMENT_TYPES:
        DocumentType.objects.update_or_create(code=entry["code"], defaults=entry)


def remove_document_types(apps, schema_editor):
    DocumentType = apps.get_model("documents", "DocumentType")
    codes = [entry["code"] for entry in DOCUMENT_TYPES]
    DocumentType.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_document_types, remove_document_types),
    ]
