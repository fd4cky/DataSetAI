from django.http import JsonResponse
from django.views.defaults import page_not_found, server_error


def api_404_view(request, exception):
    if request.path.startswith("/api/"):
        return JsonResponse(
            {
                "detail": "API route not found.",
                "code": "api_not_found",
            },
            status=404,
        )
    return page_not_found(request, exception)


def api_500_view(request):
    if request.path.startswith("/api/"):
        return JsonResponse(
            {
                "detail": "Internal API error.",
                "code": "internal_error",
            },
            status=500,
        )
    return server_error(request)
