from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db.models import Q

from core.models import AccountingPeriod
from payroll.models import AccrualRecord, Employee, EmployeeRate, Payment, normalize_person_name


MAX_EXCEL_UPLOAD_SIZE = 5 * 1024 * 1024
excel_file_validator = FileExtensionValidator(allowed_extensions=("xlsx",))


def validate_excel_upload_size(uploaded_file):
    if uploaded_file.size > MAX_EXCEL_UPLOAD_SIZE:
        raise ValidationError("Размер файла не должен превышать 5 МБ.")


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = (
            "full_name",
            "organization",
            "project",
            "position",
            "employment_type",
            "status",
        )


class EmployeeRateForm(forms.ModelForm):
    class Meta:
        model = EmployeeRate
        fields = ("hourly_rate", "daily_rate")


class RateImportUploadForm(forms.Form):
    file = forms.FileField(
        label="Файл ставок .xlsx",
        validators=(excel_file_validator, validate_excel_upload_size),
    )


class TimesheetImportUploadForm(forms.Form):
    period = forms.ModelChoiceField(
        label="Период",
        queryset=AccountingPeriod.objects.none(),
    )
    file = forms.FileField(
        label="Файл табеля .xlsx",
        validators=(excel_file_validator, validate_excel_upload_size),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["period"].queryset = AccountingPeriod.objects.filter(
            status=AccountingPeriod.Status.OPEN,
            is_archived=False,
        ).order_by("-year", "-month")


class AccrualRecordForm(forms.ModelForm):
    class Meta:
        model = AccrualRecord
        fields = (
            "salary",
            "premium",
            "ktu",
            "salary_1c",
            "daily_allowance_1c",
            "previous_plus",
            "previous_minus",
        )

    def __init__(self, *args, user, period, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.period = period

        if not user.is_accountant_admin:
            allowed = {"premium", "ktu"}
            for field_name in list(self.fields):
                if field_name not in allowed:
                    self.fields.pop(field_name)

        if not period.can_edit:
            for field in self.fields.values():
                field.disabled = True


class PaymentForm(forms.ModelForm):
    employee = forms.CharField(
        label="Сотрудник",
        widget=forms.TextInput(
            attrs={
                "list": "employee-options",
                "autocomplete": "off",
                "placeholder": "Начните вводить ФИО",
            }
        ),
    )

    class Meta:
        model = Payment
        fields = ("employee", "period", "amount", "paid_at", "comment")
        widgets = {
            "paid_at": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        employee_filter = Q(status=Employee.Status.ACTIVE)
        if self.instance and self.instance.pk:
            employee_filter |= Q(pk=self.instance.employee_id)
        self.employee_choices = list(
            Employee.objects.filter(employee_filter).order_by("normalized_full_name", "id")
        )
        self.employee_options = [self.employee_option(employee) for employee in self.employee_choices]

        if not self.is_bound:
            selected_employee = self.instance.employee if self.instance and self.instance.pk else None
            if selected_employee is None and self.initial.get("employee"):
                selected_employee = Employee.objects.filter(pk=self.initial["employee"]).first()
            if selected_employee:
                self.initial["employee"] = self.employee_option(selected_employee)

        self.fields["period"].queryset = AccountingPeriod.objects.filter(
            status=AccountingPeriod.Status.OPEN,
            is_archived=False,
        ).order_by("-year", "-month")
        if self.instance and self.instance.pk:
            self.fields["period"].queryset = (
                AccountingPeriod.objects.filter(pk=self.instance.period_id)
                | self.fields["period"].queryset
            ).order_by("-year", "-month")

    @staticmethod
    def employee_option(employee):
        return f"{employee.personnel_number} — {employee.full_name}"

    def clean_employee(self):
        value = self.cleaned_data["employee"].strip()
        by_option = {self.employee_option(employee): employee for employee in self.employee_choices}
        if value in by_option:
            return by_option[value]

        normalized = normalize_person_name(value)
        matches = [employee for employee in self.employee_choices if employee.normalized_full_name == normalized]
        if len(matches) == 1:
            return matches[0]
        raise ValidationError("Выберите сотрудника из выпадающего списка.")
