from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from core.permissions import can_manage_event
from events.models import Event, EventCategory

from .models import AIRecommendation
from .providers import DISCLAIMER, get_provider


class RecommendationSerializer(serializers.ModelSerializer):
    nss_unit_id = serializers.IntegerField(source="nss_unit.id")
    nss_unit_name = serializers.CharField(source="nss_unit.__str__")
    college = serializers.CharField(source="nss_unit.college.name")
    volunteer_count = serializers.IntegerField(source="nss_unit.volunteer_count")
    latitude = serializers.DecimalField(source="nss_unit.latitude", max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(source="nss_unit.longitude", max_digits=9, decimal_places=6)

    class Meta:
        model = AIRecommendation
        fields = [
            "id", "nss_unit_id", "nss_unit_name", "college", "volunteer_count", "latitude", "longitude",
            "match_score", "distance_score", "skill_score", "availability_score", "attendance_score", "interest_score",
            "distance_km", "available_volunteers", "reasons", "weights", "provider", "created_at",
        ]


def _get_managed_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not can_manage_event(request.user, event):
        raise PermissionDenied("Only the event organizer or administrators can use this tool.")
    return event


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def event_recommendations(request, pk):
    """Ranked NSS units for an event. Recomputed on every call (?refresh=0 returns the stored ranking)."""
    event = _get_managed_event(request, pk)
    stored = AIRecommendation.objects.filter(event=event).select_related("nss_unit", "nss_unit__college")
    if request.query_params.get("refresh") == "0" and stored.exists():
        recs = stored
    else:
        provider = get_provider()
        results = provider.recommend_units(event, limit=int(request.query_params.get("limit", 10)))
        with transaction.atomic():
            AIRecommendation.objects.filter(event=event).exclude(nss_unit__in=[r["nss_unit"] for r in results]).delete()
            for r in results:
                unit = r.pop("nss_unit")
                AIRecommendation.objects.update_or_create(event=event, nss_unit=unit, defaults={**r, "provider": provider.name})
        recs = AIRecommendation.objects.filter(event=event).select_related("nss_unit", "nss_unit__college")
    return Response({
        "event": event.id,
        "results": RecommendationSerializer(recs.order_by("-match_score"), many=True).data,
        "disclaimer": DISCLAIMER,
        "method": "Weighted score = Σ(weight × component). Components are 0–100.",
    })


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def categorize(request):
    title = str(request.data.get("title", ""))[:200]
    description = str(request.data.get("description", ""))[:5000]
    if not (title or description):
        return Response({"detail": "Provide a title or description."}, status=400)
    return Response(get_provider().categorize_event(title, description))


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def suggest_datetime(request):
    category = request.query_params.get("category") or None
    if category and category not in EventCategory.values:
        return Response({"detail": "Unknown category."}, status=400)
    return Response(get_provider().suggest_datetime(category))


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def turnout_estimate(request, pk):
    event = _get_managed_event(request, pk)
    return Response(get_provider().estimate_turnout(event))


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def generate_summary(request, pk):
    event = _get_managed_event(request, pk)
    if "organizer_notes" in request.data:
        event.organizer_notes = str(request.data["organizer_notes"])[:5000]
    result = get_provider().summarize_event(event)
    event.summary = result["summary"]
    event.save(update_fields=["summary", "organizer_notes", "updated_at"])
    return Response(result)
