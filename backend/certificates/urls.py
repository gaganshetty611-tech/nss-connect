from django.urls import path

from . import views

urlpatterns = [
    path("certificates/", views.certificate_list, name="certificate-list"),
    path("certificates/<int:pk>/download/", views.certificate_download, name="certificate-download"),
    path("certificates/<int:pk>/revoke/", views.certificate_revoke, name="certificate-revoke"),
    path("certificates/<str:certificate_id>/verify/", views.certificate_verify, name="certificate-verify"),
]
