from django.contrib import admin

from .models import AIRecommendation


@admin.register(AIRecommendation)
class AIRecommendationAdmin(admin.ModelAdmin):
    list_display = ["event", "nss_unit", "match_score", "distance_km", "available_volunteers", "provider", "created_at"]
    list_filter = ["provider", "event__category"]
    search_fields = ["event__title", "nss_unit__college__name"]
    ordering = ["event", "-match_score"]
    readonly_fields = [f.name for f in AIRecommendation._meta.fields]
