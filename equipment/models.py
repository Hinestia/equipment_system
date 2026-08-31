from django.db import models
from employees.models import Employee, Location


class EquipmentCategory(models.Model):
    """Справочник категорий оборудования (ПК, монитор, ПЛК и т.д.)."""
    name = models.CharField("Название", max_length=255, unique=True)

    class Meta:
        verbose_name = "Категория оборудования"
        verbose_name_plural = "Категории оборудования"
        ordering = ["name"]

    def __str__(self):
        return self.name


class EquipmentStatus(models.Model):
    """Справочник статусов (в эксплуатации, на складе, в ремонте, списано...)."""
    name = models.CharField("Название", max_length=100, unique=True)

    class Meta:
        verbose_name = "Статус оборудования"
        verbose_name_plural = "Статусы оборудования"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Equipment(models.Model):
    """Центральная таблица реестра оборудования — хранит текущее состояние."""
    inventory_number = models.CharField("Инвентарный номер", max_length=100, unique=True)
    serial_number = models.CharField("Серийный номер", max_length=100, blank=True)
    name = models.CharField("Наименование", max_length=255)
    model = models.CharField("Модель", max_length=255, blank=True)
    category = models.ForeignKey(
        EquipmentCategory, verbose_name="Категория",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="equipment_items",
    )
    specifications = models.TextField("Технические характеристики", blank=True)
    purchase_date = models.DateField("Дата поступления", null=True, blank=True)
    purchase_cost = models.DecimalField(
        "Балансовая стоимость", max_digits=12, decimal_places=2,
        null=True, blank=True,
    )
    status = models.ForeignKey(
        EquipmentStatus, verbose_name="Статус",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="equipment_items",
    )
    current_location = models.ForeignKey(
        Location, verbose_name="Текущее местонахождение",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="equipment_items",
    )
    responsible_employee = models.ForeignKey(
        Employee, verbose_name="Ответственное лицо",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="equipment_items",
    )
    workstation = models.ForeignKey(
        "workstations.Workstation", verbose_name="Сборка (рабочее место / ПК)",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="equipment_items",
        help_text="Если единица входит в сборку — рабочее место или ПК из нескольких компонентов",
    )
    notes = models.TextField("Примечания", blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Оборудование"
        verbose_name_plural = "Оборудование"
        ordering = ["inventory_number"]

    def __str__(self):
        return f"{self.inventory_number} — {self.name}"
