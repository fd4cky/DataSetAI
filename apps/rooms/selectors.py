from django.db.models import QuerySet

from apps.rooms.models import Room, RoomMembership
from apps.users.models import User
from common.exceptions import NotFoundError


def list_customer_rooms(*, customer: User) -> QuerySet[Room]:
    return Room.objects.filter(created_by=customer).select_related("created_by")


def list_user_rooms(*, user: User) -> QuerySet[Room]:
    return (
        Room.objects.filter(memberships__user=user)
        .select_related("created_by")
        .prefetch_related("memberships")
        .distinct()
    )


def get_room_for_owner(*, room_id: int, owner: User) -> Room:
    try:
        return Room.objects.select_related("created_by").get(id=room_id, created_by=owner)
    except Room.DoesNotExist as exc:
        raise NotFoundError("Room not found.") from exc


def get_visible_room(*, room_id: int, user: User) -> Room:
    if user.role == User.Role.CUSTOMER:
        return get_room_for_owner(room_id=room_id, owner=user)

    try:
        return (
            Room.objects.select_related("created_by")
            .prefetch_related("memberships")
            .get(id=room_id, memberships__user=user)
        )
    except Room.DoesNotExist as exc:
        raise NotFoundError("Room not found.") from exc


def get_membership(*, room: Room, user: User) -> RoomMembership:
    try:
        return RoomMembership.objects.select_related("room", "user", "invited_by").get(room=room, user=user)
    except RoomMembership.DoesNotExist as exc:
        raise NotFoundError("Membership not found for this room.") from exc
