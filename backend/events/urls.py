from django.urls import path, re_path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter(trailing_slash=True)
router.register("events", views.EventViewSet, basename="event")
router.register("emergency-requests", views.EmergencyRequestViewSet, basename="emergency-request")

urlpatterns = [
    path("applications/", views.application_list, name="application-list"),
    path("applications/<int:pk>/approve/", views.approve_application, name="application-approve"),
    path("applications/<int:pk>/reject/", views.reject_application, name="application-reject"),
    path("applications/<int:pk>/waitlist/", views.waitlist_application, name="application-waitlist"),
    re_path(r"^group-applications/(?P<pk>\d+)/(?P<decision>accept|reject)/$", views.decide_group_application, name="group-application-decide"),
    path("photos/<int:pk>/", views.delete_photo, name="photo-delete"),
] + router.urls
