from django.db import connection, transaction
from django.utils import timezone

from apps.labeling.models import Annotation, Task
from apps.rooms.models import Room, RoomMembership
from apps.users.models import User
from common.exceptions import AccessDeniedError, ConflictError


def _assert_joined_membership(*, room: Room, annotator: User) -> None:
    is_joined = RoomMembership.objects.filter(
        room=room,
        user=annotator,
        status=RoomMembership.Status.JOINED,
    ).exists()
    if not is_joined:
        raise AccessDeniedError("Annotator must join the room before labeling.")


def get_next_task_for_annotator(*, room: Room, annotator: User):
    if annotator.role != User.Role.ANNOTATOR:
        raise AccessDeniedError("Only annotators can request tasks.")

    _assert_joined_membership(room=room, annotator=annotator)

    with transaction.atomic():
        current_task = (
            Task.objects.select_for_update()
            .filter(room=room, assigned_to=annotator, status=Task.Status.IN_PROGRESS)
            .order_by("id")
            .first()
        )
        if current_task:
            return current_task

        queryset = Task.objects.filter(room=room, status=Task.Status.PENDING).order_by("id")
        if connection.features.has_select_for_update_skip_locked:
            queryset = queryset.select_for_update(skip_locked=True)
        else:
            queryset = queryset.select_for_update()

        next_task = queryset.first()
        if not next_task:
            return None

        next_task.status = Task.Status.IN_PROGRESS
        next_task.assigned_to = annotator
        next_task.assigned_at = timezone.now()
        next_task.save(update_fields=["status", "assigned_to", "assigned_at", "updated_at"])
        return next_task


def submit_annotation(*, task: Task, annotator: User, result_payload):
    if annotator.role != User.Role.ANNOTATOR:
        raise AccessDeniedError("Only annotators can submit annotations.")
    if task.assigned_to_id != annotator.id:
        raise AccessDeniedError("Task is not assigned to the current annotator.")
    if task.status != Task.Status.IN_PROGRESS:
        raise ConflictError("Only tasks in progress can be submitted.")

    with transaction.atomic():
        if Annotation.objects.filter(task=task).exists():
            raise ConflictError("Annotation for this task already exists.")

        annotation = Annotation.objects.create(
            task=task,
            annotator=annotator,
            result_payload=result_payload,
            submitted_at=timezone.now(),
        )

        task.status = Task.Status.SUBMITTED
        task.save(update_fields=["status", "updated_at"])

        return annotation
