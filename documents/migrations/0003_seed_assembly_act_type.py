from django.db import migrations

DOCUMENT_TYPE = {
    "name": "Акт формирования сборки",
    "code": "act_assembly",
    "template_filename": "assembly_act.docx",
    "number_prefix": "АФС",
}


def seed_assembly_act_type(apps, schema_editor):
    DocumentType = apps.get_model("documents", "DocumentType")
    DocumentType.objects.update_or_create(code=DOCUMENT_TYPE["code"], defaults=DOCUMENT_TYPE)


def remove_assembly_act_type(apps, schema_editor):
    DocumentType = apps.get_model("documents", "DocumentType")
    DocumentType.objects.filter(code=DOCUMENT_TYPE["code"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0002_seed_document_types"),
    ]

    operations = [
        migrations.RunPython(seed_assembly_act_type, remove_assembly_act_type),
    ]
