import base64
import io
from datetime import timedelta

import qrcode
from django.conf import settings
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from accounts.models import Role
from core.pagination import StandardPagination
from core.permissions import can_manage_event, has_role, is_admin, scope_q
from core.utils import event_window, frontend_base_url
from events.models import ApplicationStatus, Event, EventStatus

from . import services
from .models import Attendance, EventQR, Feedback, VolunteerHours


class AttendanceSerializer(serializers.ModelSerializer):
    volunteer_name = serializers.CharField(source="volunteer.display_name", read_only=True)
    volunteer_email = serializers.CharField(source="volunteer.email", read_only=True)
    event_title = serializers.CharField(source="event.title", read_only=True)
    event_date = serializers.DateField(source="event.date", read_only=True)
    event_category = serializers.CharField(source="event.category", read_only=True)
    hours = serializers.SerializerMethodField()
    hours_verified = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = [
            "id", "volunteer", "volunteer_name", "volunteer_email", "event", "event_title", "event_date", "event_category",
            "check_in", "check_out", "status", "hours", "hours_verified", "created_at", "updated_at",
        ]

    def get_hours(self, obj):
        rec = getattr(obj, "hours_record", None)
        return float(rec.hours) if rec else None

    def get_hours_verified(self, obj):
        rec = getattr(obj, "hours_record", None)
        return bool(rec and rec.verified)


class FeedbackSerializer(serializers.ModelSerializer):
    volunteer_name = serializers.CharField(source="volunteer.display_name", read_only=True)

    class Meta:
        model = Feedback
        fields = ["id", "event", "volunteer", "volunteer_name", "rating", "comments", "submitted_at"]
        read_only_fields = ["event", "volunteer", "submitted_at"]


