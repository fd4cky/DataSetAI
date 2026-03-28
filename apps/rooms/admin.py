from django.contrib import admin

from apps.rooms.models import Room, RoomMembership, RoomPin


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_by", "created_at")
    search_fields = ("title", "description", "created_by__username")


@admin.register(RoomMembership)
class RoomMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "user", "status", "invited_by", "joined_at")
    list_filter = ("status",)
    search_fields = ("room__title", "user__username", "invited_by__username")


@admin.register(RoomPin)
class RoomPinAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "user", "created_at")
    search_fields = ("room__title", "user__username")
