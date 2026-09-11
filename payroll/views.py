from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Prefetch
from django.db.models.functions import ExtractYear
from django.utils import timezone

from core.models import AccountingPeriod
from core.permissions import accountant_admin_required
from core.security import safe_next_url
from payroll.forms import (
    AccrualRecordForm,
    EmployeeForm,
    EmployeeRateForm,
    PaymentForm,
    RateImportUploadForm,
    TimesheetImportUploadForm,
)
from payroll.exports import export_accrual_workbook, export_payments_workbook, workbook_response
from payroll.models import AccrualRecord, AuditLog, Employee, EmployeeRate, Payment, TimesheetEntry
from payroll.services import (
    audit_deletion,
    audit_event,
    audit_form_changes,
    apply_rates_import,
    apply_timesheet_import,
    build_accrual_rows,
    calculate_accrual_totals,
    filter_accrual_rows,
    payment_created_message,
    payment_updated_message,
    parse_rates_upload,
    parse_timesheet_upload,
    sync_previous_balances,
)


def account_initiator(user):
    return user.get_username()


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


def parse_int_choice(value, allowed_values, default):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed in allowed_values else default


def audit_log_message(log):
    author = log.author or "Пользователь"
    if log.field_name == "event":
        return f"{author} {log.new_value}"
    old_value = log.old_value or "-"
    new_value = log.new_value or "-"
    return (
        f'{author} изменил поле "{log.field_name}" у "{log.object_repr}": '
        f'было "{old_value}", стало "{new_value}"'
    )


def audit_log_txt_response(logs, year, month):
    month_name = dict(MONTH_CHOICES)[month]
    lines = [f"Журнал изменений за {month_name} {year}", ""]
    for log in logs:
        created_at = timezone.localtime(log.created_at).strftime("%d.%m.%Y %H:%M")
        author = log.author or "-"
        lines.append(f"{created_at}; {audit_log_message(log)}; автор: {author}")
    if len(lines) == 2:
        lines.append("Записей нет.")

    response = HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="journal_{year}_{month:02d}.txt"'
    return response


@login_required
def employee_list(request):
    periods = AccountingPeriod.objects.order_by("-year", "-month")
    period_id = request.GET.get("period")

    if period_id:
        selected_period = get_object_or_404(AccountingPeriod, pk=period_id)
    else:
        selected_period = periods.first()

    employees = (
        Employee.objects.prefetch_related(
            Prefetch("rates", queryset=EmployeeRate.objects.all(), to_attr="current_rates")
        )
        .order_by("normalized_full_name", "id")
    )
    return render(
        request,
        "payroll/employee_list.html",
        {"employees": employees, "periods": periods, "selected_period": selected_period},
    )


@accountant_admin_required
def employee_create(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST)
        if form.is_valid():
            employee = form.save()
            messages.success(request, f"Сотрудник {employee} создан.")
            return redirect("employee_list")
    else:
        form = EmployeeForm()
    return render(request, "payroll/employee_form.html", {"form": form, "title": "Новый сотрудник"})


@accountant_admin_required
def employee_update(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, f"Сотрудник {employee} обновлен.")
            return redirect("employee_list")
    else:
        form = EmployeeForm(instance=employee)
    return render(request, "payroll/employee_form.html", {"form": form, "title": employee})


@accountant_admin_required
def employee_delete(request):
    if request.method != "POST":
        return redirect("employee_list")

    delete_all = request.POST.get("delete_all") == "1"
    period_id = request.POST.get("period")
    period = get_object_or_404(AccountingPeriod, pk=period_id) if period_id else None
    if period is None:
        messages.warning(request, "Выберите период, из которого нужно удалить сотрудников.")
        return redirect("employee_list")

    selected_ids = request.POST.getlist("employee_ids")
    employees = Employee.objects.all().order_by("full_name") if delete_all else Employee.objects.filter(
        pk__in=selected_ids
    ).order_by("full_name")

    if request.POST.get("confirm") == "1":
        count = 0
        for employee in employees:
            deleted = (
                TimesheetEntry.objects.filter(employee=employee, period=period).delete()[0]
                + AccrualRecord.objects.filter(employee=employee, period=period).delete()[0]
                + Payment.objects.filter(employee=employee, period=period).delete()[0]
            )
            if deleted == 0:
                continue
            object_repr = f"{employee} / {period}"
            audit_deletion(
                "EmployeePeriodData",
                employee.pk,
                object_repr,
                f"удалил данные сотрудника {employee.full_name} из периода {period}; сотрудник и ставки сохранены",
                request.user,
            )
            count += 1
        messages.success(request, f"Удалено из периода {period}: {count} сотрудников.")
        return redirect(safe_next_url(request, request.POST.get("next")) or "employee_list")

    if not employees.exists():
        messages.warning(request, "Выберите хотя бы одного сотрудника для удаления.")
        return redirect("employee_list")

    return render(
        request,
        "payroll/employee_confirm_delete.html",
        {
            "employees": employees,
            "delete_all": delete_all,
            "period": period,
            "next_url": safe_next_url(request, request.POST.get("next")),
        },
    )


