from django.urls import include, path


urlpatterns = [
    path("", include("apps.rooms.api.v1.urls")),
    path("", include("apps.labeling.api.v1.urls")),
]
