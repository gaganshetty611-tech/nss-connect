from django.contrib import admin

from .models import College, NSSUnit, University, VerificationStatus


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ["name", "short_name", "city", "created_at"]
    search_fields = ["name", "short_name", "city"]
    ordering = ["name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "university", "city"]
    list_filter = ["university"]
    search_fields = ["name", "code", "city"]
    ordering = ["name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(NSSUnit)
class NSSUnitAdmin(admin.ModelAdmin):
    list_display = ["__str__", "university", "coordinator", "volunteer_count", "verification_status", "created_at"]
    list_filter = ["verification_status", "university", "college"]
    search_fields = ["college__name", "unit_number", "email", "coordinator__email"]
    ordering = ["college__name", "unit_number"]
    readonly_fields = ["verified", "volunteer_count", "created_at", "updated_at"]
    raw_id_fields = ["coordinator"]
    actions = ["verify_units", "reject_units"]

    @admin.action(description="Verify selected NSS units")
    def verify_units(self, request, queryset):
        for unit in queryset:
            unit.verification_status = VerificationStatus.VERIFIED
            unit.save()

    @admin.action(description="Reject selected NSS units")
    def reject_units(self, request, queryset):
        for unit in queryset:
            unit.verification_status = VerificationStatus.REJECTED
            unit.save()