def _qr_payload(qr, request):
    url = f"{frontend_base_url(request)}/attendance/check-in/{qr.token}"
    img = qrcode.make(url, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return {
        "id": qr.id,
        "event": qr.event_id,
        "token": qr.token,
        "check_in_url": url,
        "qr_image": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(),
        "expires_at": qr.expires_at,
        "active": qr.active,
        "created_at": qr.created_at,
    }


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def event_qr(request, pk):
    """POST generates a fresh QR (deactivating earlier ones). GET returns the current active QR.
    The QR encodes only a random token URL – no personal data."""
    event = get_object_or_404(Event, pk=pk)
    if not can_manage_event(request.user, event):
        raise PermissionDenied("Only the organizer or administrators can manage attendance QR codes.")
    if request.method == "GET":
        qr = event.qr_codes.filter(active=True, expires_at__gt=timezone.now()).first()
        if not qr:
            return Response({"detail": "No active QR code. Generate one."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_qr_payload(qr, request))
    if event.status not in (EventStatus.APPROVED, EventStatus.ONGOING):
        raise ValidationError({"detail": "QR codes can only be generated for approved or ongoing events."})
    _, end = event_window(event)
    expires = end + timedelta(minutes=settings.ATTENDANCE_CHECKOUT_GRACE_MINUTES)
    if expires <= timezone.now():
        raise ValidationError({"detail": "This event has already ended."})
    event.qr_codes.filter(active=True).update(active=False)
    qr = EventQR.objects.create(event=event, expires_at=expires, created_by=request.user)
    return Response(_qr_payload(qr, request), status=status.HTTP_201_CREATED)


class CheckInThrottle(UserRateThrottle):
    scope = "checkin"


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([CheckInThrottle])
def check_in(request):
    attendance = services.check_in(request.user, request.data.get("token"))
    return Response(
        {"detail": f"Checked in to {attendance.event.title}.", "attendance": AttendanceSerializer(attendance).data},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([CheckInThrottle])
def check_out(request):
    attendance, hours = services.check_out(request.user, request.data.get("token"))
    return Response({
        "detail": f"Checked out. {hours.hours} hours recorded – submit feedback to verify them.",
        "attendance": AttendanceSerializer(attendance).data,
        "hours": float(hours.hours),
        "feedback_required": True,
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def scan_status(request):
    """What should the scan page show for this token? (event info + the user's current state)"""
    qr = services.resolve_qr(request.query_params.get("token"))
    event = qr.event
    app = event.applications.filter(volunteer=request.user).first()
    att = Attendance.objects.filter(event=event, volunteer=request.user).first()
    if att and att.check_out:
        next_action = "feedback" if not Feedback.objects.filter(event=event, volunteer=request.user).exists() else "done"
    elif att and att.check_in:
        next_action = "check_out"
    else:
        next_action = "check_in"
    start, end = event_window(event)
    return Response({
        "event": {"id": event.id, "title": event.title, "date": event.date, "start_time": event.start_time,
                  "end_time": event.end_time, "location": event.location, "status": event.status},
        "application_status": app.status if app else None,
        "attendance": AttendanceSerializer(att).data if att else None,
        "next_action": next_action,
        "window": {"opens": start - timedelta(minutes=settings.ATTENDANCE_EARLY_CHECKIN_MINUTES), "starts": start, "ends": end},
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def event_attendance(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not can_manage_event(request.user, event):
        raise PermissionDenied("Only the organizer or administrators can view attendance.")
    records = event.attendance_records.select_related("volunteer", "hours_record")
    approved = event.applications.filter(status__in=[ApplicationStatus.APPROVED, ApplicationStatus.COMPLETED])
    not_checked_in = approved.exclude(volunteer_id__in=records.values("volunteer_id")).select_related("volunteer")
    return Response({
        "summary": {
            "approved": approved.count(),
            "present": records.filter(status=Attendance.Status.PRESENT).count(),
            "late": records.filter(status=Attendance.Status.LATE).count(),
            "absent": records.filter(status=Attendance.Status.ABSENT).count(),
            "checked_out": records.filter(check_out__isnull=False).count(),
            "total_hours": float(VolunteerHours.objects.filter(event=event).aggregate(h=Sum("hours"))["h"] or 0),
            "feedback_count": Feedback.objects.filter(event=event).count(),
        },
        "records": AttendanceSerializer(records, many=True).data,
        "not_checked_in": [{"volunteer": a.volunteer_id, "name": a.volunteer.display_name, "email": a.volunteer.email} for a in not_checked_in],
    })


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def mark_absent(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not can_manage_event(request.user, event):
        raise PermissionDenied()
    _, end = event_window(event)
    if timezone.now() < end and event.status != EventStatus.COMPLETED:
        raise ValidationError({"detail": "Absentees can only be marked after the event ends."})
    return Response({"marked_absent": services.mark_absentees(event)})


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def event_feedback(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == "GET":
        if can_manage_event(request.user, event):
            qs = event.feedback.select_related("volunteer")
            from django.db.models import Avg

            return Response({
                "average_rating": event.feedback.aggregate(a=Avg("rating"))["a"],
                "count": qs.count(),
                "results": FeedbackSerializer(qs, many=True).data,
            })
        own = event.feedback.filter(volunteer=request.user).first()
        return Response({"results": [FeedbackSerializer(own).data] if own else []})
    serializer = FeedbackSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    feedback, hours, cert = services.submit_feedback(
        request.user, event, serializer.validated_data["rating"], serializer.validated_data.get("comments", ""), request=request
    )
    return Response({
        "detail": "Thank you! Your hours are verified." + (" Your certificate is ready." if cert else ""),
        "feedback": FeedbackSerializer(feedback).data,
        "verified_hours": float(hours.hours),
        "certificate_id": cert.certificate_id if cert else None,
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def attendance_list(request):
    """Role-aware attendance list (volunteer: own; organizer: own events; admin: scope)."""
    user = request.user
    qs = Attendance.objects.select_related("volunteer", "event", "hours_record")
    if is_admin(user):
        qs = qs.filter(scope_q(user, "event__university_id", "event__college_id", include_unscoped=True))
    elif has_role(user, Role.VOLUNTEER):
        qs = qs.filter(volunteer=user)
    else:
        qs = qs.filter(Q(event__organizer=user))
    p = request.query_params
    if p.get("event"):
        qs = qs.filter(event_id=p["event"])
    if p.get("status"):
        qs = qs.filter(status=p["status"])
    if p.get("category"):
        qs = qs.filter(event__category=p["category"])
    if p.get("search"):
        s = p["search"]
        qs = qs.filter(Q(volunteer__email__icontains=s) | Q(volunteer__first_name__icontains=s) | Q(event__title__icontains=s))
    paginator = StandardPagination()
    page = paginator.paginate_queryset(qs.order_by("-created_at"), request)
    return paginator.get_paginated_response(AttendanceSerializer(page, many=True).data)
