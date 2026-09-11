from django.urls import include, path

from core.views import home


urlpatterns = [
    path("", home, name="home"),
    path("periods/", include("core.urls")),
    path("payroll/", include("payroll.urls")),
    path("users/", include("users.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
]
