from django.db import connection, transaction
from django.utils import timezone

from apps.labeling.consensus import evaluate_annotation_consensus
from apps.labeling.models import Annotation, Task, TaskAssignment
from apps.rooms.models import Room, RoomMembership
from apps.users.models import User
from common.exceptions import AccessDeniedError, ConflictError

"""
Write-side business logic for task assignment and annotation submission.

Key invariant:
- a task can require more than one review when room cross-validation is enabled
- assignments are created lazily when an annotator requests the next task
- consensus is evaluated when enough submissions for the current round exist
"""


def _assert_joined_membership(*, room: Room, annotator: User) -> None:
    is_joined = RoomMembership.objects.filter(
        room=room,
        user=annotator,
        status=RoomMembership.Status.JOINED,
    ).exists()
    if not is_joined:
        raise AccessDeniedError("Annotator must join the room before labeling.")


def get_next_task_for_annotator(*, room: Room, annotator: User):
    _assert_joined_membership(room=room, annotator=annotator)

    with transaction.atomic():
        # Reuse an unfinished assignment first so refreshes do not hand out a
        # second task to the same annotator while the current one is open.
        current_assignment = (
            TaskAssignment.objects.select_related("task")
            .select_for_update()
            .filter(
                task__room=room,
                annotator=annotator,
                status=TaskAssignment.Status.IN_PROGRESS,
            )
            .order_by("task_id")
            .first()
        )
        if current_assignment:
            return current_assignment.task

        queryset = Task.objects.filter(
            room=room,
            status__in=(Task.Status.PENDING, Task.Status.IN_PROGRESS),
        ).order_by("id")
        # `skip_locked` lets multiple annotators ask for work concurrently
        # without blocking each other on the same candidate task.
        if connection.features.has_select_for_update_skip_locked:
            queryset = queryset.select_for_update(skip_locked=True)
        else:
            queryset = queryset.select_for_update()

        required_reviews = room.required_reviews_per_item
        for next_task in queryset:
            if next_task.assignments.filter(annotator=annotator).exists():
                continue

            round_assignments_count = next_task.assignments.filter(
                round_number=next_task.current_round,
            ).count()
            if round_assignments_count >= required_reviews:
                continue

            TaskAssignment.objects.create(
                task=next_task,
                annotator=annotator,
                round_number=next_task.current_round,
                status=TaskAssignment.Status.IN_PROGRESS,
                assigned_at=timezone.now(),
            )

            if next_task.status != Task.Status.IN_PROGRESS:
                next_task.status = Task.Status.IN_PROGRESS
                next_task.save(update_fields=["status", "updated_at"])

            return next_task

        return None


def submit_annotation(*, task: Task, annotator: User, result_payload):
    with transaction.atomic():
        locked_task = Task.objects.select_for_update().select_related("room").get(id=task.id)
        if locked_task.status != Task.Status.IN_PROGRESS:
            raise ConflictError("Only tasks in progress can be submitted.")

        assignment = (
            TaskAssignment.objects.select_for_update()
            .filter(
                task=locked_task,
                annotator=annotator,
                status=TaskAssignment.Status.IN_PROGRESS,
            )
            .order_by("-round_number", "-assigned_at")
            .first()
        )
        if assignment is None:
            raise AccessDeniedError("Task is not assigned to the current annotator.")

        if Annotation.objects.filter(assignment=assignment).exists():
            raise ConflictError("Annotation for this assignment already exists.")

        annotation = Annotation.objects.create(
            task=locked_task,
            assignment=assignment,
            annotator=annotator,
            result_payload=result_payload,
            submitted_at=timezone.now(),
        )

        assignment.status = TaskAssignment.Status.SUBMITTED
        assignment.submitted_at = annotation.submitted_at
        assignment.save(update_fields=["status", "submitted_at", "updated_at"])

        round_assignments = list(
            locked_task.assignments.filter(round_number=locked_task.current_round).order_by("id")
        )
        submitted_assignments = [item for item in round_assignments if item.status == TaskAssignment.Status.SUBMITTED]

        required_reviews = locked_task.room.required_reviews_per_item
        if len(submitted_assignments) >= required_reviews:
            # Once the round has enough reviews we either accept consensus and
            # close the task, or reopen it for the next round.
            round_annotations = list(
                Annotation.objects.filter(assignment__in=submitted_assignments).order_by("submitted_at", "id")
            )
            consensus = evaluate_annotation_consensus(
                annotations=round_annotations,
                similarity_threshold=locked_task.room.cross_validation_similarity_threshold,
            )

            locked_task.validation_score = consensus["score"]
            if consensus["accepted"]:
                locked_task.status = Task.Status.SUBMITTED
                locked_task.consensus_payload = consensus["consensus_payload"]
            else:
                locked_task.status = Task.Status.PENDING
                locked_task.current_round += 1
                locked_task.consensus_payload = None

            locked_task.save(
                update_fields=[
                    "status",
                    "current_round",
                    "validation_score",
                    "consensus_payload",
                    "updated_at",
                ]
            )
        else:
            locked_task.save(update_fields=["updated_at"])

        return annotation
