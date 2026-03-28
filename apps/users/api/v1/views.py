from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import User
from apps.users.selectors import build_user_profile


class MyProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(build_user_profile(user=request.user))


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id: int):
        user = get_object_or_404(User, id=user_id)
        return Response(build_user_profile(user=user))
