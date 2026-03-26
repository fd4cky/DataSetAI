from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        ANNOTATOR = "annotator", "Annotator"

    role = models.CharField(max_length=32, choices=Role.choices)

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"
