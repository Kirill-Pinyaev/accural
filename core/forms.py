from django import forms

from core.models import AccountingPeriod


class AccountingPeriodForm(forms.ModelForm):
    class Meta:
        model = AccountingPeriod
        fields = ("year", "month", "status", "is_archived")
        widgets = {
            "year": forms.NumberInput(attrs={"min": 2000, "max": 2100}),
        }
