"""Attendance business rules. All validation happens here, server-side."""
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.utils import event_window
from events.models import ApplicationStatus, EventApplication, EventStatus
from notifications.models import NotificationType
from notifications.services import notify

from .models import Attendance, EventQR, Feedback, VolunteerHours


class AttendanceError(ValidationError):
    pass


def _fail(message, code):
    raise AttendanceError({"detail": message, "code": code})


def resolve_qr(token):
    if not token:
        _fail("QR token is required.", "token_missing")
    qr = EventQR.objects.select_related("event").filter(token=str(token)[:64]).first()
    if qr is None:
        _fail("This QR code is not valid.", "token_invalid")
    if not qr.active:
        _fail("This QR code has been replaced or deactivated. Ask the organizer for the current code.", "token_inactive")
    if qr.expires_at <= timezone.now():
        _fail("This QR code has expired.", "token_expired")
    return qr


def calculate_hours(check_in, check_out, event):
    """Hours = check_out − check_in, capped at the event's scheduled duration (+ early window)."""
    if check_out <= check_in:
        return Decimal("0.00")
    start, end = event_window(event)
    max_hours = (end - start + timedelta(minutes=settings.ATTENDANCE_EARLY_CHECKIN_MINUTES)).total_seconds() / 3600
    hours = min((check_out - check_in).total_seconds() / 3600, max_hours)
    return Decimal(str(hours)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@transaction.atomic
def check_in(user, token, now=None):
    """Validates (1) auth (view), (2) token, (3) event exists, (4) event approved/ongoing,
    (5) registered, (6) application approved, (7) time window, (8) not already checked in."""
    now = now or timezone.now()
    qr = resolve_qr(token)
    event = qr.event
    if event.status not in (EventStatus.APPROVED, EventStatus.ONGOING):
        _fail(f"Check-in is closed: event is {event.get_status_display().lower()}.", "event_not_active")
    app = EventApplication.objects.select_for_update().filter(event=event, volunteer=user).first()
    if app is None:
        _fail("You are not registered for this event.", "not_registered")
    if app.status != ApplicationStatus.APPROVED:
        _fail(f"Your registration is {app.get_status_display().lower()}, not approved.", "not_approved")
    start, end = event_window(event)
    opens = start - timedelta(minutes=settings.ATTENDANCE_EARLY_CHECKIN_MINUTES)
    if now < opens:
        _fail(f"Check-in opens at {timezone.localtime(opens):%d %b %H:%M}.", "too_early")
    if now > end:
        _fail("The event has ended; check-in is closed.", "too_late")
    if Attendance.objects.filter(event=event, volunteer=user).exists():
        _fail("You have already checked in to this event.", "already_checked_in")
    late = now > start + timedelta(minutes=settings.ATTENDANCE_LATE_AFTER_MINUTES)
    try:
        with transaction.atomic():
            attendance = Attendance.objects.create(
                volunteer=user, event=event, application=app, check_in=now, qr=qr,
                status=Attendance.Status.LATE if late else Attendance.Status.PRESENT,
            )
    except IntegrityError:  # concurrent double-scan
        _fail("You have already checked in to this event.", "already_checked_in")
    if event.status == EventStatus.APPROVED:
        event.status = EventStatus.ONGOING
        event.save(update_fields=["status", "updated_at"])
    notify(user, NotificationType.ATTENDANCE_CONFIRMED, "Check-in confirmed",
           f"You checked in to {event.title} at {timezone.localtime(now):%H:%M}"
           + (" (marked late)." if late else "."), link=f"/events/{event.id}")
    return attendance


@transaction.atomic
def check_out(user, token, now=None):
    now = now or timezone.now()
    qr = resolve_qr(token)
    event = qr.event
    attendance = Attendance.objects.select_for_update().filter(event=event, volunteer=user).first()
    if attendance is None or attendance.status == Attendance.Status.ABSENT or not attendance.check_in:
        _fail("You have not checked in to this event.", "not_checked_in")
    if attendance.check_out:
        _fail("You have already checked out.", "already_checked_out")
    min_minutes = settings.ATTENDANCE_MIN_MINUTES
    if now < attendance.check_in + timedelta(minutes=min_minutes):
        ready = timezone.localtime(attendance.check_in + timedelta(minutes=min_minutes))
        _fail(f"You checked in less than {min_minutes} minutes ago. Check out when you leave (from {ready:%H:%M}).", "too_soon")
    _, end = event_window(event)
    if now > end + timedelta(minutes=settings.ATTENDANCE_CHECKOUT_GRACE_MINUTES):
        _fail("Check-out window has closed. The organizer's close-out records your scheduled end time.", "checkout_closed")
    return _record_checkout(attendance, now)


def _record_checkout(attendance, when):
    event = attendance.event
    attendance.check_out = when
    attendance.save(update_fields=["check_out", "updated_at"])
    hours = calculate_hours(attendance.check_in, when, event)
    record, _ = VolunteerHours.objects.update_or_create(
        volunteer=attendance.volunteer, event=event,
        defaults={"attendance": attendance, "hours": hours, "category": event.category, "verified": False},
    )
    notify(attendance.volunteer, NotificationType.FEEDBACK_REQUIRED, "Feedback required to finalise hours",
           f"You logged {hours} hours at {event.title}. Submit the post-event feedback to verify them and receive your certificate.",
           link=f"/events/{event.id}")
    return attendance, record


@transaction.atomic
def submit_feedback(user, event, rating, comments, request=None):
    """Mandatory feedback → hours verified → application COMPLETED → certificate generated."""
    from certificates.services import generate_certificate

    attendance = Attendance.objects.filter(event=event, volunteer=user).exclude(status=Attendance.Status.ABSENT).first()
    if attendance is None:
        _fail("Only volunteers who attended can submit feedback.", "not_attended")
    hours = VolunteerHours.objects.select_for_update().filter(event=event, volunteer=user).first()
    if hours is None:
        _fail("Check out first so your hours can be calculated.", "not_checked_out")
    if Feedback.objects.filter(event=event, volunteer=user).exists():
        _fail("Feedback already submitted.", "feedback_exists")
    feedback = Feedback.objects.create(event=event, volunteer=user, rating=rating, comments=comments)
    hours.verified = True
    hours.verified_at = timezone.now()
    hours.save(update_fields=["verified", "verified_at"])
    EventApplication.objects.filter(event=event, volunteer=user).update(status=ApplicationStatus.COMPLETED)
    cert = None
    if hours.hours > 0:
        cert, _ = generate_certificate(user, event, hours.hours, request=request)
        notify(user, NotificationType.CERTIFICATE_GENERATED, "Your certificate is ready",
               f"Certificate {cert.certificate_id} for {event.title} ({hours.hours} verified hours) is available.",
               link="/certificates", email=True)
    return feedback, hours, cert


@transaction.atomic
def close_out_event(event):
    """Run when an event is marked COMPLETED: auto check-out anyone still checked in (at the scheduled
    end time) and mark approved registrants with no attendance as ABSENT."""
    _, end = event_window(event)
    closed_at = min(end, timezone.now())
    auto_checked_out = 0
    for att in Attendance.objects.filter(event=event, check_out__isnull=True).exclude(status=Attendance.Status.ABSENT):
        _record_checkout(att, max(closed_at, att.check_in))
        auto_checked_out += 1
    marked_absent = mark_absentees(event)
    return {"auto_checked_out": auto_checked_out, "marked_absent": marked_absent}


def mark_absentees(event):
    attended = Attendance.objects.filter(event=event).values_list("volunteer_id", flat=True)
    missing = EventApplication.objects.filter(event=event, status=ApplicationStatus.APPROVED).exclude(volunteer_id__in=attended)
    count = 0
    for app in missing:
        Attendance.objects.get_or_create(
            volunteer=app.volunteer, event=event, defaults={"application": app, "status": Attendance.Status.ABSENT}
        )
        count += 1
    return count
