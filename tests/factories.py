from apps.labeling.models import Task
from apps.rooms.models import Room, RoomMembership
from apps.users.models import User


def make_user(*, username: str, role: str, email: str | None = None) -> User:
    return User.objects.create(username=username, email=email or f"{username}@example.com", role=role)


def make_room(*, customer: User, title: str = "Room", description: str = "", dataset_type: str = Room.DatasetType.DEMO) -> Room:
    return Room.objects.create(title=title, description=description, created_by=customer, dataset_type=dataset_type)


def invite_annotator(*, room: Room, annotator: User, invited_by: User, joined: bool = False) -> RoomMembership:
    membership = RoomMembership.objects.create(
        room=room,
        user=annotator,
        invited_by=invited_by,
        status=RoomMembership.Status.JOINED if joined else RoomMembership.Status.INVITED,
    )
    return membership


def make_task(
    *,
    room: Room,
    payload: dict,
    source_type: str = Task.SourceType.TEXT,
    source_name: str = "",
) -> Task:
    return Task.objects.create(
        room=room,
        input_payload=payload,
        source_type=source_type,
        source_name=source_name,
    )
