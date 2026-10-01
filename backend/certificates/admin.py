from django.contrib import admin

from .models import Certificate


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ["certificate_id", "volunteer", "event", "hours", "issued_at", "revoked"]
    list_filter = ["revoked", "event__category", "issued_at"]
    search_fields = ["certificate_id", "volunteer__email", "volunteer__first_name", "event__title"]
    ordering = ["-issued_at"]
    readonly_fields = ["certificate_id", "verification_token", "issued_at", "verify_url"]
    raw_id_fields = ["volunteer", "event"]