@accountant_admin_required
def rate_edit(request, employee_id):
    employee = get_object_or_404(Employee, pk=employee_id)
    rate, _ = EmployeeRate.objects.get_or_create(employee=employee)

    if request.method == "POST":
        form = EmployeeRateForm(request.POST, instance=rate)
        if form.is_valid():
            form.save()
            messages.success(request, f"Ставки для {employee.full_name} обновлены.")
            return redirect("employee_list")
    else:
        form = EmployeeRateForm(instance=rate)

    return render(
        request,
        "payroll/rate_form.html",
        {"employee": employee, "form": form},
    )


@accountant_admin_required
def rate_import_upload(request):
    if request.method == "POST":
        form = RateImportUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                rows = parse_rates_upload(form.cleaned_data["file"])
            except ValueError as exc:
                form.add_error("file", str(exc))
            else:
                request.session["rate_import"] = {
                    "rows": [row.as_dict() for row in rows],
                }
                return redirect("rate_import_preview")
    else:
        form = RateImportUploadForm()

    return render(request, "payroll/rate_import_upload.html", {"form": form})


@accountant_admin_required
def rate_import_preview(request):
    payload = request.session.get("rate_import")
    if not payload:
        messages.warning(request, "Сначала загрузите файл ставок.")
        return redirect("rate_import_upload")

    rows = payload["rows"]
    total_errors = sum(1 for row in rows if row["errors"])

    return render(
        request,
        "payroll/rate_import_preview.html",
        {"rows": rows, "total_errors": total_errors},
    )


@accountant_admin_required
def rate_import_apply(request):
    payload = request.session.get("rate_import")
    if not payload:
        messages.warning(request, "Нет подготовленного импорта.")
        return redirect("rate_import_upload")

    if request.method == "POST":
        result = apply_rates_import(payload["rows"])
        request.session.pop("rate_import", None)
        messages.success(
            request,
            "Импорт ставок применен: "
            f"создано сотрудников {result['created']}, "
            f"обновлено сотрудников {result['updated']}, "
            f"обновлено ставок {result['rates_updated']}.",
        )
        return redirect("employee_list")

    return redirect("rate_import_preview")


@login_required
def timesheet_entry_list(request):
    periods = AccountingPeriod.objects.order_by("-year", "-month")
    period_id = request.GET.get("period")
    selected_period = get_object_or_404(AccountingPeriod, pk=period_id) if period_id else periods.first()
    entries = TimesheetEntry.objects.none()

    if selected_period:
        entries = (
            TimesheetEntry.objects.select_related("employee", "period")
            .filter(period=selected_period)
            .order_by("employee__full_name")
        )

    return render(
        request,
        "payroll/timesheet_entry_list.html",
        {"periods": periods, "selected_period": selected_period, "entries": entries},
    )


@accountant_admin_required
def timesheet_import_upload(request):
    if request.method == "POST":
        form = TimesheetImportUploadForm(request.POST, request.FILES)
        if form.is_valid():
            period = form.cleaned_data["period"]
            try:
                rows = parse_timesheet_upload(form.cleaned_data["file"], period)
            except ValueError as exc:
                form.add_error("file", str(exc))
            else:
                request.session["timesheet_import"] = {
                    "period_id": period.id,
                    "rows": [row.as_dict() for row in rows],
                }
                return redirect("timesheet_import_preview")
    else:
        form = TimesheetImportUploadForm()

    return render(request, "payroll/timesheet_import_upload.html", {"form": form})


@accountant_admin_required
def timesheet_import_preview(request):
    payload = request.session.get("timesheet_import")
    if not payload:
        messages.warning(request, "Сначала загрузите файл табеля.")
        return redirect("timesheet_import_upload")

    period = get_object_or_404(AccountingPeriod, pk=payload["period_id"])
    rows = payload["rows"]
    total_errors = sum(1 for row in rows if row["errors"])

    return render(
        request,
        "payroll/timesheet_import_preview.html",
        {"period": period, "rows": rows, "total_errors": total_errors},
    )


