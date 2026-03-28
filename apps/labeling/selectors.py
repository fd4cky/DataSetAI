from apps.labeling.models import Task
from common.exceptions import NotFoundError

"""Read helpers for the labeling domain."""


def get_task_or_404(*, task_id: int) -> Task:
    try:
        return Task.objects.select_related("room").get(id=task_id)
    except Task.DoesNotExist as exc:
        raise NotFoundError("Task not found.") from exc


def get_task_for_owner_review(*, task_id: int, owner) -> Task:
    task = get_task_or_404(task_id=task_id)
    if task.room.created_by_id != owner.id:
        raise NotFoundError("Task not found.")
    return task
