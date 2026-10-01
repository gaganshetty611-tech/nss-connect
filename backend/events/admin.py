from django.contrib import admin

from .models import (
    EmergencyVolunteerRequest,
    Event,
    EventApplication,
    EventPhoto,
    EventSkill,
    EventStatus,
    GroupApplication,
)


@admin.register(EventSkill)
class EventSkillAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    ordering = ["name"]


class EventPhotoInline(admin.TabularInline):
    model = EventPhoto
    extra = 0
    readonly_fields = ["created_at", "uploaded_by"]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "theme", "status", "date", "start_time", "organizer", "ngo", "nss_unit", "maximum_volunteers"]
    list_filter = ["status", "category", "theme", "date", "university"]
    search_fields = ["title", "description", "location", "organizer__email", "ngo__name"]
    ordering = ["-date"]
    date_hierarchy = "date"
    readonly_fields = ["created_at", "updated_at", "approved_by"]
    raw_id_fields = ["organizer", "ngo", "nss_unit", "college", "university"]
    filter_horizontal = ["required_skills"]
    inlines = [EventPhotoInline]
    actions = ["approve_events", "reject_events"]

    @admin.action(description="Approve selected events")
    def approve_events(self, request, queryset):
        queryset.filter(status=EventStatus.PENDING).update(status=EventStatus.APPROVED, approved_by=request.user)

    @admin.action(description="Reject selected events")
    def reject_events(self, request, queryset):
        queryset.filter(status=EventStatus.PENDING).update(status=EventStatus.REJECTED)


@admin.register(EventApplication)
class EventApplicationAdmin(admin.ModelAdmin):
    list_display = ["volunteer", "event", "status", "college", "nss_unit", "application_date"]
    list_filter = ["status", "event__category", "college"]
    search_fields = ["volunteer__email", "volunteer__first_name", "event__title", "email"]
    ordering = ["-application_date"]
    readonly_fields = ["application_date", "created_at", "updated_at", "decided_at"]
    raw_id_fields = ["volunteer", "event", "college", "nss_unit", "decided_by"]


@admin.register(GroupApplication)
class GroupApplicationAdmin(admin.ModelAdmin):
    list_display = ["nss_unit", "event", "requested_volunteer_count", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["nss_unit__college__name", "event__title"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at", "decided_at"]


@admin.register(EventPhoto)
class EventPhotoAdmin(admin.ModelAdmin):
    list_display = ["event", "caption", "uploaded_by", "created_at"]
    search_fields = ["event__title", "caption"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at"]


@admin.register(EmergencyVolunteerRequest)
class EmergencyVolunteerRequestAdmin(admin.ModelAdmin):
    list_display = ["title", "priority", "required_volunteers", "location", "notified_count", "created_at", "expires_at"]
    list_filter = ["priority"]
    search_fields = ["title", "description", "location"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "notified_count"]
