from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from accounts.models import Role
from core.pagination import StandardPagination
from core.permissions import IsPlatformAdmin, can_manage_event, has_role, is_admin, scope_q

from .models import Certificate
from .services import generate_certificate


class CertificateSerializer(serializers.ModelSerializer):
    volunteer_name = serializers.CharField(source="volunteer.display_name", read_only=True)
    event_title = serializers.CharField(source="event.title", read_only=True)
    event_date = serializers.DateField(source="event.date", read_only=True)
    event_category = serializers.CharField(source="event.category", read_only=True)
    organizer = serializers.CharField(source="event.organizer_display", read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            "id", "certificate_id", "volunteer", "volunteer_name", "event", "event_title", "event_date", "event_category",
            "organizer", "hours", "issued_at", "verify_url", "download_url", "revoked",
        ]

    def get_download_url(self, obj):
        return f"/api/certificates/{obj.id}/download/"


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def certificate_list(request):
    user = request.user
    qs = Certificate.objects.select_related("volunteer", "event", "event__ngo", "event__nss_unit", "event__organizer")
    if is_admin(user):
        qs = qs.filter(scope_q(user, "event__university_id", "event__college_id", include_unscoped=True))
        if request.query_params.get("mine") in ("1", "true"):
            qs = qs.filter(volunteer=user)
    elif has_role(user, Role.VOLUNTEER):
        qs = qs.filter(volunteer=user)
    else:
        qs = qs.filter(event__organizer=user)
    p = request.query_params
    if p.get("event"):
        qs = qs.filter(event_id=p["event"])
    if p.get("search"):
        s = p["search"]
        qs = qs.filter(Q(certificate_id__icontains=s) | Q(volunteer__email__icontains=s) | Q(event__title__icontains=s))
    paginator = StandardPagination()
    page = paginator.paginate_queryset(qs.order_by("-issued_at"), request)
    return paginator.get_paginated_response(CertificateSerializer(page, many=True).data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def certificate_download(request, pk):
    cert = get_object_or_404(Certificate.objects.select_related("event"), pk=pk)
    if not (cert.volunteer_id == request.user.id or can_manage_event(request.user, cert.event)):
        raise PermissionDenied("You cannot download this certificate.")
    if not cert.pdf_file:
        cert, _ = generate_certificate(cert.volunteer, cert.event, cert.hours, request=request)
    if not cert.pdf_file:
        raise Http404
    return FileResponse(cert.pdf_file.open("rb"), as_attachment=True, filename=f"{cert.certificate_id}.pdf", content_type="application/pdf")


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def certificate_verify(request, certificate_id):
    """Public verification. Returns only what is printed on the certificate itself."""
    cert = Certificate.objects.select_related("volunteer", "event", "event__ngo", "event__nss_unit").filter(
        certificate_id__iexact=certificate_id.strip()
    ).first()
    if cert is None:
        return Response({"valid": False, "certificate_id": certificate_id, "detail": "No certificate with this ID exists."}, status=404)
    if cert.revoked:
        return Response({"valid": False, "certificate_id": cert.certificate_id, "detail": "This certificate has been revoked."})
    return Response({
        "valid": True,
        "certificate_id": cert.certificate_id,
        "volunteer_name": cert.volunteer.display_name,
        "event": cert.event.title,
        "category": cert.event.get_category_display(),
        "organizer": cert.event.organizer_display,
        "date": cert.event.date,
        "hours": float(cert.hours),
        "issued_at": cert.issued_at,
    })


@api_view(["POST"])
@permission_classes([IsPlatformAdmin])
def certificate_revoke(request, pk):
    cert = get_object_or_404(Certificate, pk=pk)
    if not can_manage_event(request.user, cert.event):
        raise PermissionDenied()
    cert.revoked = request.data.get("revoked", True) in (True, "true", "1", 1)
    cert.save(update_fields=["revoked"])
    return Response(CertificateSerializer(cert).data)
