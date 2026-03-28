from apps.labeling.models import Annotation, TaskAssignment
from apps.rooms.models import RoomMembership
from apps.rooms.selectors import build_activity_series
from apps.users.models import User


def build_user_profile(*, user: User) -> dict:
    invitations_count = RoomMembership.objects.filter(user=user).count()
    joined_count = RoomMembership.objects.filter(user=user, status=RoomMembership.Status.JOINED).count()
    created_rooms_count = user.created_rooms.count()
    accessible_rooms_count = created_rooms_count + RoomMembership.objects.filter(user=user).exclude(room_id__in=user.created_rooms.values_list("id", flat=True)).count()
    completed_tasks = Annotation.objects.filter(annotator=user).count()
    in_progress_tasks = TaskAssignment.objects.filter(
        annotator=user,
        status=TaskAssignment.Status.IN_PROGRESS,
    ).count()
    activity = build_activity_series(
        annotations_qs=Annotation.objects.filter(annotator=user),
    )
    return {
        "id": user.id,
        "username": user.username,
        "overview": {
            "accessible_rooms_count": accessible_rooms_count,
            "created_rooms_count": created_rooms_count,
            "joined_rooms_count": joined_count,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": in_progress_tasks,
            "invitations_count": invitations_count,
        },
        "activity": activity,
    }
