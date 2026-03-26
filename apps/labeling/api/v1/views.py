from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.labeling.api.v1.serializers import AnnotationSerializer, AnnotationSubmitSerializer, TaskSerializer
from apps.labeling.selectors import get_task_or_404
from apps.labeling.services import get_next_task_for_annotator, submit_annotation
from apps.rooms.selectors import get_visible_room


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
