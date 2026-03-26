import json

from rest_framework import serializers

from apps.rooms.models import Room, RoomLabel, RoomMembership
from apps.rooms.services import get_supported_export_formats, validate_dataset_upload
from common.exceptions import ConflictError


class JsonStringField(serializers.Field):
    default_error_messages = {
        "invalid": "Expected a JSON value or JSON string.",
    }

    def to_internal_value(self, data):
        if data in (None, "", []):
            return None
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError as exc:
                raise serializers.ValidationError(self.error_messages["invalid"]) from exc
        return data

    def to_representation(self, value):
        return value


class RoomLabelDefinitionSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=64)
    color = serializers.RegexField(regex=r"^#[0-9A-Fa-f]{6}$", required=False, allow_blank=True)


class MediaManifestItemSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    width = serializers.IntegerField(required=False, min_value=1)
    height = serializers.IntegerField(required=False, min_value=1)
    duration = serializers.FloatField(required=False, min_value=0)
    frame_rate = serializers.IntegerField(required=False, min_value=1)


class RoomCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    deadline = serializers.DateTimeField(required=False, allow_null=True)
    annotator_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
    )
    dataset_mode = serializers.ChoiceField(choices=Room.DatasetType.values, required=False, default=Room.DatasetType.DEMO)
    test_task_count = serializers.IntegerField(required=False, min_value=1, max_value=100, default=12)
    dataset_label = serializers.CharField(required=False, allow_blank=True, default="Тестовый датасет")
    dataset_files = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False),
        required=False,
        allow_empty=True,
        write_only=True,
    )
    labels = JsonStringField(required=False)
    media_manifest = JsonStringField(required=False)

    def validate(self, attrs):
        dataset_mode = attrs.get("dataset_mode", Room.DatasetType.DEMO)
        dataset_files = list(attrs.get("dataset_files") or [])
        labels = attrs.get("labels")
        media_manifest = attrs.get("media_manifest")

        try:
            validate_dataset_upload(dataset_mode=dataset_mode, dataset_files=dataset_files)
        except ConflictError as exc:
            raise serializers.ValidationError({"dataset_files": str(exc)}) from exc

        if labels is None:
            attrs["labels"] = []
        else:
            if not isinstance(labels, list):
                raise serializers.ValidationError({"labels": "Labels must be a JSON array."})
            serializer = RoomLabelDefinitionSerializer(data=labels, many=True)
            serializer.is_valid(raise_exception=True)
            attrs["labels"] = serializer.validated_data

        if dataset_mode in (Room.DatasetType.IMAGE, Room.DatasetType.VIDEO) and not attrs["labels"]:
            raise serializers.ValidationError({"labels": "Provide at least one label for image or video datasets."})

        if media_manifest in (None, ""):
            attrs["media_manifest"] = []
        else:
            if not isinstance(media_manifest, list):
                raise serializers.ValidationError({"media_manifest": "Media manifest must be a JSON array."})
            serializer = MediaManifestItemSerializer(data=media_manifest, many=True)
            serializer.is_valid(raise_exception=True)
            attrs["media_manifest"] = serializer.validated_data

        return attrs


class RoomLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomLabel
        fields = (
            "id",
            "name",
            "color",
            "sort_order",
        )


class RoomSerializer(serializers.ModelSerializer):
    created_by_id = serializers.IntegerField(read_only=True)
    membership_status = serializers.SerializerMethodField()
    has_password = serializers.SerializerMethodField()
    total_tasks = serializers.SerializerMethodField()
    completed_tasks = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()
    labels = RoomLabelSerializer(many=True, read_only=True)
    export_formats = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = (
            "id",
            "title",
            "description",
            "dataset_label",
            "dataset_type",
            "deadline",
            "created_by_id",
            "membership_status",
            "has_password",
            "total_tasks",
            "completed_tasks",
            "progress_percent",
            "labels",
            "export_formats",
            "created_at",
            "updated_at",
        )

    def get_membership_status(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None
        if obj.created_by_id == user.id:
            return "owner"
        membership = obj.memberships.filter(user=user).only("status").first()
        return membership.status if membership else None

    def get_has_password(self, obj):
        return obj.has_password

    def get_total_tasks(self, obj):
        return obj.tasks.count()

    def get_completed_tasks(self, obj):
        return obj.tasks.filter(status="submitted").count()

    def get_progress_percent(self, obj):
        total = obj.tasks.count()
        completed = obj.tasks.filter(status="submitted").count()
        if not total:
            return 0.0
        return round((completed / total) * 100, 1)

    def get_export_formats(self, obj):
        return get_supported_export_formats(room=obj)


class RoomMembershipSerializer(serializers.ModelSerializer):
    room_id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(read_only=True)
    invited_by_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = RoomMembership
        fields = (
            "id",
            "room_id",
            "user_id",
            "invited_by_id",
            "status",
            "joined_at",
            "created_at",
            "updated_at",
        )


class InviteAnnotatorSerializer(serializers.Serializer):
    annotator_id = serializers.IntegerField(min_value=1)


class RoomAccessSerializer(serializers.Serializer):
    room_id = serializers.IntegerField(min_value=1)
    password = serializers.CharField(required=False, allow_blank=True)


class RoomJoinSerializer(serializers.Serializer):
    password = serializers.CharField(required=False, allow_blank=True)
