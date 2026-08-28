from django.db import models

from employees.models import Employee, Location


class DocumentType(models.Model):
    """
    Справочник типов документов. Поле code используется в коде для сопоставления
    с шаблоном .docx и для генерации номера — не меняйте его без необходимости.
    """
    name = models.CharField("Название", max_length=255, unique=True)
    code = models.SlugField("Код типа", max_length=50, unique=True)
    template_filename = models.CharField(
        "Файл шаблона", max_length=255, blank=True,
        help_text="Имя файла .docx в папке documents/doc_templates/",
    )
    number_prefix = models.CharField(
        "Префикс номера", max_length=10, blank=True,
        help_text="Например 'АПП' для акта приёма-передачи",
    )

    class Meta:
        verbose_name = "Тип документа"
        verbose_name_plural = "Типы документов"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Document(models.Model):
    """
    Сформированный документ (акт). Хранит все данные, нужные для печатной формы,
    и ссылку на сгенерированный файл .docx.
    """
    document_type = models.ForeignKey(
        DocumentType, verbose_name="Тип документа",
        on_delete=models.PROTECT, related_name="documents",
    )
    number = models.CharField("Номер", max_length=50, blank=True)
    date_created = models.DateTimeField("Дата создания", auto_now_add=True)

    from_employee = models.ForeignKey(
        Employee, verbose_name="Передал (сотрудник)",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="documents_from",
    )
    to_employee = models.ForeignKey(
        Employee, verbose_name="Принял (сотрудник)",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="documents_to",
    )
    from_location = models.ForeignKey(
        Location, verbose_name="Откуда",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="documents_from",
    )
    to_location = models.ForeignKey(
        Location, verbose_name="Куда",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="documents_to",
    )
    reason = models.TextField(
        "Причина/основание", blank=True,
        help_text="Используется для актов списания и возврата (состояние, причина списания и т.д.)",
    )
    comment = models.TextField("Комментарий", blank=True)
    generated_file = models.FileField(
        "Сгенерированный файл", upload_to="documents/", blank=True, null=True,
    )

    class Meta:
        verbose_name = "Документ"
        verbose_name_plural = "Документы"
        ordering = ["-date_created"]

    def __str__(self):
        return f"{self.document_type} №{self.number or self.pk}"


class DocumentEquipment(models.Model):
    """Состав оборудования, включённого в документ (один акт — несколько единиц техники)."""
    document = models.ForeignKey(
        Document, verbose_name="Документ",
        on_delete=models.CASCADE, related_name="items",
    )
    equipment = models.ForeignKey(
        "equipment.Equipment", verbose_name="Оборудование",
        on_delete=models.PROTECT, related_name="document_entries",
    )
    quantity = models.PositiveIntegerField("Количество", default=1)
    notes = models.CharField("Примечание", max_length=255, blank=True)

    class Meta:
        verbose_name = "Позиция документа"
        verbose_name_plural = "Позиции документа"

    def __str__(self):
        return f"{self.equipment} — {self.document}"
