from django.urls import path

from apps.rooms.api.v1.views import (
    MyRoomListView,
    RoomAccessView,
    RoomDashboardView,
    RoomDetailView,
    RoomInviteView,
    RoomJoinView,
    RoomListCreateView,
    RoomPinView,
    RoomExportView,
)


urlpatterns = [
    path("rooms/", RoomListCreateView.as_view(), name="room-list-create"),
    path("rooms/access/", RoomAccessView.as_view(), name="room-access"),
    path("rooms/<int:room_id>/", RoomDetailView.as_view(), name="room-detail"),
    path("rooms/<int:room_id>/dashboard/", RoomDashboardView.as_view(), name="room-dashboard"),
    path("rooms/<int:room_id>/invite/", RoomInviteView.as_view(), name="room-invite"),
    path("rooms/<int:room_id>/pin/", RoomPinView.as_view(), name="room-pin"),
    path("rooms/<int:room_id>/export/", RoomExportView.as_view(), name="room-export"),
    path("me/rooms/", MyRoomListView.as_view(), name="my-rooms"),
    path("rooms/<int:room_id>/join/", RoomJoinView.as_view(), name="room-join"),
]
