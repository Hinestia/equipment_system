from django.db import models


class Workstation(models.Model):
    """
    Сборка — рабочее место или ПК, объединяющее несколько единиц оборудования
    (системный блок, монитор, клавиатура и т.д.) в один логический комплект.
    Само оборудование при этом остаётся в общем реестре — сборка лишь
    группирует его для удобства учёта и передачи целиком.
    """
    name = models.CharField("Название", max_length=255, help_text="Например: «АРМ инженера Иванова» или «ПК №5»")
    location = models.ForeignKey(
        "employees.Location", verbose_name="Местонахождение",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="workstations",
    )
    responsible_employee = models.ForeignKey(
        "employees.Employee", verbose_name="Ответственное лицо",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="workstations",
    )
    notes = models.TextField("Примечания", blank=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)

    class Meta:
        verbose_name = "Сборка (рабочее место / ПК)"
        verbose_name_plural = "Сборки (рабочие места / ПК)"
        ordering = ["name"]

    def __str__(self):
        return self.name