@accountant_admin_required
def timesheet_import_apply(request):
    payload = request.session.get("timesheet_import")
    if not payload:
        messages.warning(request, "Нет подготовленного импорта табеля.")
        return redirect("timesheet_import_upload")

    period = get_object_or_404(AccountingPeriod, pk=payload["period_id"])
    if request.method == "POST":
        result = apply_timesheet_import(period, payload["rows"])
        request.session.pop("timesheet_import", None)
        messages.success(
            request,
            "Импорт табеля применен: "
            f"создано сотрудников {result['created_employees']}, "
            f"обновлено строк табеля {result['updated_entries']}.",
        )
        return redirect("timesheet_entry_list")

    return redirect("timesheet_import_preview")


@login_required
def accrual_list(request):
    periods = AccountingPeriod.objects.order_by("-year", "-month")
    period_id = request.GET.get("period")
    selected_period = get_object_or_404(AccountingPeriod, pk=period_id) if period_id else periods.first()
    rows = []
    totals = {}

    if selected_period:
        sync_previous_balances(selected_period)
        rows, totals = build_accrual_rows(selected_period)
        has_accrual_rows = bool(rows)
        show_zero = request.GET.get("show_zero") == "1"
        only_zero = request.GET.get("only_zero") == "1"
        if only_zero:
            position_rows = [row for row in rows if row["is_zero"]]
        elif show_zero:
            position_rows = rows
        else:
            position_rows = [row for row in rows if not row["is_zero"]]
        filter_options = {
            "organizations": sorted({row["employee"].organization for row in rows if row["employee"].organization}),
            "projects": sorted({row["employee"].project for row in rows if row["employee"].project}),
            "positions": sorted(
                {row["employee"].position for row in position_rows if row["employee"].position},
                key=str.casefold,
            ),
            "employment_types": [
                (value, label)
                for value, label in Employee.EmploymentType.choices
                if value in {row["employee"].employment_type for row in rows}
            ],
        }
        filters = {
            "fio": request.GET.get("fio", "").strip(),
            "organization": request.GET.get("organization", ""),
            "project": request.GET.get("project", ""),
            "position": request.GET.get("position", ""),
            "employment_type": request.GET.get("employment_type", ""),
            "show_zero": show_zero,
            "only_zero": only_zero,
        }
        rows = filter_accrual_rows(rows, filters)
        totals = calculate_accrual_totals(rows)
    else:
        filter_options = {"organizations": [], "projects": [], "positions": [], "employment_types": []}
        filters = {
            "fio": "",
            "organization": "",
            "project": "",
            "position": "",
            "employment_type": "",
            "show_zero": False,
            "only_zero": False,
        }
        has_accrual_rows = False

    return render(
        request,
        "payroll/accrual_list.html",
        {
            "periods": periods,
            "selected_period": selected_period,
            "rows": rows,
            "totals": totals,
            "filter_options": filter_options,
            "filters": filters,
            "has_accrual_rows": has_accrual_rows,
        },
    )


@login_required
def accrual_export(request):
    period = get_object_or_404(AccountingPeriod, pk=request.GET.get("period"))
    filters = {
        "fio": request.GET.get("fio", "").strip(),
        "organization": request.GET.get("organization", ""),
        "project": request.GET.get("project", ""),
        "position": request.GET.get("position", ""),
        "employment_type": request.GET.get("employment_type", ""),
        "show_zero": request.GET.get("show_zero") == "1",
        "only_zero": request.GET.get("only_zero") == "1",
    }
    workbook = export_accrual_workbook(period, filters)
    filename = f"accrual_{period.year}_{period.month:02d}.xlsx"
    return workbook_response(workbook, filename)


@login_required
def accrual_edit(request, record_id):
    record = get_object_or_404(
        AccrualRecord.objects.select_related("employee", "period"),
        pk=record_id,
    )
    if request.method == "POST":
        if not record.period.can_edit:
            messages.error(request, "Период закрыт или архивный, редактирование запрещено.")
            return redirect(safe_next_url(request, request.POST.get("next")) or "accrual_list")

        form = AccrualRecordForm(request.POST, instance=record, user=request.user, period=record.period)
        if form.is_valid():
            manual_override = bool({"previous_plus", "previous_minus"} & set(form.changed_data))
            form.save()
            if manual_override and request.user.is_accountant_admin:
                record.previous_balance_manual_override = True
                record.save(update_fields=["previous_balance_manual_override", "updated_at"])
            audit_form_changes(record, form, request.user)
            messages.success(request, f"Начисление для {record.employee.full_name} обновлено.")
            return redirect(safe_next_url(request, request.POST.get("next")) or "accrual_list")
    else:
        form = AccrualRecordForm(instance=record, user=request.user, period=record.period)

    return render(
        request,
        "payroll/accrual_form.html",
        {"form": form, "record": record, "next_url": safe_next_url(request, request.GET.get("next"))},
    )


