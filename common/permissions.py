from rest_framework.permissions import BasePermission

from apps.users.models import User


class IsCustomer(BasePermission):
    message = "Customer role is required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.CUSTOMER)


class IsAnnotator(BasePermission):
    message = "Annotator role is required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.ANNOTATOR)
