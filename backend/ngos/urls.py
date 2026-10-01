from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import NGOViewSet, download_document, review_document

router = DefaultRouter(trailing_slash=True)
router.register("ngos", NGOViewSet, basename="ngo")

urlpatterns = router.urls + [
    path("documents/<int:pk>/review/", review_document, name="document-review"),
    path("documents/<int:pk>/download/", download_document, name="document-download"),
]