@login_required
def payment_list(request):
    periods = AccountingPeriod.objects.order_by("-year", "-month")
    period_id = request.GET.get("period")
    selected_period = get_object_or_404(AccountingPeriod, pk=period_id) if period_id else periods.first()
    payments = Payment.objects.none()

    if selected_period:
        payments = (
            Payment.objects.select_related("employee", "period", "updated_by")
            .filter(period=selected_period)
            .order_by("-paid_at", "employee__full_name")
        )

    return render(
        request,
        "payroll/payment_list.html",
        {"periods": periods, "selected_period": selected_period, "payments": payments},
    )


@login_required
def payment_export(request):
    period = get_object_or_404(AccountingPeriod, pk=request.GET.get("period"))
    workbook = export_payments_workbook(period)
    filename = f"payments_{period.year}_{period.month:02d}.xlsx"
    return workbook_response(workbook, filename)


@login_required
def payment_create(request):
    initial = {}
    period_id = request.GET.get("period")
    employee_id = request.GET.get("employee")
    if period_id:
        initial["period"] = period_id
    if employee_id:
        initial["employee"] = employee_id

    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            if not payment.period.can_edit:
                form.add_error(None, "Период закрыт или архивный, редактирование запрещено.")
            else:
                payment.initiator = account_initiator(request.user)
                payment.updated_by = request.user
                payment.save()
                audit_event(payment, payment_created_message(payment), request.user)
                messages.success(request, "Выплата создана.")
                return redirect(safe_next_url(request, request.POST.get("next")) or "payment_list")
    else:
        form = PaymentForm(initial=initial)

    return render(
        request,
        "payroll/payment_form.html",
        {"form": form, "title": "Новая выплата", "next_url": safe_next_url(request, request.GET.get("next"))},
    )


@login_required
def payment_update(request, pk):
    payment = get_object_or_404(
        Payment.objects.select_related("employee", "period", "updated_by"),
        pk=pk,
    )
    if request.method == "POST":
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            payment = form.save(commit=False)
            if not payment.period.can_edit:
                form.add_error(None, "Период закрыт или архивный, редактирование запрещено.")
            else:
                payment.initiator = account_initiator(request.user)
                payment.updated_by = request.user
                payment.save()
                audit_event(payment, payment_updated_message(payment, form.changed_data), request.user)
                messages.success(request, "Выплата обновлена.")
                return redirect(safe_next_url(request, request.POST.get("next")) or "payment_list")
    else:
        form = PaymentForm(instance=payment)

    if not payment.period.can_edit:
        for field in form.fields.values():
            field.disabled = True

    return render(
        request,
        "payroll/payment_form.html",
        {
            "form": form,
            "title": "Редактирование выплаты",
            "payment": payment,
            "next_url": safe_next_url(request, request.GET.get("next")),
        },
    )


@login_required
def audit_log_list(request):
    today = timezone.localdate()
    years = list(
        AuditLog.objects.annotate(log_year=ExtractYear("created_at"))
        .values_list("log_year", flat=True)
        .distinct()
        .order_by("-log_year")
    )
    if today.year not in years:
        years.insert(0, today.year)

    selected_year = parse_int_choice(request.GET.get("year"), years, today.year)
    selected_month = parse_int_choice(
        request.GET.get("month"),
        [value for value, _label in MONTH_CHOICES],
        today.month,
    )

    logs = (
        AuditLog.objects.select_related("author")
        .filter(created_at__year=selected_year, created_at__month=selected_month)
        .order_by("-created_at", "-id")
    )

    if request.GET.get("download") == "txt":
        return audit_log_txt_response(logs, selected_year, selected_month)

    paginator = Paginator(logs, 50)
    page_obj = paginator.get_page(request.GET.get("page"))
    for log in page_obj.object_list:
        log.display_message = audit_log_message(log)

    return render(
        request,
        "payroll/audit_log_list.html",
        {
            "logs": page_obj.object_list,
            "page_obj": page_obj,
            "years": years,
            "months": MONTH_CHOICES,
            "selected_year": selected_year,
            "selected_month": selected_month,
            "selected_month_name": dict(MONTH_CHOICES)[selected_month],
            "total_logs": paginator.count,
        },
    )
