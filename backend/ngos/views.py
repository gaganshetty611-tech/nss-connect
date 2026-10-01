from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from accounts.models import Role
from core.permissions import IsPlatformAdmin, has_role, is_admin, scope_q
from events.models import EventStatus
from notifications.models import NotificationType
from notifications.services import notify
from nss_units.models import VerificationStatus

from .models import NGO, VerificationDocument
from .serializers import NGOSerializer, VerificationDocumentSerializer


def can_review_ngos(user):
    """NGOs are not tied to a college, so only university and super admins verify them."""
    return has_role(user, Role.SUPER_ADMIN, Role.UNIVERSITY_ADMIN)


class NGOViewSet(viewsets.ModelViewSet):
    serializer_class = NGOSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        today = timezone.localdate()
        qs = NGO.objects.select_related("owner").annotate(
            event_count=Count("events", filter=Q(events__status__in=[EventStatus.APPROVED, EventStatus.ONGOING, EventStatus.COMPLETED]), distinct=True),
            upcoming_event_count=Count("events", filter=Q(events__status=EventStatus.APPROVED, events__date__gte=today), distinct=True),
        )
        visible = Q(verification_status=VerificationStatus.VERIFIED)
        if user.is_authenticated:
            visible |= Q(owner=user)
            if is_admin(user):
                visible = Q()
        qs = qs.filter(visible)
        p = self.request.query_params
        if p.get("status"):
            qs = qs.filter(verification_status=p["status"])
        if p.get("mine") in ("1", "true") and user.is_authenticated:
            qs = qs.filter(owner=user)
        if p.get("focus_area"):
            # JSON list containment works on PostgreSQL; icontains on the serialised JSON works everywhere.
            qs = qs.filter(focus_areas__icontains=p["focus_area"])
        if p.get("search"):
            s = p["search"]
            qs = qs.filter(Q(name__icontains=s) | Q(description__icontains=s) | Q(location__icontains=s))
        return qs.order_by("name")

    def perform_create(self, serializer):
        user = self.request.user
        if not (has_role(user, Role.NGO_ORGANIZER) or is_admin(user)):
            raise PermissionDenied("Only NGO organizer accounts can register an NGO.")
        if has_role(user, Role.NGO_ORGANIZER) and NGO.objects.filter(owner=user).exists():
            raise ValidationError({"detail": "You have already registered an NGO."})
        ngo = serializer.save(owner=user if has_role(user, Role.NGO_ORGANIZER) else None)
        admins = _ngo_reviewers()
        for admin in admins:
            notify(admin, NotificationType.NGO_STATUS_CHANGED, "New NGO awaiting verification",
                   f"{ngo.name} registered and is waiting for document review.", link="/admin/ngos")

    def perform_update(self, serializer):
        ngo = serializer.instance
        user = self.request.user
        if not (ngo.owner_id == user.id or can_review_ngos(user)):
            raise PermissionDenied("You cannot edit this NGO.")
        serializer.save()

    def perform_destroy(self, instance):
        if not can_review_ngos(self.request.user):
            raise PermissionDenied("Only administrators can delete NGOs.")
        instance.delete()

    def _set_status(self, request, new_status):
        if not can_review_ngos(request.user):
            raise PermissionDenied("Only university or super admins can review NGOs.")
        ngo = get_object_or_404(NGO, pk=self.kwargs["pk"])
        ngo.verification_status = new_status
        ngo.review_note = request.data.get("note", "")
        ngo.verified_at = timezone.now() if new_status == VerificationStatus.VERIFIED else None
        ngo.save()
        if ngo.owner:
            if new_status == VerificationStatus.VERIFIED:
                notify(ngo.owner, NotificationType.NGO_VERIFIED, "Your NGO is verified",
                       f"{ngo.name} is now verified. You can create drives on NSS Connect.", link=f"/ngos/{ngo.id}", email=True)
            else:
                notify(ngo.owner, NotificationType.NGO_STATUS_CHANGED, f"NGO {new_status.lower()}",
                       f"{ngo.name} was marked {new_status.lower()}. {ngo.review_note}".strip(), link=f"/ngos/{ngo.id}", email=True)
        return Response(NGOSerializer(ngo, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        return self._set_status(request, VerificationStatus.VERIFIED)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._set_status(request, VerificationStatus.REJECTED)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        return self._set_status(request, VerificationStatus.SUSPENDED)

    @action(detail=True, methods=["get", "post"], parser_classes=[MultiPartParser, FormParser])
    def documents(self, request, pk=None):
        ngo = get_object_or_404(NGO, pk=pk)
        if not (ngo.owner_id == request.user.id or is_admin(request.user)):
            raise PermissionDenied("Only the NGO owner or administrators can access verification documents.")
        if request.method == "GET":
            docs = ngo.documents.select_related("reviewed_by")
            return Response(VerificationDocumentSerializer(docs, many=True, context={"request": request}).data)
        if ngo.owner_id != request.user.id:
            raise PermissionDenied("Only the NGO owner can upload documents.")
        serializer = VerificationDocumentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        upload = request.FILES.get("file")
        doc = serializer.save(ngo=ngo, original_filename=(upload.name if upload else "")[:255])
        if ngo.verification_status == VerificationStatus.REJECTED:
            ngo.verification_status = VerificationStatus.PENDING
            ngo.save()
        return Response(VerificationDocumentSerializer(doc, context={"request": request}).data, status=status.HTTP_201_CREATED)


def _ngo_reviewers():
    from accounts.models import User

    return User.objects.filter(is_active=True, role__in=[Role.SUPER_ADMIN, Role.UNIVERSITY_ADMIN])


@api_view(["POST"])
@permission_classes([IsPlatformAdmin])
def review_document(request, pk):
    if not can_review_ngos(request.user):
        raise PermissionDenied("Only university or super admins can review NGO documents.")
    doc = get_object_or_404(VerificationDocument, pk=pk)
    new_status = request.data.get("status")
    if new_status not in (VerificationDocument.Status.APPROVED, VerificationDocument.Status.REJECTED):
        raise ValidationError({"status": "Must be APPROVED or REJECTED."})
    doc.status = new_status
    doc.review_note = request.data.get("note", "")
    doc.reviewed_at = timezone.now()
    doc.reviewed_by = request.user
    doc.save()
    return Response(VerificationDocumentSerializer(doc, context={"request": request}).data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def download_document(request, pk):
    """Documents are private: served only to the owner and admins, never via public /media/ listing."""
    doc = get_object_or_404(VerificationDocument, pk=pk)
    if not (doc.ngo.owner_id == request.user.id or is_admin(request.user)):
        raise PermissionDenied()
    if not doc.file:
        raise Http404
    return FileResponse(doc.file.open("rb"), as_attachment=True, filename=doc.original_filename or doc.file.name.rsplit("/", 1)[-1])
