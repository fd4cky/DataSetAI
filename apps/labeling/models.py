from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class Task(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In progress"
        SUBMITTED = "submitted", "Submitted"

    room = models.ForeignKey("rooms.Room", on_delete=models.CASCADE, related_name="tasks")
    input_payload = models.JSONField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    assigned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("id",)
        indexes = [
            models.Index(fields=("room", "status")),
            models.Index(fields=("assigned_to", "status")),
        ]

    def __str__(self) -> str:
        return f"Task {self.id} in room {self.room_id}"


class Annotation(TimeStampedModel):
    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name="annotation")
    annotator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="annotations",
    )
    result_payload = models.JSONField()
    submitted_at = models.DateTimeField()

    class Meta:
        ordering = ("-submitted_at", "-id")

    def __str__(self) -> str:
        return f"Annotation {self.id} for task {self.task_id}"
