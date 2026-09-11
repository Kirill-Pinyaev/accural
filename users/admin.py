from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Права в системе начисления", {"fields": ("role",)}),
    )
    list_display = ("username", "email", "first_name", "last_name", "role", "is_staff")
    list_filter = UserAdmin.list_filter + ("role",)
