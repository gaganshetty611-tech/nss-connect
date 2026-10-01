"""All statistics are computed from database records with the ORM – nothing is hard-coded."""
from datetime import date, timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from accounts.models import Gender, Role, User
from attendance.models import Attendance, Feedback, VolunteerHours
from certificates.models import Certificate
from events.models import ApplicationStatus, Event, EventApplication, EventCategory, EventStatus

ATTENDED = [Attendance.Status.PRESENT, Attendance.Status.LATE]
CATEGORY_LABELS = dict(EventCategory.choices)

# Transparent impact-points formula (shown in the UI).
POINTS_PER_HOUR = 10
POINTS_PER_EVENT = 20
POINTS_PER_FEEDBACK = 5

BADGES = [
    # (code, label, description, predicate(stats))
    ("FIRST_DRIVE", "First Drive", "Attended your first drive", lambda s: s["events_participated"] >= 1),
    ("FIVE_DRIVES", "Committed", "Attended 5 drives", lambda s: s["events_participated"] >= 5),
    ("TEN_DRIVES", "Drive Veteran", "Attended 10 drives", lambda s: s["events_participated"] >= 10),
    ("HOURS_10", "10 Hours", "10 verified volunteer hours", lambda s: s["volunteer_hours"] >= 10),
    ("HOURS_25", "25 Hours", "25 verified volunteer hours", lambda s: s["volunteer_hours"] >= 25),
    ("HOURS_50", "50 Hours", "50 verified volunteer hours", lambda s: s["volunteer_hours"] >= 50),
    ("HOURS_120", "NSS 120", "120 verified hours (typical NSS annual requirement)", lambda s: s["volunteer_hours"] >= 120),
    ("ABP1_CHAMPION", "ABP 1 Champion", "10+ verified hours in ABP 1", lambda s: s["hours_by_category"].get("ABP1", 0) >= 10),
    ("ABP2_CHAMPION", "ABP 2 Champion", "10+ verified hours in ABP 2", lambda s: s["hours_by_category"].get("ABP2", 0) >= 10),
    ("RELIABLE", "Reliable", "90%+ attendance across 3+ drives", lambda s: (s["attendance_rate"] or 0) >= 90 and s["attendance_total"] >= 3),
]


def month_start(d, back=0):
    y, m = d.year, d.month - back
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


def volunteer_stats(user):
    today = timezone.localdate()
    att = Attendance.objects.filter(volunteer=user)
    attended = att.filter(status__in=ATTENDED).count()
    total = att.count()
    hours_qs = VolunteerHours.objects.filter(volunteer=user)
    verified = hours_qs.filter(verified=True)
    hours = float(verified.aggregate(h=Sum("hours"))["h"] or 0)
    pending_hours = float(hours_qs.filter(verified=False).aggregate(h=Sum("hours"))["h"] or 0)
    by_cat = {c: 0.0 for c in EventCategory.values}
    for row in verified.values("category").annotate(h=Sum("hours")):
        by_cat[row["category"]] = float(row["h"] or 0)
    apps = EventApplication.objects.filter(volunteer=user)
    feedback_count = Feedback.objects.filter(volunteer=user).count()
    stats = {
        "events_participated": attended,
        "upcoming_drives": apps.filter(
            status=ApplicationStatus.APPROVED, event__date__gte=today, event__status__in=[EventStatus.APPROVED, EventStatus.ONGOING]
        ).count(),
        "registered_events": apps.filter(status__in=[ApplicationStatus.PENDING, ApplicationStatus.APPROVED, ApplicationStatus.WAITLISTED]).count(),
        "volunteer_hours": round(hours, 2),
        "pending_hours": round(pending_hours, 2),
        "hours_by_category": by_cat,
        "certificates": Certificate.objects.filter(volunteer=user, revoked=False).count(),
        "attendance_rate": round(100 * attended / total, 1) if total else None,
        "attendance_total": total,
        "feedback_given": feedback_count,
    }
    stats["impact_points"] = round(hours * POINTS_PER_HOUR + attended * POINTS_PER_EVENT + feedback_count * POINTS_PER_FEEDBACK)
    stats["impact_points_formula"] = f"{POINTS_PER_HOUR}×verified hours + {POINTS_PER_EVENT}×drives attended + {POINTS_PER_FEEDBACK}×feedback"
    stats["badges"] = [
        {"code": code, "label": label, "description": desc, "earned": bool(pred(stats))} for code, label, desc, pred in BADGES
    ]
    return stats


