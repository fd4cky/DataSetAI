from django.contrib.auth import login
from django.contrib.auth.views import LogoutView
from django.db import DatabaseError
from django.db.utils import OperationalError, ProgrammingError
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.labeling.models import Task
from apps.rooms.models import Room
from apps.ui.forms import LoginForm, RegistrationForm
from apps.users.models import User


class UiContextMixin:
    active_page = "home"
    page_key = "home"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stats = {
            "users": 0,
            "rooms": 0,
            "tasks": 0,
        }

        try:
            stats = {
                "users": User.objects.count(),
                "rooms": Room.objects.count(),
                "tasks": Task.objects.count(),
            }
        except (OperationalError, ProgrammingError, DatabaseError):
            pass

        context["stats"] = stats
        context["active_page"] = self.active_page
        context["page_key"] = self.page_key
        context["room_id"] = kwargs.get("room_id")
        context["auth_user_data"] = (
            {
                "id": self.request.user.id,
                "username": self.request.user.username,
            }
            if self.request.user.is_authenticated
            else None
        )
        return context


class LandingView(UiContextMixin, TemplateView):
    template_name = "ui/landing.html"
    active_page = "home"
    page_key = "home"


class RoomsView(LoginRequiredMixin, UiContextMixin, TemplateView):
    template_name = "ui/rooms.html"
    active_page = "rooms"
    page_key = "rooms"


class ProfileView(LoginRequiredMixin, UiContextMixin, TemplateView):
    template_name = "ui/profile.html"
    active_page = "profile"
    page_key = "profile"


class RoomCreateView(LoginRequiredMixin, UiContextMixin, TemplateView):
    template_name = "ui/room_create.html"
    active_page = "rooms"
    page_key = "room-create"


class RoomWorkspaceView(LoginRequiredMixin, UiContextMixin, TemplateView):
    template_name = "ui/room_detail.html"
    active_page = "rooms"
    page_key = "room-detail"


class RoomWorkView(LoginRequiredMixin, UiContextMixin, TemplateView):
    template_name = "ui/room_work.html"
    active_page = "rooms"
    page_key = "room-work"


class AuthContextMixin(UiContextMixin):
    active_page = "auth"


class LoginPageView(AuthContextMixin, FormView):
    template_name = "ui/auth/login.html"
    form_class = LoginForm
    success_url = "/rooms/"
    page_key = "auth-login"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        login(self.request, form.get_user())
        return super().form_valid(form)


class RegisterPageView(AuthContextMixin, FormView):
    template_name = "ui/auth/register.html"
    form_class = RegistrationForm
    success_url = "/rooms/"
    page_key = "auth-register"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


class UserLogoutView(LogoutView):
    next_page = "/"


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
