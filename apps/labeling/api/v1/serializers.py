from rest_framework import serializers

from apps.labeling.models import Annotation, Task


class TaskSerializer(serializers.ModelSerializer):
    room_id = serializers.IntegerField(read_only=True)
    source_file_url = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = (
            "id",
            "room_id",
            "status",
            "current_round",
            "validation_score",
            "input_payload",
            "source_type",
            "source_name",
            "source_file_url",
            "created_at",
            "updated_at",
        )

    def get_source_file_url(self, obj):
        if not obj.source_file:
            return None
        request = self.context.get("request")
        if request is None:
            return obj.source_file.url
        return request.build_absolute_uri(obj.source_file.url)


class BoundingBoxAnnotationSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=("bbox",))
    label_id = serializers.IntegerField(min_value=1)
    points = serializers.ListField(
        child=serializers.FloatField(),
        min_length=4,
        max_length=4,
    )
    frame = serializers.IntegerField(min_value=0)
    attributes = serializers.ListField(child=serializers.JSONField(), required=False, allow_empty=True)
    occluded = serializers.BooleanField(required=False, default=False)

    def validate_points(self, value):
        x_min, y_min, x_max, y_max = value
        if x_max <= x_min or y_max <= y_min:
            raise serializers.ValidationError("Bounding box points must form a positive-size rectangle.")
        return value


class AnnotationSubmitSerializer(serializers.Serializer):
    result_payload = serializers.JSONField()

    def validate_result_payload(self, value):
        task: Task = self.context["task"]
        if task.source_type not in (Task.SourceType.IMAGE, Task.SourceType.VIDEO):
            return value

        if not isinstance(value, dict):
            raise serializers.ValidationError("Media annotation payload must be a JSON object.")

        annotations = value.get("annotations")
        if annotations is None:
            raise serializers.ValidationError("Media annotation payload must contain an annotations array.")
        if not isinstance(annotations, list):
            raise serializers.ValidationError("Annotations must be an array.")

        serializer = BoundingBoxAnnotationSerializer(data=annotations, many=True)
        serializer.is_valid(raise_exception=True)

        valid_label_ids = set(task.room.labels.values_list("id", flat=True))
        invalid_label_ids = {
            item["label_id"]
            for item in serializer.validated_data
            if item["label_id"] not in valid_label_ids
        }
        if invalid_label_ids:
            raise serializers.ValidationError(f"Unknown label ids: {', '.join(map(str, sorted(invalid_label_ids)))}.")

        return {
            "annotations": serializer.validated_data,
        }


class AnnotationSerializer(serializers.ModelSerializer):
    task_id = serializers.IntegerField(read_only=True)
    annotator_id = serializers.IntegerField(read_only=True)
    assignment_id = serializers.IntegerField(read_only=True)
    annotator_username = serializers.CharField(source="annotator.username", read_only=True)
    round_number = serializers.IntegerField(source="assignment.round_number", read_only=True)

    class Meta:
        model = Annotation
        fields = (
            "id",
            "task_id",
            "assignment_id",
            "annotator_id",
            "annotator_username",
            "round_number",
            "result_payload",
            "submitted_at",
            "created_at",
            "updated_at",
        )


class ReviewTaskListItemSerializer(serializers.ModelSerializer):
    source_file_url = serializers.SerializerMethodField()
    annotations_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = (
            "id",
            "status",
            "current_round",
            "validation_score",
            "source_type",
            "source_name",
            "source_file_url",
            "annotations_count",
            "updated_at",
        )

    def get_source_file_url(self, obj):
        if not obj.source_file:
            return None
        request = self.context.get("request")
        if request is None:
            return obj.source_file.url
        return request.build_absolute_uri(obj.source_file.url)

    def get_annotations_count(self, obj):
        return obj.annotations.count()


class ReviewTaskDetailSerializer(serializers.Serializer):
    task = TaskSerializer()
    consensus_payload = serializers.JSONField(allow_null=True)
    annotations = AnnotationSerializer(many=True)
