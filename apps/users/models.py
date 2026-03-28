from django.contrib.auth.models import AbstractUser
from django.db import models

"""Custom user model kept intentionally small for the MVP."""


class User(AbstractUser):
    class Role(models.TextChoices):
        USER = "user", "User"
        CUSTOMER = "customer", "Customer"
        ANNOTATOR = "annotator", "Annotator"

    role = models.CharField(max_length=32, choices=Role.choices, default=Role.USER)

    def __str__(self) -> str:
        return self.username
