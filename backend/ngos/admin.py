from django.contrib import admin
from django.utils import timezone

from nss_units.models import VerificationStatus

from .models import NGO, VerificationDocument


class VerificationDocumentInline(admin.TabularInline):
    model = VerificationDocument
    extra = 0
    readonly_fields = ["uploaded_at", "reviewed_at", "reviewed_by", "original_filename"]


@admin.register(NGO)
class NGOAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "location", "verification_status", "verified", "created_at"]
    list_filter = ["verification_status", "verified", "created_at"]
    search_fields = ["name", "email", "location", "owner__email", "registration_number"]
    ordering = ["name"]
    readonly_fields = ["verified", "verified_at", "created_at", "updated_at"]
    raw_id_fields = ["owner"]
    inlines = [VerificationDocumentInline]
    actions = ["verify_ngos", "reject_ngos", "suspend_ngos"]

    def _set(self, queryset, status):
        for ngo in queryset:
            ngo.verification_status = status
            ngo.verified_at = timezone.now() if status == VerificationStatus.VERIFIED else None
            ngo.save()

    @admin.action(description="Verify selected NGOs")
    def verify_ngos(self, request, queryset):
        self._set(queryset, VerificationStatus.VERIFIED)

    @admin.action(description="Reject selected NGOs")
    def reject_ngos(self, request, queryset):
        self._set(queryset, VerificationStatus.REJECTED)

    @admin.action(description="Suspend selected NGOs")
    def suspend_ngos(self, request, queryset):
        self._set(queryset, VerificationStatus.SUSPENDED)


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = ["ngo", "document_type", "status", "uploaded_at", "reviewed_by", "reviewed_at"]
    list_filter = ["status", "document_type"]
    search_fields = ["ngo__name", "original_filename"]
    ordering = ["-uploaded_at"]
    readonly_fields = ["uploaded_at", "reviewed_at", "original_filename"]
