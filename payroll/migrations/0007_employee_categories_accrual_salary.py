from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


ITR_POSITIONS = {
    "Директор коммерческий",
    "Инженер",
    "Инженер ПТО",
    "Инженер по электромонтажу",
    "Ведущий инженер ПТО",
    "Координатор проекта",
    "Мастер",
    "Менеджер складского хозяйства",
    "Производитель работ",
    "Руководитель проекта",
}


def update_employee_categories(apps, schema_editor):
    Employee = apps.get_model("payroll", "Employee")
    for employee in Employee.objects.all().iterator():
        organization = (employee.organization or "").strip().casefold().replace("ё", "е")
        if organization.startswith("ип"):
            employee.organization = "ИП"
        elif organization == "сз" or "самозанят" in organization:
            employee.organization = "СЗ"
        elif "подряд" in organization:
            employee.organization = "Подрядчик"
        else:
            employee.organization = "СПЕКТРУМ-С"
        employee.employment_type = "itr" if employee.position.strip() in ITR_POSITIONS else "worker"
        employee.save(update_fields=["organization", "employment_type"])


class Migration(migrations.Migration):
    dependencies = [("payroll", "0006_alter_employeerate_options_and_more")]

    operations = [
        migrations.AddField(
            model_name="accrualrecord",
            name="salary",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                max_digits=12,
                validators=[MinValueValidator(Decimal("0"))],
                verbose_name="оклад",
            ),
        ),
        migrations.RunPython(update_employee_categories, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="employee",
            name="employment_type",
            field=models.CharField(
                choices=[("itr", "ИТР"), ("worker", "Рабочий персонал")],
                default="worker",
                max_length=20,
                verbose_name="тип",
            ),
        ),
        migrations.AlterField(
            model_name="employee",
            name="organization",
            field=models.CharField(
                choices=[
                    ("Подрядчик", "Подрядчик"),
                    ("СЗ", "СЗ"),
                    ("ИП", "ИП"),
                    ("СПЕКТРУМ-С", "СПЕКТРУМ-С"),
                ],
                default="СПЕКТРУМ-С",
                max_length=120,
                verbose_name="организация",
            ),
        ),
        migrations.AlterModelOptions(
            name="employee",
            options={
                "ordering": ("normalized_full_name", "id"),
                "verbose_name": "сотрудник",
                "verbose_name_plural": "сотрудники",
            },
        ),
    ]
