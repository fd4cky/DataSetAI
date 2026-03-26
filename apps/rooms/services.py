from django.utils import timezone

from apps.rooms.models import Room, RoomMembership
from apps.users.models import User
from common.exceptions import AccessDeniedError, ConflictError, NotFoundError


def create_room(*, creator: User, title: str, description: str = "") -> Room:
    if creator.role != User.Role.CUSTOMER:
        raise AccessDeniedError("Only customers can create rooms.")
    return Room.objects.create(title=title, description=description, created_by=creator)


def invite_user_to_room(*, room: Room, inviter: User, invited_user_id: int) -> RoomMembership:
    if inviter.role != User.Role.CUSTOMER or room.created_by_id != inviter.id:
        raise AccessDeniedError("Only the room owner can invite annotators.")

    try:
        invited_user = User.objects.get(id=invited_user_id)
    except User.DoesNotExist as exc:
        raise NotFoundError("Invited user not found.") from exc

    if invited_user.role != User.Role.ANNOTATOR:
        raise ConflictError("Only annotators can be invited to rooms.")

    membership, created = RoomMembership.objects.get_or_create(
        room=room,
        user=invited_user,
        defaults={
            "invited_by": inviter,
            "status": RoomMembership.Status.INVITED,
        },
    )

    if not created and membership.status == RoomMembership.Status.INVITED:
        membership.invited_by = inviter
        membership.save(update_fields=["invited_by", "updated_at"])

    return membership


def join_room(*, room: Room, annotator: User) -> RoomMembership:
    if annotator.role != User.Role.ANNOTATOR:
        raise AccessDeniedError("Only annotators can join rooms.")

    try:
        membership = RoomMembership.objects.get(room=room, user=annotator)
    except RoomMembership.DoesNotExist as exc:
        raise AccessDeniedError("You were not invited to this room.") from exc

    if membership.status != RoomMembership.Status.JOINED:
        membership.status = RoomMembership.Status.JOINED
        membership.joined_at = timezone.now()
        membership.save(update_fields=["status", "joined_at", "updated_at"])

    return membership
