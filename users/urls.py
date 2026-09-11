from django.urls import path

from users import views


urlpatterns = [
    path("", views.app_user_list, name="app_user_list"),
    path("new/", views.app_user_create, name="app_user_create"),
    path("<int:pk>/edit/", views.app_user_update, name="app_user_update"),
    path("<int:pk>/password/", views.app_user_password, name="app_user_password"),
    path("<int:pk>/delete/", views.app_user_delete, name="app_user_delete"),
]
