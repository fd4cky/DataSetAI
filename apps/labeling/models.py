from django.conf import settings
from django.db import models
from uuid import uuid4

from common.models import TimeStampedModel


def task_source_upload_to(instance, filename: str) -> str:
    return f"task_sources/room_{instance.room_id}/{uuid4().hex}_{filename}"


class Task(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In progress"
        SUBMITTED = "submitted", "Submitted"

    class SourceType(models.TextChoices):
        TEXT = "text", "Text"
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    room = models.ForeignKey("rooms.Room", on_delete=models.CASCADE, related_name="tasks")
    input_payload = models.JSONField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    source_type = models.CharField(
        max_length=16,
        choices=SourceType.choices,
        default=SourceType.TEXT,
    )
    source_file = models.FileField(upload_to=task_source_upload_to, blank=True)
    source_name = models.CharField(max_length=255, blank=True)
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
