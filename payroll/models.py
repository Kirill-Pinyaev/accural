from decimal import Decimal

from django.core.validators import MinValueValidator
from django.conf import settings
from django.db import models, transaction

from core.models import AccountingPeriod


def normalize_person_name(value):
    return " ".join((value or "").strip().lower().replace("ё", "е").split())


class Employee(models.Model):
    class EmploymentType(models.TextChoices):
        ITR = "itr", "ИТР"
        WORKER = "worker", "Рабочий персонал"

    class Organization(models.TextChoices):
        CONTRACTOR = "Подрядчик", "Подрядчик"
        SELF_EMPLOYED = "СЗ", "СЗ"
        INDIVIDUAL = "ИП", "ИП"
        SPECTRUM = "СПЕКТРУМ-С", "СПЕКТРУМ-С"

    class Status(models.TextChoices):
        ACTIVE = "active", "Активен"
        ARCHIVED = "archived", "Архив"

    personnel_number = models.CharField("табельный номер", max_length=6, unique=True, blank=True)
    full_name = models.CharField("ФИО", max_length=255)
    normalized_full_name = models.CharField("ФИО для поиска", max_length=255, db_index=True, editable=False)
    organization = models.CharField(
        "организация",
        max_length=120,
        choices=Organization.choices,
        default=Organization.SPECTRUM,
    )
    project = models.CharField("проект", max_length=255, blank=True)
    position = models.CharField("должность / категория", max_length=255, blank=True)
    employment_type = models.CharField(
        "тип",
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.WORKER,
    )
    status = models.CharField(
        "статус",
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField("создан", auto_now_add=True)
    updated_at = models.DateTimeField("изменен", auto_now=True)

    class Meta:
        verbose_name = "сотрудник"
        verbose_name_plural = "сотрудники"
        ordering = ("normalized_full_name", "id")

    def __str__(self):
        return f"{self.personnel_number} - {self.full_name}"

    def save(self, *args, **kwargs):
        self.normalized_full_name = normalize_person_name(self.full_name)
        if not self.personnel_number:
            self.personnel_number = self.next_personnel_number()
        super().save(*args, **kwargs)

    @classmethod
    def next_personnel_number(cls):
        with transaction.atomic():
            last = (
                cls.objects.select_for_update()
                .exclude(personnel_number="")
                .order_by("-personnel_number")
                .first()
            )
            next_number = int(last.personnel_number) + 1 if last else 1
            return f"{next_number:06d}"


class EmployeeAlias(models.Model):
    employee = models.ForeignKey(
        Employee,
        verbose_name="сотрудник",
        related_name="aliases",
        on_delete=models.CASCADE,
    )
    source_name = models.CharField("ФИО из файла", max_length=255)
    normalized_source_name = models.CharField("ФИО из файла для поиска", max_length=255, db_index=True)
    source = models.CharField("источник", max_length=100, blank=True)
    created_at = models.DateTimeField("создан", auto_now_add=True)

    class Meta:
        verbose_name = "алиас сотрудника"
        verbose_name_plural = "алиасы сотрудников"
        constraints = [
            models.UniqueConstraint(
                fields=("normalized_source_name", "source"),
                name="unique_employee_alias_per_source",
            )
        ]

    def __str__(self):
        return f"{self.source_name} -> {self.employee}"

    def save(self, *args, **kwargs):
        self.normalized_source_name = normalize_person_name(self.source_name)
        super().save(*args, **kwargs)


class EmployeeRate(models.Model):
    employee = models.ForeignKey(
        Employee,
        verbose_name="сотрудник",
        related_name="rates",
        on_delete=models.CASCADE,
    )
    hourly_rate = models.DecimalField(
        "ставка за час",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    daily_rate = models.DecimalField(
        "ставка за день",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    updated_at = models.DateTimeField("изменена", auto_now=True)

    class Meta:
        verbose_name = "ставка сотрудника"
        verbose_name_plural = "ставки сотрудников"
        ordering = ("employee__full_name",)
        constraints = [
            models.UniqueConstraint(fields=("employee",), name="unique_employee_rate")
        ]

    def __str__(self):
        return f"{self.employee}"


class TimesheetEntry(models.Model):
    employee = models.ForeignKey(
        Employee,
        verbose_name="сотрудник",
        related_name="timesheet_entries",
        on_delete=models.CASCADE,
    )
    period = models.ForeignKey(
        AccountingPeriod,
        verbose_name="период",
        related_name="timesheet_entries",
        on_delete=models.CASCADE,
    )
    days = models.PositiveSmallIntegerField("дни", default=0)
    hours = models.DecimalField(
        "часы",
        max_digits=8,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    daily_hours = models.JSONField("часы по дням", default=dict, blank=True)
    source_name = models.CharField("ФИО из табеля", max_length=255, blank=True)
    updated_at = models.DateTimeField("изменен", auto_now=True)

    class Meta:
        verbose_name = "строка табеля"
        verbose_name_plural = "табель"
        ordering = ("period", "employee__full_name")
        constraints = [
            models.UniqueConstraint(fields=("employee", "period"), name="unique_timesheet_entry_period")
        ]

    def __str__(self):
        return f"{self.employee} / {self.period}: {self.days} дн., {self.hours} ч."


class AccrualRecord(models.Model):
    employee = models.ForeignKey(
        Employee,
        verbose_name="сотрудник",
        related_name="accrual_records",
        on_delete=models.CASCADE,
    )
    period = models.ForeignKey(
        AccountingPeriod,
        verbose_name="период",
        related_name="accrual_records",
        on_delete=models.CASCADE,
    )
    premium = models.DecimalField(
        "премия",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    ktu = models.DecimalField(
        "КТУ",
        max_digits=6,
        decimal_places=3,
        default=Decimal("1"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    salary = models.DecimalField(
        "оклад",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    salary_1c = models.DecimalField(
        "ЗП 1С",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    daily_allowance_1c = models.DecimalField(
        "суточные 1С",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    previous_plus = models.DecimalField(
        "плюс за пред. месяц",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    previous_minus = models.DecimalField(
        "минус за пред. месяц",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    previous_balance_manual_override = models.BooleanField(
        "ручная корректировка переноса",
        default=False,
    )
    updated_at = models.DateTimeField("изменен", auto_now=True)

    class Meta:
        verbose_name = "начисление"
        verbose_name_plural = "начисления"
        ordering = ("period", "employee__full_name")
        constraints = [
            models.UniqueConstraint(fields=("employee", "period"), name="unique_accrual_record_period")
        ]

    def __str__(self):
        return f"{self.employee} / {self.period}"


class Payment(models.Model):
    employee = models.ForeignKey(
        Employee,
        verbose_name="сотрудник",
        related_name="payments",
        on_delete=models.CASCADE,
    )
    period = models.ForeignKey(
        AccountingPeriod,
        verbose_name="период",
        related_name="payments",
        on_delete=models.CASCADE,
    )
    amount = models.DecimalField(
        "сумма",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    paid_at = models.DateField("дата выплаты")
    initiator = models.CharField("инициатор", max_length=255)
    comment = models.TextField("комментарий", blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="автор изменения",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField("создана", auto_now_add=True)
    updated_at = models.DateTimeField("изменена", auto_now=True)

    class Meta:
        verbose_name = "выплата"
        verbose_name_plural = "выплаты"
        ordering = ("-paid_at", "employee__full_name")

    def __str__(self):
        return f"{self.employee} / {self.period}: {self.amount}"


class AuditLog(models.Model):
    object_type = models.CharField("объект", max_length=100)
    object_id = models.PositiveBigIntegerField("ID объекта", null=True, blank=True)
    object_repr = models.CharField("представление", max_length=255, blank=True)
    field_name = models.CharField("поле", max_length=100)
    old_value = models.TextField("старое значение", blank=True)
    new_value = models.TextField("новое значение", blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="автор",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField("дата и время", auto_now_add=True)

    class Meta:
        verbose_name = "запись журнала"
        verbose_name_plural = "журнал изменений"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.created_at:%d.%m.%Y %H:%M} {self.object_type}.{self.field_name}"
