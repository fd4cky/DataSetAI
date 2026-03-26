from django.conf import settings
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import include, path
from apps.ui.views import HealthView, ServiceInfoView


urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("service/", ServiceInfoView.as_view(), name="service-info"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.api.v1.urls")),
    path("", include("apps.ui.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


handler404 = "common.error_views.api_404_view"
handler500 = "common.error_views.api_500_view"
