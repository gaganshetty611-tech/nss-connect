from django.urls import path

from . import views

urlpatterns = [
    path("notifications/", views.NotificationListView.as_view(), name="notification-list"),
    path("notifications/unread-count/", views.unread_count, name="notification-unread-count"),
    path("notifications/read-all/", views.mark_all_read, name="notification-read-all"),
    path("notifications/<int:pk>/read/", views.mark_read, name="notification-read"),
]
