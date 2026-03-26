from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class Room(TimeStampedModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_rooms",
    )

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return self.title


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
