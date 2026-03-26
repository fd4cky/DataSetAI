from django.urls import path

from apps.rooms.api.v1.views import (
    MyRoomListView,
    RoomDetailView,
    RoomInviteView,
    RoomJoinView,
    RoomListCreateView,
)


urlpatterns = [
    path("rooms/", RoomListCreateView.as_view(), name="room-list-create"),
    path("rooms/<int:room_id>/", RoomDetailView.as_view(), name="room-detail"),
    path("rooms/<int:room_id>/invite/", RoomInviteView.as_view(), name="room-invite"),
    path("me/rooms/", MyRoomListView.as_view(), name="my-rooms"),
    path("rooms/<int:room_id>/join/", RoomJoinView.as_view(), name="room-join"),
]
