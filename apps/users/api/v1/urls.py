from django.urls import path

from apps.users.api.v1.views import MyProfileView, UserProfileView


urlpatterns = [
    path("me/profile/", MyProfileView.as_view(), name="my-profile"),
    path("users/<int:user_id>/profile/", UserProfileView.as_view(), name="user-profile"),
]
