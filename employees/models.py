from django.db import models


class Department(models.Model):
    """Подразделение (может иметь вложенные под-отделы)."""
    name = models.CharField("Название", max_length=255)
    code = models.CharField("Код", max_length=50, blank=True)
    parent_department = models.ForeignKey(
        "self", verbose_name="Родительское подразделение",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="sub_departments",
    )

    class Meta:
        verbose_name = "Подразделение"
        verbose_name_plural = "Подразделения"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Location(models.Model):
    """Кабинет / помещение / склад."""
    name = models.CharField("Название", max_length=255)
    department = models.ForeignKey(
        Department, verbose_name="Подразделение",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="locations",
    )
    building = models.CharField("Здание", max_length=100, blank=True)
    floor = models.CharField("Этаж", max_length=20, blank=True)

    class Meta:
        verbose_name = "Местонахождение"
        verbose_name_plural = "Местонахождения"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Employee(models.Model):
    """Сотрудник, в т.ч. потенциально материально ответственное лицо."""
    full_name = models.CharField("ФИО", max_length=255)
    position = models.CharField("Должность", max_length=255, blank=True)
    department = models.ForeignKey(
        Department, verbose_name="Подразделение",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="employees",
    )
    phone = models.CharField("Телефон", max_length=50, blank=True)
    email = models.EmailField("Email", blank=True)
    is_mol = models.BooleanField("Материально ответственное лицо", default=False)
    is_active = models.BooleanField("Активен", default=True)
    hire_date = models.DateField("Дата приёма", null=True, blank=True)

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name
