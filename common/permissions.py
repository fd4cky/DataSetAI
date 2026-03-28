from rest_framework.permissions import BasePermission


class IsRoomOwner(BasePermission):
    """Object-level permission for endpoints that operate on a room owner scope."""

    message = "Only the room owner can perform this action."

    def has_object_permission(self, request, view, obj):
        return bool(request.user and request.user.is_authenticated and getattr(obj, "created_by_id", None) == request.user.id)
