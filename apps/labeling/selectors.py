from apps.labeling.models import Task
from common.exceptions import NotFoundError


def get_task_or_404(*, task_id: int) -> Task:
    try:
        return Task.objects.select_related("room").get(id=task_id)
    except Task.DoesNotExist as exc:
        raise NotFoundError("Task not found.") from exc
