from django.conf import settings
from django.db import models
from uuid import uuid4

from common.models import TimeStampedModel

"""
Task/assignment/annotation models for the labeling pipeline.

`Task` is the unit of work.
`TaskAssignment` tracks who is currently working on it for a round.
`Annotation` stores the submitted result bound to a concrete assignment.
"""


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
    current_round = models.PositiveIntegerField(default=1)
    validation_score = models.FloatField(null=True, blank=True)
    consensus_payload = models.JSONField(null=True, blank=True)
    source_type = models.CharField(
        max_length=16,
        choices=SourceType.choices,
        default=SourceType.TEXT,
    )
    source_file = models.FileField(upload_to=task_source_upload_to, blank=True)
    source_name = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("id",)
        indexes = [
            models.Index(fields=("room", "status")),
        ]

    def __str__(self) -> str:
        return f"Task {self.id} in room {self.room_id}"


class Annotation(TimeStampedModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="annotations")
    assignment = models.OneToOneField(
        "labeling.TaskAssignment",
        on_delete=models.CASCADE,
        related_name="annotation",
    )
    annotator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="annotations",
    )
    result_payload = models.JSONField()
    submitted_at = models.DateTimeField()

    class Meta:
        ordering = ("-submitted_at", "-id")
        constraints = [
            models.UniqueConstraint(fields=("task", "annotator"), name="unique_task_annotator_annotation"),
        ]

    def __str__(self) -> str:
        return f"Annotation {self.id} for task {self.task_id}"


class TaskAssignment(TimeStampedModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        SUBMITTED = "submitted", "Submitted"

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="assignments")
    annotator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_assignments",
    )
    round_number = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.IN_PROGRESS)
    assigned_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("task_id", "round_number", "annotator_id")
        constraints = [
            models.UniqueConstraint(fields=("task", "annotator"), name="unique_task_assignment_annotator"),
        ]
        indexes = [
            models.Index(fields=("task", "status"), name="labeling_ta_task_st_4f3f33_idx"),
            models.Index(fields=("annotator", "status"), name="labeling_ta_annota_86cd11_idx"),
            models.Index(fields=("task", "round_number", "status"), name="labeling_ta_task_ro_217969_idx"),
        ]

    def __str__(self) -> str:
        return f"Assignment task={self.task_id} annotator={self.annotator_id} round={self.round_number}"
