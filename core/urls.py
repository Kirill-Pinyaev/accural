from django.urls import path

from core import views


urlpatterns = [
    path("", views.period_list, name="period_list"),
    path("new/", views.period_create, name="period_create"),
    path("delete/", views.period_delete, name="period_delete"),
    path("<int:pk>/close/", views.period_close, name="period_close"),
    path("<int:pk>/reopen/", views.period_reopen, name="period_reopen"),
]
