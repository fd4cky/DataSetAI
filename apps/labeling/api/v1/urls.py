from django.urls import path

from apps.labeling.api.v1.views import RoomNextTaskView, TaskSubmitView


urlpatterns = [
    path("rooms/<int:room_id>/tasks/next/", RoomNextTaskView.as_view(), name="room-next-task"),
    path("tasks/<int:task_id>/submit/", TaskSubmitView.as_view(), name="task-submit"),
]
