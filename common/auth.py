from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class HeaderUserAuthentication(BaseAuthentication):
    header_name = "HTTP_X_USER_ID"

    def authenticate(self, request):
        raw_user_id = request.META.get(self.header_name)
        if not raw_user_id:
            return None

        try:
            user_id = int(raw_user_id)
        except (TypeError, ValueError) as exc:
            raise AuthenticationFailed("Invalid X-User-Id header.") from exc

        user_model = get_user_model()
        try:
            user = user_model.objects.get(pk=user_id, is_active=True)
        except user_model.DoesNotExist as exc:
            raise AuthenticationFailed("User not found for X-User-Id.") from exc

        return (user, None)

    def authenticate_header(self, request):
        return "X-User-Id"