def recommended_events_for(user, limit=4):
    """Rule-based: upcoming approved drives with spots left, ranked by interest/skill overlap and proximity."""
    from core.utils import haversine_km

    vp = getattr(user, "volunteer_profile", None)
    today = timezone.localdate()
    taken = EventApplication.objects.filter(volunteer=user).exclude(status=ApplicationStatus.CANCELLED).values("event_id")
    qs = (
        Event.objects.filter(status=EventStatus.APPROVED, date__gte=today)
        .exclude(pk__in=taken)
        .annotate(approved=Count("applications", filter=Q(applications__status=ApplicationStatus.APPROVED)))
        .prefetch_related("required_skills")
    )[:100]
    interests = set(vp.interests or []) if vp else set()
    skills = set(vp.skills.values_list("name", flat=True)) if vp else set()
    availability = set(vp.availability or []) if vp else set()
    ref = vp.nss_unit if vp and vp.nss_unit_id else None
    ranked = []
    for e in qs:
        if e.approved >= e.maximum_volunteers:
            continue
        score, reasons = 0, []
        if e.category in interests or e.theme in interests:
            score += 3
            reasons.append(f"Matches your interest in {e.get_category_display() if e.category in interests else e.get_theme_display()}")
        overlap = skills & {s.name for s in e.required_skills.all()}
        if overlap:
            score += 2 * len(overlap)
            reasons.append(f"Uses your skills: {', '.join(sorted(overlap))}")
        wd = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"][e.date.weekday()]
        if wd in availability:
            score += 1
            reasons.append("On a day you're usually available")
        if ref is not None:
            d = haversine_km(e.latitude, e.longitude, ref.latitude, ref.longitude)
            if d is not None and d <= 15:
                score += 2
                reasons.append(f"{d} km from your NSS unit")
        ranked.append((score, e.date, e, reasons))
    ranked.sort(key=lambda r: (-r[0], r[1]))
    return [
        {"id": e.id, "title": e.title, "date": e.date, "category": e.category, "location": e.location, "score": s, "reasons": r}
        for s, _, e, r in ranked[:limit]
    ]


