from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    REQUIRED_FIELDS = []

    class Role(models.TextChoices):
        ADMIN = "admin", "Администратор"
        MANAGER = "manager", "Руководство"

    role = models.CharField(
        "роль",
        max_length=20,
        choices=Role.choices,
        default=Role.MANAGER,
    )

    @property
    def is_accountant_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER
