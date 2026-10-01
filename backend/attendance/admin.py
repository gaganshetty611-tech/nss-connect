from django.contrib import admin

from .models import Attendance, EventQR, Feedback, VolunteerHours


@admin.register(EventQR)
class EventQRAdmin(admin.ModelAdmin):
    list_display = ["event", "active", "expires_at", "created_by", "created_at"]
    list_filter = ["active"]
    search_fields = ["event__title"]
    ordering = ["-created_at"]
    readonly_fields = ["token", "created_at"]


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ["volunteer", "event", "status", "check_in", "check_out"]
    list_filter = ["status", "event__category"]
    search_fields = ["volunteer__email", "volunteer__first_name", "event__title"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["volunteer", "event", "application", "qr"]


@admin.register(VolunteerHours)
class VolunteerHoursAdmin(admin.ModelAdmin):
    list_display = ["volunteer", "event", "hours", "category", "verified", "created_at"]
    list_filter = ["category", "verified"]
    search_fields = ["volunteer__email", "event__title"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "verified_at"]
    raw_id_fields = ["volunteer", "event", "attendance"]


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ["volunteer", "event", "rating", "submitted_at"]
    list_filter = ["rating"]
    search_fields = ["volunteer__email", "event__title", "comments"]
    ordering = ["-submitted_at"]
    readonly_fields = ["submitted_at"]
