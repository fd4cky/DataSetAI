from django.conf import settings
from django.db import models
from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import RegexValidator

from common.models import TimeStampedModel


class Room(TimeStampedModel):
    class DatasetType(models.TextChoices):
        DEMO = "demo", "Demo"
        JSON = "json", "JSON"
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    access_password_hash = models.CharField(max_length=255, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    dataset_label = models.CharField(max_length=255, blank=True)
    dataset_type = models.CharField(
        max_length=16,
        choices=DatasetType.choices,
        default=DatasetType.DEMO,
    )
    cross_validation_enabled = models.BooleanField(default=False)
    cross_validation_annotators_count = models.PositiveSmallIntegerField(default=1)
    cross_validation_similarity_threshold = models.PositiveSmallIntegerField(default=80)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_rooms",
    )

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return self.title

    @property
    def has_password(self) -> bool:
        return bool(self.access_password_hash)

    def set_access_password(self, raw_password: str) -> None:
        self.access_password_hash = make_password(raw_password) if raw_password else ""

    def check_access_password(self, raw_password: str) -> bool:
        if not self.access_password_hash:
            return True
        return check_password(raw_password or "", self.access_password_hash)

    @property
    def required_reviews_per_item(self) -> int:
        if not self.cross_validation_enabled:
            return 1
        return max(1, self.cross_validation_annotators_count)


class RoomLabel(TimeStampedModel):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="labels")
    name = models.CharField(max_length=64)
    color = models.CharField(
        max_length=7,
        validators=[RegexValidator(regex=r"^#[0-9A-Fa-f]{6}$")],
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")
        constraints = [
            models.UniqueConstraint(fields=("room", "name"), name="unique_room_label_name"),
        ]

    def __str__(self) -> str:
        return f"{self.room_id}:{self.name}"


class RoomMembership(TimeStampedModel):
    class Status(models.TextChoices):
        INVITED = "invited", "Invited"
        JOINED = "joined", "Joined"

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="room_memberships",
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_room_invitations",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.INVITED)
    joined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("room_id", "user_id")
        constraints = [
            models.UniqueConstraint(fields=("room", "user"), name="unique_room_membership"),
        ]

    def __str__(self) -> str:
        return f"{self.room_id}:{self.user_id}:{self.status}"
