from rest_framework import serializers

from apps.labeling.models import Annotation, Task


class TaskSerializer(serializers.ModelSerializer):
    room_id = serializers.IntegerField(read_only=True)
    assigned_to_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Task
        fields = (
            "id",
            "room_id",
            "status",
            "input_payload",
            "assigned_to_id",
            "assigned_at",
            "created_at",
            "updated_at",
        )


class AnnotationSubmitSerializer(serializers.Serializer):
    result_payload = serializers.JSONField()


class AnnotationSerializer(serializers.ModelSerializer):
    task_id = serializers.IntegerField(read_only=True)
    annotator_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Annotation
        fields = (
            "id",
            "task_id",
            "annotator_id",
            "result_payload",
            "submitted_at",
            "created_at",
            "updated_at",
        )
