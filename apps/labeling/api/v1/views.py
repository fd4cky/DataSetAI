from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.labeling.api.v1.serializers import (
    AnnotationSerializer,
    AnnotationSubmitSerializer,
    ReviewTaskDetailSerializer,
    ReviewTaskListItemSerializer,
    TaskSerializer,
)
from apps.labeling.selectors import get_task_for_owner_review, get_task_or_404
from apps.labeling.services import get_next_task_for_annotator, reject_task_annotation, submit_annotation
from apps.rooms.selectors import get_room_for_owner, get_visible_room

"""
Labeling endpoints used by the annotator workflow:
- ask for the next available task in a room
- submit an annotation for an assigned task
"""


class RoomNextTaskView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_id: int):
        room = get_visible_room(room_id=room_id, user=request.user)
        task = get_next_task_for_annotator(room=room, annotator=request.user)
        if task is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(TaskSerializer(task, context={"request": request}).data)


class TaskSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id: int):
        task = get_task_or_404(task_id=task_id)
        serializer = AnnotationSubmitSerializer(data=request.data, context={"task": task})
        serializer.is_valid(raise_exception=True)
        annotation = submit_annotation(
            task=task,
            annotator=request.user,
            result_payload=serializer.validated_data["result_payload"],
        )
        return Response(AnnotationSerializer(annotation).data, status=status.HTTP_201_CREATED)


class RoomReviewTaskListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_id: int):
        room = get_room_for_owner(room_id=room_id, owner=request.user)
        tasks = room.tasks.filter(status="submitted").prefetch_related("annotations").order_by("-updated_at", "-id")
        serializer = ReviewTaskListItemSerializer(tasks, many=True, context={"request": request})
        return Response(serializer.data)


class TaskReviewDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id: int):
        task = get_task_for_owner_review(task_id=task_id, owner=request.user)
        task = task.__class__.objects.select_related("room").prefetch_related("annotations__annotator", "annotations__assignment").get(
            id=task.id
        )
        payload = {
            "task": task,
            "consensus_payload": task.consensus_payload,
            "annotations": task.annotations.order_by("-submitted_at", "-id"),
        }
        return Response(ReviewTaskDetailSerializer(payload, context={"request": request}).data)


class TaskRejectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id: int):
        task = get_task_for_owner_review(task_id=task_id, owner=request.user)
        task = reject_task_annotation(task=task, owner=request.user)
        return Response(TaskSerializer(task, context={"request": request}).data)
