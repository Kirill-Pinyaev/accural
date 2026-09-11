from django.contrib import admin

from core.models import AccountingPeriod


@admin.register(AccountingPeriod)
class AccountingPeriodAdmin(admin.ModelAdmin):
    list_display = ("year", "month", "status", "is_archived", "updated_at")
    list_filter = ("year", "status", "is_archived")
    ordering = ("-year", "-month")
    search_fields = ("year",)
    actions = ("close_periods", "reopen_periods", "archive_periods")

    @admin.action(description="Закрыть выбранные периоды")
    def close_periods(self, request, queryset):
        for period in queryset:
            period.close()

    @admin.action(description="Открыть выбранные периоды")
    def reopen_periods(self, request, queryset):
        for period in queryset:
            period.reopen()

    @admin.action(description="Перенести выбранные периоды в архив")
    def archive_periods(self, request, queryset):
        queryset.update(status=AccountingPeriod.Status.CLOSED, is_archived=True)
