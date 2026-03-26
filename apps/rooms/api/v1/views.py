from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rooms.api.v1.serializers import (
    RoomAccessSerializer,
    InviteAnnotatorSerializer,
    RoomCreateSerializer,
    RoomJoinSerializer,
    RoomMembershipSerializer,
    RoomSerializer,
)
from apps.rooms.selectors import (
    build_room_dashboard,
    get_room_by_id,
    get_room_for_owner,
    get_visible_room,
    list_member_rooms,
    list_owned_rooms,
)
from apps.rooms.services import create_room, export_room_annotations, invite_user_to_room, join_room


class RoomListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rooms = list_owned_rooms(user=request.user)
        serializer = RoomSerializer(rooms, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        self.check_permissions(request)
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        dataset_files = request.FILES.getlist("dataset_files")
        if hasattr(data, "setlist"):
            data.setlist("dataset_files", dataset_files)
        elif dataset_files:
            data["dataset_files"] = dataset_files

        serializer = RoomCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        room = create_room(creator=request.user, **serializer.validated_data)
        return Response(
            RoomSerializer(room, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class RoomDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_id: int):
        room = get_visible_room(room_id=room_id, user=request.user)
        serializer = RoomSerializer(room, context={"request": request})
        return Response(serializer.data)


class RoomDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_id: int):
        room = get_visible_room(room_id=room_id, user=request.user)
        return Response(build_room_dashboard(room=room, actor=request.user))


class RoomInviteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_id: int):
        room = get_room_for_owner(room_id=room_id, owner=request.user)
        serializer = InviteAnnotatorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = invite_user_to_room(
            room=room,
            inviter=request.user,
            invited_user_id=serializer.validated_data["annotator_id"],
        )
        return Response(
            RoomMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )


class MyRoomListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rooms = list_member_rooms(user=request.user)
        serializer = RoomSerializer(rooms, many=True, context={"request": request})
        return Response(serializer.data)


class RoomAccessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RoomAccessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        room = get_room_by_id(room_id=serializer.validated_data["room_id"])
        password = serializer.validated_data.get("password", "")

        if room.created_by_id != request.user.id:
            membership = join_room(room=room, annotator=request.user, password=password)
            return Response(
                {
                    "room": RoomSerializer(room, context={"request": request}).data,
                    "membership": RoomMembershipSerializer(membership).data,
                    "redirect_url": f"/rooms/{room.id}/",
                }
            )

        return Response(
            {
                "room": RoomSerializer(room, context={"request": request}).data,
                "redirect_url": f"/rooms/{room.id}/",
            }
        )


class RoomJoinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_id: int):
        room = get_visible_room(room_id=room_id, user=request.user)
        serializer = RoomJoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = join_room(room=room, annotator=request.user, password=serializer.validated_data.get("password"))
        return Response(RoomMembershipSerializer(membership).data)


class RoomExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_id: int):
        room = get_room_for_owner(room_id=room_id, owner=request.user)
        export_format = request.query_params.get("export_format") or request.query_params.get(
            "format",
            "native_json",
        )
        artifact = export_room_annotations(
            room=room,
            export_format=export_format,
            base_url=request.build_absolute_uri("/").rstrip("/"),
        )
        response = HttpResponse(artifact.content, content_type=artifact.content_type)
        response["Content-Disposition"] = f'attachment; filename="{artifact.filename}"'
        return response
