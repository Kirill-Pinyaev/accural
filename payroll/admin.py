from django.contrib import admin

from payroll.models import AccrualRecord, AuditLog, Employee, EmployeeAlias, EmployeeRate, Payment, TimesheetEntry


class EmployeeAliasInline(admin.TabularInline):
    model = EmployeeAlias
    extra = 0
    readonly_fields = ("normalized_source_name", "created_at")


class EmployeeRateInline(admin.TabularInline):
    model = EmployeeRate
    extra = 0


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "personnel_number",
        "full_name",
        "organization",
        "project",
        "position",
        "employment_type",
        "status",
    )
    list_filter = ("organization", "employment_type", "status")
    search_fields = ("personnel_number", "full_name", "aliases__source_name")
    readonly_fields = ("normalized_full_name", "created_at", "updated_at")
    inlines = (EmployeeAliasInline, EmployeeRateInline)


@admin.register(EmployeeRate)
class EmployeeRateAdmin(admin.ModelAdmin):
    list_display = ("employee", "hourly_rate", "daily_rate", "updated_at")
    search_fields = ("employee__full_name", "employee__personnel_number")


@admin.register(EmployeeAlias)
class EmployeeAliasAdmin(admin.ModelAdmin):
    list_display = ("source_name", "employee", "source", "created_at")
    list_filter = ("source",)
    search_fields = ("source_name", "employee__full_name", "employee__personnel_number")
    readonly_fields = ("normalized_source_name", "created_at")


@admin.register(TimesheetEntry)
class TimesheetEntryAdmin(admin.ModelAdmin):
    list_display = ("employee", "period", "days", "hours", "updated_at")
    list_filter = ("period",)
    search_fields = ("employee__full_name", "employee__personnel_number", "source_name")
    readonly_fields = ("updated_at",)


@admin.register(AccrualRecord)
class AccrualRecordAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "period",
        "premium",
        "ktu",
        "salary",
        "salary_1c",
        "daily_allowance_1c",
        "previous_plus",
        "previous_minus",
        "previous_balance_manual_override",
        "updated_at",
    )
    list_filter = ("period",)
    search_fields = ("employee__full_name", "employee__personnel_number")
    readonly_fields = ("updated_at",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("employee", "period", "amount", "paid_at", "initiator", "updated_by", "updated_at")
    list_filter = ("period", "paid_at")
    search_fields = ("employee__full_name", "employee__personnel_number", "initiator", "comment")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "object_type", "object_id", "field_name", "author")
    list_filter = ("object_type", "field_name", "created_at")
    search_fields = ("object_repr", "field_name", "old_value", "new_value", "author__username")
    readonly_fields = (
        "object_type",
        "object_id",
        "object_repr",
        "field_name",
        "old_value",
        "new_value",
        "author",
        "created_at",
    )
