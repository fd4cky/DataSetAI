from collections import Counter
from datetime import timedelta

from django.db.models import Exists, OuterRef, QuerySet
from django.utils import timezone

from apps.labeling.models import Annotation, Task, TaskAssignment

from apps.rooms.models import Room, RoomMembership, RoomPin
from apps.rooms.services import get_supported_export_formats
from apps.users.models import User
from common.exceptions import NotFoundError


def list_owned_rooms(*, user: User) -> QuerySet[Room]:
    pinned_subquery = RoomPin.objects.filter(room_id=OuterRef("pk"), user=user)
    return (
        Room.objects.filter(created_by=user)
        .annotate(is_pinned=Exists(pinned_subquery))
        .select_related("created_by")
        .prefetch_related("tasks", "memberships", "labels")
        .order_by("-is_pinned", "-created_at", "-id")
    )


def list_member_rooms(*, user: User) -> QuerySet[Room]:
    pinned_subquery = RoomPin.objects.filter(room_id=OuterRef("pk"), user=user)
    return (
        Room.objects.filter(memberships__user=user)
        .annotate(is_pinned=Exists(pinned_subquery))
        .select_related("created_by")
        .prefetch_related("memberships", "tasks", "labels")
        .distinct()
        .order_by("-is_pinned", "-created_at", "-id")
    )


def get_room_for_owner(*, room_id: int, owner: User) -> Room:
    try:
        return Room.objects.select_related("created_by").get(id=room_id, created_by=owner)
    except Room.DoesNotExist as exc:
        raise NotFoundError("Room not found.") from exc


def get_room_by_id(*, room_id: int) -> Room:
    try:
        return Room.objects.select_related("created_by").prefetch_related("memberships", "labels").get(id=room_id)
    except Room.DoesNotExist as exc:
        raise NotFoundError("Room not found.") from exc


def get_visible_room(*, room_id: int, user: User) -> Room:
    room = get_room_by_id(room_id=room_id)
    if room.created_by_id == user.id:
        return room
    if room.memberships.filter(user=user).exists():
        return room
    raise NotFoundError("Room not found.")


def get_membership(*, room: Room, user: User) -> RoomMembership:
    try:
        return RoomMembership.objects.select_related("room", "user", "invited_by").get(room=room, user=user)
    except RoomMembership.DoesNotExist as exc:
        raise NotFoundError("Membership not found for this room.") from exc


def build_activity_series(*, annotations_qs, days: int = 49) -> list[dict]:
    end_date = timezone.localdate()
    start_date = end_date - timedelta(days=days - 1)
    activity_dates = annotations_qs.filter(submitted_at__date__gte=start_date).values_list("submitted_at__date", flat=True)
    counts = Counter(activity_dates)

    return [
        {
            "date": current_date.isoformat(),
            "count": counts.get(current_date, 0),
        }
        for current_date in (start_date + timedelta(days=offset) for offset in range(days))
    ]


def build_room_dashboard(*, room: Room, actor: User) -> dict:
    total_tasks = Task.objects.filter(room=room).count()
    completed_tasks = Task.objects.filter(room=room, status=Task.Status.SUBMITTED).count()
    remaining_tasks = max(total_tasks - completed_tasks, 0)
    progress_percent = round((completed_tasks / total_tasks) * 100, 1) if total_tasks else 0.0

    overview = {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "remaining_tasks": remaining_tasks,
        "progress_percent": progress_percent,
    }

    actor_membership_status = RoomMembership.objects.filter(room=room, user=actor).values_list("status", flat=True).first()
    actor_is_owner = room.created_by_id == actor.id
    actor_room_role = "customer" if actor_is_owner else "annotator"
    actor_can_manage = actor_is_owner
    actor_can_annotate = actor_is_owner or actor_membership_status == RoomMembership.Status.JOINED

    payload = {
        "room": {
            "id": room.id,
            "title": room.title,
            "description": room.description,
            "dataset_label": room.dataset_label,
            "dataset_type": room.dataset_type,
            "cross_validation_enabled": room.cross_validation_enabled,
            "cross_validation_annotators_count": room.cross_validation_annotators_count,
            "cross_validation_similarity_threshold": room.cross_validation_similarity_threshold,
            "deadline": room.deadline.isoformat() if room.deadline else None,
            "has_password": room.has_password,
            "is_pinned": RoomPin.objects.filter(room=room, user=actor).exists(),
            "created_by_id": room.created_by_id,
            "membership_status": "owner" if room.created_by_id == actor.id else actor_membership_status,
        },
        "labels": [
            {
                "id": label.id,
                "name": label.name,
                "color": label.color,
                "sort_order": label.sort_order,
            }
            for label in room.labels.all()
        ],
        "export_formats": get_supported_export_formats(room=room),
        "overview": overview,
        "actor": {
            "id": actor.id,
            "username": actor.username,
            "role": actor_room_role,
            "can_manage": actor_can_manage,
            "can_annotate": actor_can_annotate,
        },
    }

    if actor_can_annotate:
        actor_completed = Annotation.objects.filter(task__room=room, annotator=actor).count()
        actor_in_progress = TaskAssignment.objects.filter(
            task__room=room,
            annotator=actor,
            status=TaskAssignment.Status.IN_PROGRESS,
        ).count()
        actor_remaining = max(total_tasks - actor_completed, 0)
        actor_progress = round((actor_completed / total_tasks) * 100, 1) if total_tasks else 0.0
        activity = build_activity_series(
            annotations_qs=Annotation.objects.filter(task__room=room, annotator=actor),
        )

        payload["annotator_stats"] = {
            "completed_tasks": actor_completed,
            "in_progress_tasks": actor_in_progress,
            "remaining_tasks": actor_remaining,
            "progress_percent": actor_progress,
            "activity": activity,
        }
        if not actor_can_manage:
            return payload

    annotators = []
    memberships = RoomMembership.objects.filter(room=room).select_related("user").order_by("user__username")
    for membership in memberships:
        user = membership.user
        user_completed = Annotation.objects.filter(task__room=room, annotator=user).count()
        user_in_progress = TaskAssignment.objects.filter(
            task__room=room,
            annotator=user,
            status=TaskAssignment.Status.IN_PROGRESS,
        ).count()
        user_remaining = max(total_tasks - user_completed, 0)
        user_progress = round((user_completed / total_tasks) * 100, 1) if total_tasks else 0.0

        annotators.append(
            {
                "user_id": user.id,
                "username": user.username,
                "status": membership.status,
                "joined_at": membership.joined_at.isoformat() if membership.joined_at else None,
                "completed_tasks": user_completed,
                "in_progress_tasks": user_in_progress,
                "remaining_tasks": user_remaining,
                "progress_percent": user_progress,
                "activity": build_activity_series(
                    annotations_qs=Annotation.objects.filter(task__room=room, annotator=user),
                ),
            }
        )

    payload["annotators"] = annotators
    return payload
