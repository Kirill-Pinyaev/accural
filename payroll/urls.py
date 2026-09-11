from django.urls import path

from payroll import views


urlpatterns = [
    path("employees/", views.employee_list, name="employee_list"),
    path("employees/new/", views.employee_create, name="employee_create"),
    path("employees/delete/", views.employee_delete, name="employee_delete"),
    path("employees/<int:pk>/edit/", views.employee_update, name="employee_update"),
    path("employees/<int:employee_id>/rates/", views.rate_edit, name="rate_edit"),
    path("rates/import/", views.rate_import_upload, name="rate_import_upload"),
    path("rates/import/preview/", views.rate_import_preview, name="rate_import_preview"),
    path("rates/import/apply/", views.rate_import_apply, name="rate_import_apply"),
    path("timesheet/", views.timesheet_entry_list, name="timesheet_entry_list"),
    path("timesheet/import/", views.timesheet_import_upload, name="timesheet_import_upload"),
    path("timesheet/import/preview/", views.timesheet_import_preview, name="timesheet_import_preview"),
    path("timesheet/import/apply/", views.timesheet_import_apply, name="timesheet_import_apply"),
    path("accruals/", views.accrual_list, name="accrual_list"),
    path("accruals/export/", views.accrual_export, name="accrual_export"),
    path("accruals/<int:record_id>/edit/", views.accrual_edit, name="accrual_edit"),
    path("payments/", views.payment_list, name="payment_list"),
    path("payments/export/", views.payment_export, name="payment_export"),
    path("payments/new/", views.payment_create, name="payment_create"),
    path("payments/<int:pk>/edit/", views.payment_update, name="payment_update"),
    path("audit/", views.audit_log_list, name="audit_log_list"),
]
