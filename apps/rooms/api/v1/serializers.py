from rest_framework import serializers

from apps.rooms.models import Room, RoomMembership


class RoomCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)


class RoomSerializer(serializers.ModelSerializer):
    created_by_id = serializers.IntegerField(read_only=True)
    membership_status = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = (
            "id",
            "title",
            "description",
            "created_by_id",
            "membership_status",
            "created_at",
            "updated_at",
        )

    def get_membership_status(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None
        membership = obj.memberships.filter(user=user).only("status").first()
        return membership.status if membership else None


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