def analytics(filters=None):
    filters = filters or {}
    ev = Event.objects.all()
    if filters.get("university"):
        ev = ev.filter(Q(university_id=filters["university"]) | Q(applications__college__university_id=filters["university"])).distinct()
    if filters.get("college"):
        ev = ev.filter(Q(college_id=filters["college"]) | Q(applications__college_id=filters["college"])).distinct()
    if filters.get("date_from"):
        ev = ev.filter(date__gte=filters["date_from"])
    if filters.get("date_to"):
        ev = ev.filter(date__lte=filters["date_to"])
    if filters.get("category"):
        ev = ev.filter(category=filters["category"])
    public = ev.filter(status__in=[EventStatus.APPROVED, EventStatus.ONGOING, EventStatus.COMPLETED])
    event_ids = public.values("id")

    att = Attendance.objects.filter(event_id__in=event_ids)
    if filters.get("college"):
        att = att.filter(volunteer__profile__college_id=filters["college"])
    elif filters.get("university"):
        att = att.filter(volunteer__profile__university_id=filters["university"])
    attended = att.filter(status__in=ATTENDED)
    hours = VolunteerHours.objects.filter(attendance__in=att, verified=True)

    total_att = att.count()
    by_cat_events = {c: 0 for c in EventCategory.values}
    for row in public.values("category").annotate(n=Count("id", distinct=True)):
        by_cat_events[row["category"]] = row["n"]
    hours_by_cat = {c: 0.0 for c in EventCategory.values}
    for row in hours.values("category").annotate(h=Sum("hours")):
        hours_by_cat[row["category"]] = round(float(row["h"] or 0), 2)
    volunteers_by_cat = {c: 0 for c in EventCategory.values}
    for row in attended.values("event__category").annotate(n=Count("volunteer", distinct=True)):
        volunteers_by_cat[row["event__category"]] = row["n"]

    summary = {
        "total_events": public.count(),
        "abp1_events": by_cat_events["ABP1"],
        "abp2_events": by_cat_events["ABP2"],
        "college_events": by_cat_events["COLLEGE_EVENT"],
        "university_events": by_cat_events["UNIVERSITY_EVENT"],
        "total_volunteers": attended.values("volunteer").distinct().count(),
        "registered_volunteers": User.objects.filter(role=Role.VOLUNTEER, is_active=True).count(),
        "volunteer_hours": round(float(hours.aggregate(h=Sum("hours"))["h"] or 0), 2),
        "attendance_rate": round(100 * attended.count() / total_att, 1) if total_att else None,
        "completed_drives": public.filter(status=EventStatus.COMPLETED).count(),
        "upcoming_drives": public.filter(status=EventStatus.APPROVED, date__gte=timezone.localdate()).count(),
        "certificates_issued": Certificate.objects.filter(event_id__in=event_ids, revoked=False).count(),
        "hours_by_category": hours_by_cat,
    }

    # Monthly series, last 12 months
    today = timezone.localdate()
    months = [month_start(today, back) for back in range(11, -1, -1)]
    first = months[0]
    monthly_events = {m: {c: 0 for c in EventCategory.values} for m in months}
    for row in public.filter(date__gte=first).annotate(m=TruncMonth("date")).values("m", "category").annotate(n=Count("id", distinct=True)):
        m = row["m"] if isinstance(row["m"], date) else row["m"].date()
        if m in monthly_events:
            monthly_events[m][row["category"]] = row["n"]
    monthly_att = {m: {"PRESENT": 0, "LATE": 0, "ABSENT": 0, "volunteers": 0} for m in months}
    for row in att.filter(event__date__gte=first).annotate(m=TruncMonth("event__date")).values("m", "status").annotate(n=Count("id")):
        m = row["m"] if isinstance(row["m"], date) else row["m"].date()
        if m in monthly_att:
            monthly_att[m][row["status"]] = row["n"]
    for row in attended.filter(event__date__gte=first).annotate(m=TruncMonth("event__date")).values("m").annotate(n=Count("volunteer", distinct=True)):
        m = row["m"] if isinstance(row["m"], date) else row["m"].date()
        if m in monthly_att:
            monthly_att[m]["volunteers"] = row["n"]
    monthly_hours = {m: 0.0 for m in months}
    for row in hours.filter(event__date__gte=first).annotate(m=TruncMonth("event__date")).values("m").annotate(h=Sum("hours")):
        m = row["m"] if isinstance(row["m"], date) else row["m"].date()
        if m in monthly_hours:
            monthly_hours[m] = round(float(row["h"] or 0), 2)

    def label(m):
        return m.strftime("%b %Y")

    charts = {
        "events_by_category": [
            {"category": c, "label": CATEGORY_LABELS[c], "events": by_cat_events[c], "hours": hours_by_cat[c], "volunteers": volunteers_by_cat[c]}
            for c in EventCategory.values
        ],
        "monthly_events": [{"month": label(m), **{CATEGORY_LABELS[c]: monthly_events[m][c] for c in EventCategory.values}} for m in months],
        "volunteer_participation": [{"month": label(m), "volunteers": monthly_att[m]["volunteers"], "hours": monthly_hours[m]} for m in months],
        "attendance_trends": [
            {
                "month": label(m),
                "present": monthly_att[m]["PRESENT"],
                "late": monthly_att[m]["LATE"],
                "absent": monthly_att[m]["ABSENT"],
                "rate": round(100 * (monthly_att[m]["PRESENT"] + monthly_att[m]["LATE"]) / t, 1)
                if (t := monthly_att[m]["PRESENT"] + monthly_att[m]["LATE"] + monthly_att[m]["ABSENT"]) else None,
            }
            for m in months
        ],
        "college_participation": college_participation(att, hours),
        "abp_comparison": [
            {"metric": "Events", "ABP 1": by_cat_events["ABP1"], "ABP 2": by_cat_events["ABP2"]},
            {"metric": "Volunteers", "ABP 1": volunteers_by_cat["ABP1"], "ABP 2": volunteers_by_cat["ABP2"]},
            {"metric": "Hours", "ABP 1": hours_by_cat["ABP1"], "ABP 2": hours_by_cat["ABP2"]},
        ],
        "university_gender": university_gender(attended),
    }
    return {"summary": summary, "charts": charts, "filters": {k: v for k, v in filters.items() if v}}


def college_participation(att, hours, limit=10):
    rows = (
        att.filter(status__in=ATTENDED)
        .exclude(volunteer__profile__college__isnull=True)
        .values("volunteer__profile__college__id", "volunteer__profile__college__name")
        .annotate(volunteers=Count("volunteer", distinct=True), attendances=Count("id"))
        .order_by("-attendances")[:limit]
    )
    hours_map = {
        r["volunteer__profile__college__id"]: float(r["h"] or 0)
        for r in hours.values("volunteer__profile__college__id").annotate(h=Sum("hours"))
    }
    return [
        {
            "college": r["volunteer__profile__college__name"],
            "volunteers": r["volunteers"],
            "attendances": r["attendances"],
            "hours": round(hours_map.get(r["volunteer__profile__college__id"], 0), 2),
        }
        for r in rows
    ]


def university_gender(attended):
    """Proposal requirement: male, female and total volunteer counts organised university-wise."""
    out = {}
    rows = (
        attended.exclude(volunteer__profile__university__isnull=True)
        .values("volunteer__profile__university__name", "volunteer__gender")
        .annotate(n=Count("volunteer", distinct=True))
    )
    for r in rows:
        u = r["volunteer__profile__university__name"]
        d = out.setdefault(u, {"university": u, "male": 0, "female": 0, "other": 0, "total": 0})
        key = {Gender.MALE: "male", Gender.FEMALE: "female"}.get(r["volunteer__gender"], "other")
        d[key] += r["n"]
        d["total"] += r["n"]
    return sorted(out.values(), key=lambda d: -d["total"])
