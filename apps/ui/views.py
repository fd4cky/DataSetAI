from django.db import DatabaseError
from django.db.utils import OperationalError, ProgrammingError
from django.views.generic import TemplateView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.labeling.models import Task
from apps.rooms.models import Room
from apps.users.models import User


class AppView(TemplateView):
    template_name = "ui/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        users = []
        stats = {
            "users": 0,
            "rooms": 0,
            "tasks": 0,
        }

        try:
            users_qs = User.objects.order_by("id").values("id", "username", "role")
            users = list(users_qs)
            stats = {
                "users": len(users),
                "rooms": Room.objects.count(),
                "tasks": Task.objects.count(),
            }
        except (OperationalError, ProgrammingError, DatabaseError):
            pass

        context["mock_users"] = users
        context["stats"] = stats
        return context


class ServiceInfoView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response(
            {
                "service": "DataSetAI Backend MVP",
                "status": "ok",
                "docs_hint": {
                    "ui": "/",
                    "admin": "/admin/",
                    "api_v1": "/api/v1/",
                    "health": "/health/",
                },
            }
        )


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok"})
