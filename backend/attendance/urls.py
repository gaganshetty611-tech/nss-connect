from django.urls import path

from . import views

urlpatterns = [
    path("events/<int:pk>/qr/", views.event_qr, name="event-qr"),
    path("events/<int:pk>/attendance/", views.event_attendance, name="event-attendance"),
    path("events/<int:pk>/attendance/mark-absent/", views.mark_absent, name="event-mark-absent"),
    path("events/<int:pk>/feedback/", views.event_feedback, name="event-feedback"),
    path("attendance/", views.attendance_list, name="attendance-list"),
    path("attendance/check-in/", views.check_in, name="attendance-check-in"),
    path("attendance/check-out/", views.check_out, name="attendance-check-out"),
    path("attendance/scan-status/", views.scan_status, name="attendance-scan-status"),
]
