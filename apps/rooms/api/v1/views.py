from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rooms.api.v1.serializers import (
    InviteAnnotatorSerializer,
    RoomCreateSerializer,
    RoomMembershipSerializer,
    RoomSerializer,
)
from apps.rooms.selectors import get_room_for_owner, get_visible_room, list_customer_rooms, list_user_rooms
from apps.rooms.services import create_room, invite_user_to_room, join_room
from apps.users.models import User
from common.exceptions import AccessDeniedError
from common.permissions import IsAnnotator, IsCustomer


class RoomListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != User.Role.CUSTOMER:
            raise AccessDeniedError("Only customers can list owned rooms here.")
        rooms = list_customer_rooms(customer=request.user)
        serializer = RoomSerializer(rooms, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        self.check_permissions(request)
        if request.user.role != User.Role.CUSTOMER:
            raise AccessDeniedError("Only customers can create rooms.")
        serializer = RoomCreateSerializer(data=request.data)
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


class RoomInviteView(APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

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
    permission_classes = [IsAuthenticated, IsAnnotator]

    def get(self, request):
        rooms = list_user_rooms(user=request.user)
        serializer = RoomSerializer(rooms, many=True, context={"request": request})
        return Response(serializer.data)


class RoomJoinView(APIView):
    permission_classes = [IsAuthenticated, IsAnnotator]

    def post(self, request, room_id: int):
        room = get_visible_room(room_id=room_id, user=request.user)
        membership = join_room(room=room, annotator=request.user)
        return Response(RoomMembershipSerializer(membership).data)
