import csv
import io

from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import Role, User
from attendance.models import Attendance, Feedback, VolunteerHours
from certificates.models import Certificate
from core.permissions import IsPlatformAdmin, admin_scope, has_role, is_admin, scope_q
from events.models import ApplicationStatus, Event, EventApplication, EventCategory, EventStatus, GroupApplication
from ngos.models import NGO
from nss_units.models import NSSUnit, VerificationStatus

from . import services


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def analytics_view(request):
    """Public, aggregate-only ABP analytics. Filters: university, college, category, date_from, date_to."""
    p = request.query_params
    filters = {k: p.get(k) for k in ("university", "college", "category", "date_from", "date_to")}
    if filters["category"] and filters["category"] not in EventCategory.values:
        raise ValidationError({"category": "Unknown category."})
    return Response(services.analytics(filters))


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def volunteer_dashboard(request):
    user = request.user
    if not has_role(user, Role.VOLUNTEER):
        raise PermissionDenied("The volunteer dashboard is for volunteer accounts.")
    today = timezone.localdate()
    stats = services.volunteer_stats(user)
    upcoming = (
        EventApplication.objects.filter(
            volunteer=user, event__date__gte=today,
            status__in=[ApplicationStatus.PENDING, ApplicationStatus.APPROVED, ApplicationStatus.WAITLISTED],
            event__status__in=[EventStatus.APPROVED, EventStatus.ONGOING],
        ).select_related("event").order_by("event__date", "event__start_time")[:6]
    )
    feedback_done = Feedback.objects.filter(volunteer=user).values("event_id")
    needs_feedback = VolunteerHours.objects.filter(volunteer=user, verified=False).exclude(event_id__in=feedback_done).select_related("event")
    recent_certs = Certificate.objects.filter(volunteer=user, revoked=False).select_related("event").order_by("-issued_at")[:5]
    return Response({
        "stats": stats,
        "upcoming": [
            {"application_id": a.id, "status": a.status, "event_id": a.event_id, "title": a.event.title, "date": a.event.date,
             "start_time": a.event.start_time, "location": a.event.location, "category": a.event.category}
            for a in upcoming
        ],
        "pending_feedback": [
            {"event_id": h.event_id, "title": h.event.title, "date": h.event.date, "hours": float(h.hours)} for h in needs_feedback
        ],
        "recent_certificates": [
            {"id": c.id, "certificate_id": c.certificate_id, "event": c.event.title, "hours": float(c.hours), "issued_at": c.issued_at}
            for c in recent_certs
        ],
        "recommended_events": services.recommended_events_for(user),
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def organizer_dashboard(request):
    user = request.user
    if not (has_role(user, Role.NGO_ORGANIZER, Role.NSS_COORDINATOR) or is_admin(user)):
        raise PermissionDenied("The organizer dashboard is for NGO organizers and NSS coordinators.")
    events = Event.objects.filter(organizer=user)
    today = timezone.localdate()
    by_status = {s: 0 for s in EventStatus.values}
    for row in events.values("status").annotate(n=Count("id")):
        by_status[row["status"]] = row["n"]
    apps = EventApplication.objects.filter(event__organizer=user)
    att = Attendance.objects.filter(event__organizer=user)
    attended = att.filter(status__in=services.ATTENDED)
    upcoming = events.filter(date__gte=today, status__in=[EventStatus.PENDING, EventStatus.APPROVED, EventStatus.ONGOING]).annotate(
        approved=Count("applications", filter=Q(applications__status=ApplicationStatus.APPROVED)),
        pending=Count("applications", filter=Q(applications__status=ApplicationStatus.PENDING)),
    ).order_by("date")[:8]
    to_close = events.filter(status__in=[EventStatus.APPROVED, EventStatus.ONGOING], date__lt=today).order_by("-date")[:8]
    ngo = NGO.objects.filter(owner=user).first()
    unit = user.coordinated_units.first()
    return Response({
        "stats": {
            "total_events": events.count(),
            "events_by_status": by_status,
            "pending_applications": apps.filter(status=ApplicationStatus.PENDING).count(),
            "approved_volunteers": apps.filter(status__in=[ApplicationStatus.APPROVED, ApplicationStatus.COMPLETED]).count(),
            "unique_volunteers_engaged": attended.values("volunteer").distinct().count(),
            "volunteer_hours_generated": round(float(VolunteerHours.objects.filter(event__organizer=user).aggregate(h=Sum("hours"))["h"] or 0), 2),
            "attendance_rate": round(100 * attended.count() / att.count(), 1) if att.count() else None,
            "pending_group_applications": GroupApplication.objects.filter(event__organizer=user, status="PENDING").count(),
        },
        "upcoming_events": [
            {"id": e.id, "title": e.title, "date": e.date, "status": e.status, "category": e.category,
             "approved": e.approved, "pending": e.pending, "capacity": e.maximum_volunteers}
            for e in upcoming
        ],
        "needs_close_out": [{"id": e.id, "title": e.title, "date": e.date, "status": e.status} for e in to_close],
        "organization": (
            {"type": "NGO", "id": ngo.id, "name": ngo.name, "status": ngo.verification_status} if ngo
            else {"type": "NSS_UNIT", "id": unit.id, "name": str(unit), "status": unit.verification_status} if unit
            else None
        ),
    })


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_dashboard(request):
    user = request.user
    events = Event.objects.filter(scope_q(user, "university_id", "college_id", include_unscoped=True))
    units = NSSUnit.objects.filter(scope_q(user, "university_id", "college_id"))
    users = User.objects.filter(scope_q(user, "profile__university_id", "profile__college_id"))
    uni, col = admin_scope(user)
    can_ngos = col is None  # college admins do not review NGOs
    return Response({
        "scope": {"university": uni, "college": col, "global": uni is None and col is None},
        "pending": {
            "ngos": NGO.objects.filter(verification_status=VerificationStatus.PENDING).count() if can_ngos else None,
            "nss_units": units.filter(verification_status=VerificationStatus.PENDING).count(),
            "events": events.filter(status=EventStatus.PENDING).count(),
            "applications": EventApplication.objects.filter(event__in=events, status=ApplicationStatus.PENDING).count(),
        },
        "totals": {
            "users": users.count(),
            "volunteers": users.filter(role=Role.VOLUNTEER).count(),
            "suspended_users": users.filter(is_active=False).count(),
            "ngos_verified": NGO.objects.filter(verification_status=VerificationStatus.VERIFIED).count(),
            "nss_units_verified": units.filter(verification_status=VerificationStatus.VERIFIED).count(),
            "events": events.count(),
            "attendance_records": Attendance.objects.filter(event__in=events).count(),
            "certificates": Certificate.objects.filter(event__in=events).count(),
        },
        "recent_events": [
            {"id": e.id, "title": e.title, "status": e.status, "date": e.date, "category": e.category}
            for e in events.order_by("-created_at")[:6]
        ],
    })


# ------------------------------------------------------------------------ reports
REPORT_TYPES = {
    "volunteer_participation": "Volunteer participation",
    "event_participation": "Event participation",
    "abp1": "ABP 1 report",
    "abp2": "ABP 2 report",
    "attendance": "Attendance",
    "volunteer_hours": "Volunteer hours",
    "college": "College-wise participation",
    "university": "University-wise participation",
}


def build_report(kind, user, params):
    """Returns (title, headers, rows). Rows come straight from the database."""
    events = Event.objects.filter(scope_q(user, "university_id", "college_id", include_unscoped=True))
    if params.get("date_from"):
        events = events.filter(date__gte=params["date_from"])
    if params.get("date_to"):
        events = events.filter(date__lte=params["date_to"])
    att = Attendance.objects.filter(event__in=events).select_related("volunteer", "event", "volunteer__profile__college")
    hours = VolunteerHours.objects.filter(event__in=events, verified=True)

    if kind == "volunteer_participation":
        rows = []
        vols = User.objects.filter(role=Role.VOLUNTEER, attendance_records__event__in=events).distinct().select_related("profile__college")
        for v in vols:
            a = att.filter(volunteer=v)
            h = hours.filter(volunteer=v)
            by = {r["category"]: float(r["s"]) for r in h.values("category").annotate(s=Sum("hours"))}
            rows.append([
                v.display_name, v.email, v.get_gender_display(), v.profile.college.name if v.profile.college else "",
                a.filter(status__in=services.ATTENDED).count(), a.filter(status="ABSENT").count(),
                by.get("ABP1", 0), by.get("ABP2", 0), by.get("COLLEGE_EVENT", 0), by.get("UNIVERSITY_EVENT", 0), sum(by.values()),
            ])
        return REPORT_TYPES[kind], ["Volunteer", "Email", "Gender", "College", "Attended", "Absent", "ABP1 h", "ABP2 h", "College h", "University h", "Total h"], rows

    if kind in ("event_participation", "abp1", "abp2"):
        ev = events
        if kind == "abp1":
            ev = ev.filter(category="ABP1")
        elif kind == "abp2":
            ev = ev.filter(category="ABP2")
        ev = ev.annotate(
            approved=Count("applications", filter=Q(applications__status__in=[ApplicationStatus.APPROVED, ApplicationStatus.COMPLETED]), distinct=True),
            present=Count("attendance_records", filter=Q(attendance_records__status__in=services.ATTENDED), distinct=True),
            absent=Count("attendance_records", filter=Q(attendance_records__status="ABSENT"), distinct=True),
        ).order_by("date")
        rows = []
        for e in ev:
            h = float(hours.filter(event=e).aggregate(s=Sum("hours"))["s"] or 0)
            genders = att.filter(event=e, status__in=services.ATTENDED).values("volunteer__gender").annotate(n=Count("id"))
            g = {r["volunteer__gender"]: r["n"] for r in genders}
            rows.append([e.date.isoformat(), e.title, e.get_category_display(), e.get_status_display(), e.organizer_display,
                         e.maximum_volunteers, e.approved, e.present, e.absent, g.get("MALE", 0), g.get("FEMALE", 0), round(h, 2)])
        return REPORT_TYPES[kind], ["Date", "Event", "Category", "Status", "Organizer", "Capacity", "Approved", "Attended", "Absent", "Male", "Female", "Verified h"], rows

    if kind == "attendance":
        rows = [
            [a.event.date.isoformat(), a.event.title, a.volunteer.display_name, a.volunteer.email, a.get_status_display(),
             timezone.localtime(a.check_in).strftime("%H:%M") if a.check_in else "",
             timezone.localtime(a.check_out).strftime("%H:%M") if a.check_out else ""]
            for a in att.order_by("event__date", "volunteer__first_name")
        ]
        return REPORT_TYPES[kind], ["Date", "Event", "Volunteer", "Email", "Status", "Check-in", "Check-out"], rows

    if kind == "volunteer_hours":
        rows = [
            [h.event.date.isoformat(), h.volunteer.display_name, h.volunteer.email, h.event.title, h.category, float(h.hours),
             "Yes" if h.verified else "No"]
            for h in VolunteerHours.objects.filter(event__in=events).select_related("volunteer", "event").order_by("event__date")
        ]
        return REPORT_TYPES[kind], ["Date", "Volunteer", "Email", "Event", "Category", "Hours", "Verified"], rows

    if kind in ("college", "university"):
        key = "volunteer__profile__college__name" if kind == "college" else "volunteer__profile__university__name"
        rows = []
        grouped = (
            att.filter(status__in=services.ATTENDED).exclude(**{f"{key}__isnull": True}).values(key)
            .annotate(
                volunteers=Count("volunteer", distinct=True),
                male=Count("volunteer", filter=Q(volunteer__gender="MALE"), distinct=True),
                female=Count("volunteer", filter=Q(volunteer__gender="FEMALE"), distinct=True),
                attendances=Count("id"), events=Count("event", distinct=True),
            ).order_by(key)
        )
        for g in grouped:
            h = hours.filter(**{key: g[key]})
            by = {r["category"]: float(r["s"]) for r in h.values("category").annotate(s=Sum("hours"))}
            rows.append([g[key], g["male"], g["female"], g["volunteers"], g["events"], g["attendances"],
                         by.get("ABP1", 0), by.get("ABP2", 0), round(sum(by.values()), 2)])
        label = "College" if kind == "college" else "University"
        return REPORT_TYPES[kind], [label, "Male", "Female", "Total volunteers", "Events", "Attendances", "ABP1 h", "ABP2 h", "Total h"], rows

    raise ValidationError({"type": f"Unknown report type. Choose one of: {', '.join(REPORT_TYPES)}."})


def render_pdf_report(title, headers, rows, user):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
                            title=f"NSS Connect – {title}")
    styles = getSampleStyleSheet()
    small = styles["BodyText"].clone("small", fontSize=7.5, leading=9)
    story = [
        Paragraph(f"<b>NSS Connect</b> — {title}", styles["Title"]),
        Paragraph(f"Generated {timezone.localtime():%d %b %Y %H:%M} by {user.display_name} · {len(rows)} rows", styles["Normal"]),
        Spacer(1, 6 * mm),
    ]
    data = [[Paragraph(f"<b>{h}</b>", small) for h in headers]] + [[Paragraph(str(c), small) for c in r] for r in rows]
    if not rows:
        data.append([Paragraph("No records for the selected filters.", small)] + [""] * (len(headers) - 1))
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6d28d9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(table)
    doc.build(story)
    return buf.getvalue()


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def report_export(request):
    """GET /api/reports/?type=abp1&export=csv|pdf|json&date_from=&date_to=
    (`export` rather than `format`: DRF reserves ?format= for renderer negotiation.)"""
    kind = request.query_params.get("type", "event_participation")
    fmt = request.query_params.get("export", "csv").lower()
    title, headers, rows = build_report(kind, request.user, request.query_params)
    stamp = timezone.localdate().isoformat()
    if fmt == "json":
        return Response({"title": title, "headers": headers, "rows": rows})
    if fmt == "pdf":
        resp = HttpResponse(render_pdf_report(title, headers, rows, request.user), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="nss-connect-{kind}-{stamp}.pdf"'
        return resp
    if fmt != "csv":
        raise ValidationError({"export": "Use csv, pdf or json."})
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(headers)
    for r in rows:
        # neutralise spreadsheet formula injection
        writer.writerow([("'" + c) if isinstance(c, str) and c[:1] in ("=", "+", "-", "@") else c for c in r])
    resp = HttpResponse(out.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="nss-connect-{kind}-{stamp}.csv"'
    return resp


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def report_types(request):
    return Response([{"type": k, "label": v} for k, v in REPORT_TYPES.items()])
