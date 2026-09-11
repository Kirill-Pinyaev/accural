from django.core.exceptions import ValidationError
from django.db import models


class AccountingPeriod(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Открыт"
        CLOSED = "closed", "Закрыт"

    MONTH_CHOICES = (
        (1, "Январь"),
        (2, "Февраль"),
        (3, "Март"),
        (4, "Апрель"),
        (5, "Май"),
        (6, "Июнь"),
        (7, "Июль"),
        (8, "Август"),
        (9, "Сентябрь"),
        (10, "Октябрь"),
        (11, "Ноябрь"),
        (12, "Декабрь"),
    )

    year = models.PositiveSmallIntegerField("год")
    month = models.PositiveSmallIntegerField("месяц", choices=MONTH_CHOICES)
    status = models.CharField(
        "статус",
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    is_archived = models.BooleanField("архив", default=False)
    created_at = models.DateTimeField("создан", auto_now_add=True)
    updated_at = models.DateTimeField("изменен", auto_now=True)

    class Meta:
        verbose_name = "расчетный период"
        verbose_name_plural = "расчетные периоды"
        ordering = ("-year", "-month")
        constraints = [
            models.UniqueConstraint(fields=("year", "month"), name="unique_accounting_period")
        ]

    def __str__(self):
        return f"{self.get_month_display()} {self.year}"

    @property
    def is_open(self):
        return self.status == self.Status.OPEN

    @property
    def is_closed(self):
        return self.status == self.Status.CLOSED

    @property
    def can_edit(self):
        return self.is_open and not self.is_archived

    def clean(self):
        if self.month < 1 or self.month > 12:
            raise ValidationError({"month": "Месяц должен быть от 1 до 12."})
        if self.year < 2000 or self.year > 2100:
            raise ValidationError({"year": "Год должен быть в диапазоне 2000-2100."})
        if self.is_archived and self.status != self.Status.CLOSED:
            raise ValidationError("Архивный период должен быть закрыт.")

    def close(self):
        self.status = self.Status.CLOSED
        self.full_clean()
        self.save(update_fields=["status", "updated_at"])

    def reopen(self):
        self.status = self.Status.OPEN
        self.is_archived = False
        self.full_clean()
        self.save(update_fields=["status", "is_archived", "updated_at"])
