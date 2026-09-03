from django.db import models
from employees.models import Employee, Location
from equipment.models import Equipment


class MovementEventType(models.TextChoices):
    TRANSFER = "transfer", "Передача сотруднику"
    MOVE = "move", "Перемещение (смена местонахождения)"
    REPAIR = "repair", "Отправка в ремонт"
    RETURN_FROM_REPAIR = "return_repair", "Возврат из ремонта"
    STATUS_CHANGE = "status_change", "Изменение статуса"
    WRITE_OFF = "write_off", "Списание"
    RECEIPT = "receipt", "Поступление (первичная постановка на учёт)"
    RETURN = "return", "Возврат оборудования (сдан обратно)"
    ASSEMBLY = "assembly", "Включение в сборку (акт сборки)"


class MovementHistory(models.Model):
    """
    Неизменяемый журнал всех событий по единице оборудования.
    Записи никогда не редактируются и не удаляются — это история эксплуатации.
    """
    equipment = models.ForeignKey(
        Equipment, verbose_name="Оборудование",
        on_delete=models.CASCADE, related_name="movement_events",
    )
    event_type = models.CharField(
        "Тип события", max_length=20, choices=MovementEventType.choices,
    )
    from_employee = models.ForeignKey(
        Employee, verbose_name="От сотрудника",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="movements_from",
    )
    to_employee = models.ForeignKey(
        Employee, verbose_name="Кому передано",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="movements_to",
    )
    from_location = models.ForeignKey(
        Location, verbose_name="Откуда",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="movements_from",
    )
    to_location = models.ForeignKey(
        Location, verbose_name="Куда",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="movements_to",
    )
    # Ссылка на документ (акт) добавится на этапе 3, когда появится модуль documents.
    document = models.ForeignKey(
        "documents.Document", verbose_name="Документ-основание",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="movement_events",
    )
    event_date = models.DateTimeField("Дата события", auto_now_add=True)
    comment = models.TextField("Комментарий", blank=True)

    class Meta:
        verbose_name = "Событие истории"
        verbose_name_plural = "История перемещений"
        ordering = ["-event_date"]

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.equipment} ({self.event_date:%d.%m.%Y})"
