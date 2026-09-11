from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.forms import AccountingPeriodForm
from core.models import AccountingPeriod
from core.permissions import accountant_admin_required
from payroll.services import audit_deletion


@login_required
def home(request):
    latest_periods = AccountingPeriod.objects.order_by("-year", "-month")[:6]
    return render(request, "core/home.html", {"latest_periods": latest_periods})


@login_required
def period_list(request):
    periods = AccountingPeriod.objects.order_by("-year", "-month")
    return render(request, "core/period_list.html", {"periods": periods})


@accountant_admin_required
def period_create(request):
    if request.method == "POST":
        form = AccountingPeriodForm(request.POST)
        if form.is_valid():
            period = form.save()
            messages.success(request, f"Период {period} создан.")
            return redirect("period_list")
    else:
        form = AccountingPeriodForm()

    return render(request, "core/period_form.html", {"form": form})


@accountant_admin_required
def period_close(request, pk):
    period = get_object_or_404(AccountingPeriod, pk=pk)
    if request.method == "POST":
        period.close()
        messages.success(request, f"Период {period} закрыт.")
    return redirect("period_list")


@accountant_admin_required
def period_reopen(request, pk):
    period = get_object_or_404(AccountingPeriod, pk=pk)
    if request.method == "POST":
        period.reopen()
        messages.success(request, f"Период {period} открыт.")
    return redirect("period_list")


@accountant_admin_required
def period_delete(request):
    if request.method != "POST":
        return redirect("period_list")

    delete_all = request.POST.get("delete_all") == "1"
    selected_ids = request.POST.getlist("period_ids")
    periods = AccountingPeriod.objects.all().order_by("-year", "-month") if delete_all else AccountingPeriod.objects.filter(
        pk__in=selected_ids
    ).order_by("-year", "-month")

    if request.POST.get("confirm") == "1":
        count = 0
        for period in periods:
            object_id = period.pk
            object_repr = str(period)
            audit_deletion(
                "AccountingPeriod",
                object_id,
                object_repr,
                f"удалил период {object_repr}; вместе с ним удалены связанные ставки, табель, начисления и выплаты",
                request.user,
            )
            period.delete()
            count += 1
        messages.success(request, f"Удалено периодов: {count}.")
        return redirect("period_list")

    if not periods.exists():
        messages.warning(request, "Выберите хотя бы один период для удаления.")
        return redirect("period_list")

    return render(
        request,
        "core/period_confirm_delete.html",
        {"periods": periods, "delete_all": delete_all},
    )
