"""
URL layout
  /api/...            REST API (JWT)
  /django-admin/      Django admin (the React app owns /admin/*)
  /media/...          uploaded public media (profile photos, event images, gallery)
  /*                  built React app (frontend/dist) when present – single-URL deployment/tunnel
"""
from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, Http404, JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve

admin.site.site_header = "NSS Connect administration"
admin.site.site_title = "NSS Connect admin"
admin.site.index_title = "Platform management"

PRIVATE_MEDIA_PREFIXES = ("ngo_documents/", "certificates/")


def health(request):
    from django.db import connection

    with connection.cursor() as c:
        c.execute("SELECT 1")
    return JsonResponse({"status": "ok", "database": connection.vendor, "ai_provider": settings.AI_PROVIDER})


def public_media(request, path):
    # NGO documents and certificate PDFs are only served through authenticated API endpoints.
    if path.startswith(PRIVATE_MEDIA_PREFIXES) or ".." in path:
        raise Http404
    return serve(request, path, document_root=settings.MEDIA_ROOT)


def spa(request, path=""):
    dist = settings.FRONTEND_DIST
    candidate = (dist / path).resolve() if path else None
    if candidate and candidate.is_file() and str(candidate).startswith(str(dist.resolve())):
        return FileResponse(open(candidate, "rb"))
    index = dist / "index.html"
    if not index.exists():
        return JsonResponse(
            {"detail": "API server is running. Frontend build not found – run the Vite dev server or `npm run build`."},
            status=404,
        )
    return FileResponse(open(index, "rb"), content_type="text/html")


api_patterns = [
    path("health/", health),
    path("", include("accounts.urls")),
    path("", include("notifications.urls")),
    path("", include("nss_units.urls")),
    path("", include("ngos.urls")),
    path("", include("ai_matching.urls")),
    path("", include("attendance.urls")),
    path("", include("events.urls")),
    path("", include("certificates.urls")),
    path("", include("analytics.urls")),
]

urlpatterns = [
    path("api/", include(api_patterns)),
    path("django-admin/", admin.site.urls),
]

if settings.DEBUG or settings.SERVE_MEDIA:
    media_prefix = settings.MEDIA_URL.lstrip("/")
    urlpatterns += [re_path(rf"^{media_prefix}(?P<path>.*)$", public_media)]

urlpatterns += [re_path(r"^(?!api/|django-admin/|static/)(?P<path>.*)$", spa)]
