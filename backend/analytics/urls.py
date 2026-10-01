from django.urls import path

from . import views

urlpatterns = [
    path("analytics/", views.analytics_view, name="analytics"),
    path("dashboard/volunteer/", views.volunteer_dashboard, name="dashboard-volunteer"),
    path("dashboard/organizer/", views.organizer_dashboard, name="dashboard-organizer"),
    path("dashboard/admin/", views.admin_dashboard, name="dashboard-admin"),
    path("reports/", views.report_export, name="report-export"),
    path("reports/types/", views.report_types, name="report-types"),
]
