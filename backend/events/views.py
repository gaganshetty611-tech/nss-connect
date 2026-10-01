from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from accounts.models import Role, User
from accounts.serializers import skills_from_names
from ai_matching.providers import get_provider
from core.permissions import admin_can_manage_event, can_manage_event, has_role, is_admin, scope_q
from core.utils import event_window, haversine_km, extract_exif_gps
from ngos.models import NGO
from notifications.models import NotificationType
from notifications.services import notify, notify_many
from nss_units.models import NSSUnit, VerificationStatus

from .models import (
    PUBLIC_EVENT_STATUSES,
    ApplicationStatus,
    EmergencyVolunteerRequest,
    Event,
    EventApplication,
    EventCategory,
    EventPhoto,
    EventSkill,
    EventStatus,
    GroupApplication,
)
from .serializers import (
    ApplicationSerializer,
    EmergencyRequestSerializer,
    EventDetailSerializer,
    EventListSerializer,
    EventPhotoSerializer,
    EventSkillSerializer,
    EventWriteSerializer,
    GroupApplicationSerializer,
    RegisterForEventSerializer,
)

APPROVED_LIKE = [ApplicationStatus.APPROVED, ApplicationStatus.COMPLETED]
MATERIAL_FIELDS = {"title", "date", "start_time", "end_time", "location", "category"}


def _admins_for_event(event):
    admins = User.objects.filter(is_active=True, role__in=[Role.SUPER_ADMIN, Role.UNIVERSITY_ADMIN, Role.COLLEGE_ADMIN])
    return [a for a in admins if admin_can_manage_event(a, event)]


class EventViewSet(viewsets.ModelViewSet):
    """
    GET /api/events/?category=ABP1&search=cleanup&date=2026-10-01&date_from=&date_to=&location=&skill=&available=true
                    &theme=&ngo=&upcoming=true&status=&mine=true&ordering=date|-date|created
    """

    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action in ("list", "retrieve", "calendar", "map", "photos", "skills"):
            return [permissions.AllowAny()] if self.request.method == "GET" else [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return EventWriteSerializer
        if self.action == "list":
            return EventListSerializer
        return EventDetailSerializer

    def _visibility_q(self):
        user = self.request.user
        q = Q(status__in=PUBLIC_EVENT_STATUSES)
        if user.is_authenticated:
            q |= Q(organizer=user)
            if is_admin(user):
                q |= scope_q(user, "university_id", "college_id", include_unscoped=True)
        return q

    def get_queryset(self):
        qs = (
            Event.objects.filter(self._visibility_q())
            .select_related("organizer", "ngo", "nss_unit", "nss_unit__college", "college", "university")
            .prefetch_related("required_skills")
            .annotate(approved_count=Count("applications", filter=Q(applications__status__in=APPROVED_LIKE), distinct=True))
        )
        if self.action != "list":
            return qs
        p = self.request.query_params
        user = self.request.user
        if p.get("category") and p["category"].upper() != "ALL":
            qs = qs.filter(category=p["category"])
        if p.get("theme"):
            qs = qs.filter(theme=p["theme"])
        if p.get("status"):
            qs = qs.filter(status__in=p["status"].split(","))
        elif not (p.get("mine") in ("1", "true") or p.get("all") in ("1", "true")):
            # Public default: only APPROVED/ONGOING drives (upcoming discovery)
            qs = qs.filter(status__in=[EventStatus.APPROVED, EventStatus.ONGOING])
        if p.get("search"):
            s = p["search"]
            qs = qs.filter(
                Q(title__icontains=s) | Q(description__icontains=s) | Q(location__icontains=s)
                | Q(ngo__name__icontains=s) | Q(required_skills__name__icontains=s)
            ).distinct()
        if p.get("date"):
            qs = qs.filter(date=p["date"])
        if p.get("date_from"):
            qs = qs.filter(date__gte=p["date_from"])
        if p.get("date_to"):
            qs = qs.filter(date__lte=p["date_to"])
        if p.get("upcoming") in ("1", "true"):
            qs = qs.filter(date__gte=timezone.localdate())
        if p.get("location"):
            qs = qs.filter(location__icontains=p["location"])
        if p.get("skill"):
            names = [s.strip() for s in p["skill"].split(",") if s.strip()]
            qs = qs.filter(required_skills__name__in=[n.title() for n in names]).distinct()
        if p.get("available") in ("1", "true"):
            qs = qs.filter(approved_count__lt=F("maximum_volunteers"))
        if p.get("ngo"):
            qs = qs.filter(ngo_id=p["ngo"])
        if p.get("nss_unit"):
            qs = qs.filter(nss_unit_id=p["nss_unit"])
        if p.get("mine") in ("1", "true") and user.is_authenticated:
            qs = qs.filter(organizer=user)
        if p.get("registered") in ("1", "true") and user.is_authenticated:
            qs = qs.filter(applications__volunteer=user).exclude(applications__status=ApplicationStatus.CANCELLED).distinct()
        ordering = p.get("ordering", "date")
        order_map = {"date": ["date", "start_time"], "-date": ["-date", "-start_time"], "created": ["-created_at"], "title": ["title"]}
        return qs.order_by(*order_map.get(ordering, ["date", "start_time"]))

    # ------------------------------------------------------------------ create/update/delete
    def perform_create(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        extra = {"organizer": user}
        if has_role(user, Role.NGO_ORGANIZER):
            ngo = NGO.objects.filter(owner=user).first()
            if ngo is None:
                raise PermissionDenied("Register your NGO before hosting drives.")
            if ngo.verification_status != VerificationStatus.VERIFIED:
                raise PermissionDenied("Your NGO must be verified by an administrator before it can post drives.")
            extra.update(ngo=ngo, nss_unit=None)
        elif has_role(user, Role.NSS_COORDINATOR):
            unit = user.coordinated_units.filter(verification_status=VerificationStatus.VERIFIED).first()
            if unit is None:
                raise PermissionDenied("Your NSS unit must be verified before it can host drives.")
            extra.update(nss_unit=unit, college=unit.college, university=unit.university, ngo=None)
        elif is_admin(user):
            prof = user.profile
            if data.get("nss_unit"):
                extra.update(college=data["nss_unit"].college, university=data["nss_unit"].university)
            else:
                extra.update(college=prof.college, university=prof.university or (prof.college.university if prof.college else None))
        else:
            raise PermissionDenied("Volunteers cannot host drives. Ask your NSS coordinator.")

        if data.get("category") == EventCategory.UNIVERSITY_EVENT and has_role(user, Role.NGO_ORGANIZER):
            raise ValidationError({"category": "NGOs cannot create University Events."})
        if "theme" not in data:
            extra["theme"] = get_provider().categorize_event(data["title"], data["description"])["theme"]

        event = serializer.save(**extra)
        if is_admin(user) and admin_can_manage_event(user, event):
            event.status = EventStatus.APPROVED
            event.approved_by = user
            event.save(update_fields=["status", "approved_by"])
        else:
            for admin in _admins_for_event(event):
                notify(admin, NotificationType.EVENT_UPDATED, "New drive awaiting approval",
                       f"{event.title} ({event.get_category_display()}) on {event.date:%d %b} needs review.", link="/admin/events")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        event = self.get_queryset().get(pk=serializer.instance.pk)
        return Response(EventDetailSerializer(event, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        event = serializer.instance
        user = self.request.user
        if not can_manage_event(user, event):
            raise PermissionDenied("You can only edit your own events.")
        if event.status in (EventStatus.COMPLETED, EventStatus.CANCELLED) and not is_admin(user):
            raise PermissionDenied("Completed or cancelled events cannot be edited.")
        changed = {k for k, v in serializer.validated_data.items() if getattr(event, k, None) != v} & MATERIAL_FIELDS
        if not is_admin(user):  # organizers cannot re-assign the hosting NGO/unit
            serializer.validated_data.pop("ngo", None)
            serializer.validated_data.pop("nss_unit", None)
        updated = serializer.save()
        if changed and not is_admin(user) and updated.status == EventStatus.APPROVED:
            updated.status = EventStatus.PENDING
            updated.save(update_fields=["status"])
            for admin in _admins_for_event(updated):
                notify(admin, NotificationType.EVENT_UPDATED, "Edited drive needs re-approval",
                       f"{updated.title} changed ({', '.join(sorted(changed))}).", link="/admin/events")
        if changed:
            recipients = [a.volunteer for a in updated.applications.filter(status__in=[ApplicationStatus.APPROVED, ApplicationStatus.PENDING, ApplicationStatus.WAITLISTED]).select_related("volunteer")]
            notify_many(recipients, NotificationType.EVENT_UPDATED, f"Drive updated: {updated.title}",
                        f"Details changed: {', '.join(sorted(changed))}. Please re-check the drive page.", link=f"/events/{updated.id}")

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        event = self.get_queryset().get(pk=kwargs["pk"])
        return Response(EventDetailSerializer(event, context=self.get_serializer_context()).data)

    def perform_destroy(self, instance):
        user = self.request.user
        if not can_manage_event(user, instance):
            raise PermissionDenied("You can only delete your own events.")
        if not is_admin(user) and instance.status not in (EventStatus.PENDING, EventStatus.REJECTED, EventStatus.CANCELLED):
            raise PermissionDenied("Approved events cannot be deleted; cancel them instead.")
        if instance.attendance_records.exists() or instance.certificates.exists():
            raise ValidationError({"detail": "This event has attendance/certificate records and cannot be deleted. Cancel it instead."})
        instance.delete()

    # ------------------------------------------------------------------ admin review
    def _get_event_any_status(self, pk):
        event = get_object_or_404(Event, pk=pk)
        return event

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        event = self._get_event_any_status(pk)
        if not admin_can_manage_event(request.user, event):
            raise PermissionDenied("Only administrators in scope can approve events.")
        if event.status not in (EventStatus.PENDING, EventStatus.REJECTED):
            raise ValidationError({"detail": f"Event is already {event.get_status_display().lower()}."})
        event.status = EventStatus.APPROVED
        event.approved_by = request.user
        event.review_note = request.data.get("note", "")
        event.save()
        notify(event.organizer, NotificationType.EVENT_APPROVED, "Drive approved",
               f"{event.title} is approved and now visible to volunteers.", link=f"/events/{event.id}", email=True)
        return Response(EventDetailSerializer(event, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        event = self._get_event_any_status(pk)
        if not admin_can_manage_event(request.user, event):
            raise PermissionDenied("Only administrators in scope can reject events.")
        if event.status not in (EventStatus.PENDING, EventStatus.APPROVED):
            raise ValidationError({"detail": f"Cannot reject a {event.get_status_display().lower()} event."})
        event.status = EventStatus.REJECTED
        event.review_note = request.data.get("note", "")
        event.save()
        notify(event.organizer, NotificationType.EVENT_REJECTED, "Drive rejected",
               f"{event.title} was not approved. {event.review_note}".strip(), link=f"/events/{event.id}", email=True)
        return Response(EventDetailSerializer(event, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, pk=None):
        """Organizer lifecycle: ONGOING, COMPLETED (runs close-out + summary) or CANCELLED."""
        from attendance.services import close_out_event

        event = self._get_event_any_status(pk)
        if not can_manage_event(request.user, event):
            raise PermissionDenied("Only the organizer or administrators can change event status.")
        new = request.data.get("status")
        allowed = {
            EventStatus.ONGOING: [EventStatus.APPROVED],
            EventStatus.COMPLETED: [EventStatus.APPROVED, EventStatus.ONGOING],
            EventStatus.CANCELLED: [EventStatus.PENDING, EventStatus.APPROVED, EventStatus.ONGOING],
        }
        if new not in allowed:
            raise ValidationError({"status": "Must be ONGOING, COMPLETED or CANCELLED."})
        if event.status not in allowed[new]:
            raise ValidationError({"detail": f"Cannot move from {event.status} to {new}."})
        if new == EventStatus.COMPLETED:
            start, _ = event_window(event)
            if timezone.now() < start:
                raise ValidationError({"detail": "An event cannot be completed before it starts."})
        extra = {}
        with transaction.atomic():
            event.status = new
            event.save(update_fields=["status", "updated_at"])
            if new in (EventStatus.COMPLETED, EventStatus.CANCELLED):
                event.qr_codes.filter(active=True).update(active=False)
            if new == EventStatus.COMPLETED:
                extra = close_out_event(event)
                event.summary = get_provider().summarize_event(event)["summary"]
                event.save(update_fields=["summary"])
        if new == EventStatus.CANCELLED:
            recipients = [a.volunteer for a in event.applications.exclude(status__in=[ApplicationStatus.CANCELLED, ApplicationStatus.REJECTED]).select_related("volunteer")]
            notify_many(recipients, NotificationType.EVENT_UPDATED, f"Drive cancelled: {event.title}",
                        f"{event.title} on {event.date:%d %b} has been cancelled by the organizer.", link=f"/events/{event.id}", email=True)
        data = EventDetailSerializer(event, context={"request": request}).data
        data["close_out"] = extra
        return Response(data)

    # ------------------------------------------------------------------ volunteer registration
    @action(detail=True, methods=["post"])
    def register(self, request, pk=None):
        user = request.user
        if not has_role(user, Role.VOLUNTEER):
            raise PermissionDenied("Only volunteer accounts can register for drives.")
        event = get_object_or_404(Event, pk=pk, status__in=[EventStatus.APPROVED, EventStatus.ONGOING])
        start, end = event_window(event)
        if timezone.now() > end:
            raise ValidationError({"detail": "This drive has already ended."})
        serializer = RegisterForEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        vp = user.volunteer_profile
        with transaction.atomic():
            Event.objects.select_for_update().filter(pk=event.pk).first()  # serialise capacity checks
            approved = event.applications.filter(status__in=APPROVED_LIKE).count()
            initial = ApplicationStatus.WAITLISTED if approved >= event.maximum_volunteers else ApplicationStatus.PENDING
            fields = {
                "college": user.profile.college or (vp.nss_unit.college if vp.nss_unit else None),
                "nss_unit": vp.nss_unit,
                "email": d.get("email") or user.email,
                "phone": d.get("phone") or user.phone,
                "motivation": d.get("motivation", ""),
                "status": initial,
            }
            existing = EventApplication.objects.filter(event=event, volunteer=user).first()
            if existing and existing.status != ApplicationStatus.CANCELLED:
                return Response(
                    {"detail": "You are already registered for this drive.", "code": "duplicate", "application": ApplicationSerializer(existing).data},
                    status=status.HTTP_409_CONFLICT,
                )
            try:
                if existing:  # re-registering after a cancellation re-uses the row (unique constraint)
                    for k, v in fields.items():
                        setattr(existing, k, v)
                    existing.decided_at = existing.decided_by = None
                    existing.save()
                    app = existing
                else:
                    app = EventApplication.objects.create(volunteer=user, event=event, **fields)
            except IntegrityError:
                return Response({"detail": "You are already registered for this drive.", "code": "duplicate"}, status=status.HTTP_409_CONFLICT)
            skills = skills_from_names(d.get("skills")) if d.get("skills") else list(vp.skills.all())
            app.skills.set(skills)
        notify(event.organizer, NotificationType.APPLICATION_CREATED, "New volunteer application",
               f"{user.display_name} applied for {event.title}.", link=f"/events/{event.id}/applications")
        notify(user, NotificationType.APPLICATION_CREATED,
               "Application received" if initial == ApplicationStatus.PENDING else "Added to waitlist",
               f"Your application for {event.title} on {event.date:%d %b %Y} was received"
               + (" and is awaiting approval." if initial == ApplicationStatus.PENDING else "; the drive is full so you are waitlisted."),
               link=f"/events/{event.id}", email=True)
        return Response(ApplicationSerializer(app).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        event = get_object_or_404(Event, pk=pk)
        app = EventApplication.objects.filter(event=event, volunteer=request.user).first()
        if app is None or app.status == ApplicationStatus.CANCELLED:
            raise ValidationError({"detail": "You have no active registration for this drive."})
        if app.status == ApplicationStatus.COMPLETED or event.attendance_records.filter(volunteer=request.user).exists():
            raise ValidationError({"detail": "You already attended this drive; the registration cannot be cancelled."})
        was_approved = app.status == ApplicationStatus.APPROVED
        app.status = ApplicationStatus.CANCELLED
        app.save(update_fields=["status", "updated_at"])
        notify(event.organizer, NotificationType.APPLICATION_CANCELLED, "Volunteer cancelled",
               f"{request.user.display_name} cancelled their registration for {event.title}"
               + (" (a confirmed spot is now free)." if was_approved else "."), link=f"/events/{event.id}/applications")
        return Response(ApplicationSerializer(app).data)

    @action(detail=True, methods=["get"])
    def applications(self, request, pk=None):
        event = get_object_or_404(Event, pk=pk)
        if not can_manage_event(request.user, event):
            raise PermissionDenied("Only the organizer or administrators can view applications.")
        qs = event.applications.select_related("volunteer", "college", "nss_unit", "nss_unit__college").prefetch_related("skills", "attendance_records")
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        return Response({
            "event": EventListSerializer(event, context={"request": request}).data,
            "counts": {s: event.applications.filter(status=s).count() for s in ApplicationStatus.values},
            "results": ApplicationSerializer(qs, many=True).data,
        })

    # ------------------------------------------------------------------ group applications
    @action(detail=True, methods=["post"], url_path="group-apply")
    def group_apply(self, request, pk=None):
        user = request.user
        if not has_role(user, Role.NSS_COORDINATOR):
            raise PermissionDenied("Only NSS coordinators can apply as a group.")
        event = get_object_or_404(Event, pk=pk, status__in=[EventStatus.APPROVED, EventStatus.ONGOING])
        unit_id = request.data.get("nss_unit")
        units = user.coordinated_units.filter(verification_status=VerificationStatus.VERIFIED)
        unit = units.filter(pk=unit_id).first() if unit_id else units.first()
        if unit is None:
            raise PermissionDenied("You need a verified NSS unit to apply as a group.")
        serializer = GroupApplicationSerializer(data={**request.data.dict(), "nss_unit": unit.id} if hasattr(request.data, "dict") else {**request.data, "nss_unit": unit.id})
        serializer.is_valid(raise_exception=True)
        count = serializer.validated_data["requested_volunteer_count"]
        if count > max(unit.volunteer_count, 1) * 2 and count > 10:
            raise ValidationError({"requested_volunteer_count": f"Your unit has {unit.volunteer_count} registered volunteers."})
        existing = GroupApplication.objects.filter(nss_unit=unit, event=event).first()
        if existing and existing.status in (GroupApplication.Status.PENDING, GroupApplication.Status.ACCEPTED):
            return Response({"detail": "Your unit has already applied for this drive."}, status=status.HTTP_409_CONFLICT)
        with transaction.atomic():
            if existing:
                existing.delete()
            names = serializer.validated_data.pop("skills", [])
            ga = serializer.save(event=event, submitted_by=user)
            ga.skills.set(skills_from_names(names))
        notify(event.organizer, NotificationType.GROUP_APPLICATION, "NSS unit group application",
               f"{unit} wants to bring {ga.requested_volunteer_count} volunteers to {event.title}.", link=f"/events/{event.id}/applications", email=True)
        return Response(GroupApplicationSerializer(ga).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="group-applications")
    def group_applications(self, request, pk=None):
        event = get_object_or_404(Event, pk=pk)
        if not can_manage_event(request.user, event):
            raise PermissionDenied("Only the organizer or administrators can view group applications.")
        qs = event.group_applications.select_related("nss_unit", "nss_unit__college", "submitted_by").prefetch_related("skills")
        return Response(GroupApplicationSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="invite-unit")
    def invite_unit(self, request, pk=None):
        event = get_object_or_404(Event, pk=pk, status__in=[EventStatus.APPROVED, EventStatus.ONGOING])
        if not can_manage_event(request.user, event):
            raise PermissionDenied("Only the organizer or administrators can invite units.")
        unit = get_object_or_404(NSSUnit, pk=request.data.get("nss_unit"), verification_status=VerificationStatus.VERIFIED)
        message = str(request.data.get("message", ""))[:1000]
        sent = 0
        if unit.coordinator:
            notify(unit.coordinator, NotificationType.NSS_INVITATION, f"Invitation: {event.title}",
                   f"{event.organizer_display} invites {unit} to {event.title} on {event.date:%d %b %Y}. {message}".strip(),
                   link=f"/events/{event.id}", email=True)
            sent += 1
        if request.data.get("notify_members") in (True, "true", "1"):
            members = [vp.user for vp in unit.volunteers.select_related("user")]
            sent += notify_many(members, NotificationType.NSS_INVITATION, f"Your unit is invited: {event.title}",
                                f"{event.organizer_display} invited your NSS unit. Register on the drive page.", link=f"/events/{event.id}")
        return Response({"detail": f"Invitation sent to {sent} recipient(s).", "sent": sent})

    # ------------------------------------------------------------------ gallery
    @action(detail=True, methods=["get", "post"], parser_classes=[MultiPartParser, FormParser])
    def photos(self, request, pk=None):
        event = get_object_or_404(Event.objects.filter(self._visibility_q()), pk=pk)
        if request.method == "GET":
            return Response(EventPhotoSerializer(event.photos.select_related("uploaded_by"), many=True, context={"request": request}).data)
        user = request.user
        attended = event.attendance_records.filter(volunteer=user).exclude(status="ABSENT").exists() if user.is_authenticated else False
        if not (can_manage_event(user, event) or attended):
            raise PermissionDenied("Only the organizer, admins or volunteers who attended can upload photos.")
        if event.photos.count() >= 200:
            raise ValidationError({"detail": "Gallery limit reached (200 photos)."})
        serializer = EventPhotoSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        lat = serializer.validated_data.get("latitude")
        lon = serializer.validated_data.get("longitude")
        if lat is not None and lon is not None:
            location_source = "DEVICE"
        else:
            # Uploader's browser didn't supply Geolocation coordinates (denied
            # permission, unsupported, or a file picked from an older photo) —
            # fall back to whatever GPS tag the image itself was taken with.
            lat, lon = extract_exif_gps(request.data.get("photo"))
            location_source = "EXIF" if lat is not None else ""

        photo = serializer.save(event=event, uploaded_by=user, latitude=lat, longitude=lon, location_source=location_source)
        return Response(EventPhotoSerializer(photo, context={"request": request}).data, status=status.HTTP_201_CREATED)

    # ------------------------------------------------------------------ calendar & map feeds
    @action(detail=False, methods=["get"])
    def calendar(self, request):
        """Approved/ongoing events between ?start= and ?end= (defaults: this month ± 1)."""
        today = timezone.localdate()
        start = request.query_params.get("start") or (today.replace(day=1) - timedelta(days=7)).isoformat()
        end = request.query_params.get("end") or (today.replace(day=28) + timedelta(days=40)).isoformat()
        qs = Event.objects.filter(status__in=PUBLIC_EVENT_STATUSES, date__gte=start, date__lte=end)
        if request.query_params.get("category"):
            qs = qs.filter(category=request.query_params["category"])
        return Response([
            {"id": e.id, "title": e.title, "date": e.date, "start_time": e.start_time, "end_time": e.end_time,
             "category": e.category, "status": e.status, "location": e.location}
            for e in qs.order_by("date", "start_time")
        ])

    @action(detail=False, methods=["get"])
    def map(self, request):
        """Map pins for upcoming public events, verified NGOs and verified NSS units."""
        today = timezone.localdate()
        events = Event.objects.filter(status__in=[EventStatus.APPROVED, EventStatus.ONGOING], date__gte=today, latitude__isnull=False)
        if request.query_params.get("category"):
            events = events.filter(category=request.query_params["category"])
        ngos = NGO.objects.filter(verification_status=VerificationStatus.VERIFIED, latitude__isnull=False)
        units = NSSUnit.objects.filter(verification_status=VerificationStatus.VERIFIED, latitude__isnull=False).select_related("college")
        return Response({
            "events": [{"id": e.id, "title": e.title, "lat": e.latitude, "lng": e.longitude, "category": e.category, "date": e.date, "location": e.location} for e in events],
            "ngos": [{"id": n.id, "name": n.name, "lat": n.latitude, "lng": n.longitude, "location": n.location} for n in ngos],
            "nss_units": [{"id": u.id, "name": str(u), "lat": u.latitude, "lng": u.longitude, "volunteer_count": u.volunteer_count} for u in units],
        })

    @action(detail=False, methods=["get"])
    def skills(self, request):
        return Response(EventSkillSerializer(EventSkill.objects.all(), many=True).data)


# ---------------------------------------------------------------------- application decisions
def _decide(request, pk, new_status):
    app = get_object_or_404(EventApplication.objects.select_related("event", "volunteer"), pk=pk)
    event = app.event
    if not can_manage_event(request.user, event):
        raise PermissionDenied("Only the organizer or administrators can decide applications.")
    if app.status in (ApplicationStatus.CANCELLED, ApplicationStatus.COMPLETED):
        raise ValidationError({"detail": f"Application is {app.get_status_display().lower()}."})
    if event.status in (EventStatus.COMPLETED, EventStatus.CANCELLED, EventStatus.REJECTED):
        raise ValidationError({"detail": f"Event is {event.get_status_display().lower()}."})
    with transaction.atomic():
        Event.objects.select_for_update().filter(pk=event.pk).first()
        if new_status == ApplicationStatus.APPROVED and app.status != ApplicationStatus.APPROVED:
            approved = event.applications.filter(status__in=APPROVED_LIKE).count()
            if approved >= event.maximum_volunteers:
                raise ValidationError({"detail": "The drive is full. Increase capacity or waitlist this volunteer.", "code": "full"})
        app.status = new_status
        app.decided_at = timezone.now()
        app.decided_by = request.user
        app.save()
    ntype, title, msg = {
        ApplicationStatus.APPROVED: (NotificationType.APPLICATION_APPROVED, "Application approved",
                                     f"You're confirmed for {event.title} on {event.date:%d %b %Y}, {event.start_time:%H:%M} at {event.location}. Scan the event QR at the venue to check in."),
        ApplicationStatus.REJECTED: (NotificationType.APPLICATION_REJECTED, "Application not accepted",
                                     f"Your application for {event.title} was not accepted this time."),
        ApplicationStatus.WAITLISTED: (NotificationType.APPLICATION_WAITLISTED, "You're on the waitlist",
                                       f"You're waitlisted for {event.title}. We'll notify you if a spot opens."),
    }[new_status]
    notify(app.volunteer, ntype, title, msg, link=f"/events/{event.id}", email=new_status == ApplicationStatus.APPROVED)
    return Response(ApplicationSerializer(app).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def approve_application(request, pk):
    return _decide(request, pk, ApplicationStatus.APPROVED)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def reject_application(request, pk):
    return _decide(request, pk, ApplicationStatus.REJECTED)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def waitlist_application(request, pk):
    return _decide(request, pk, ApplicationStatus.WAITLISTED)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def application_list(request):
    """Role-aware list: volunteers see their own, organizers see their events', admins see their scope."""
    user = request.user
    qs = EventApplication.objects.select_related("event", "volunteer", "college", "nss_unit", "nss_unit__college").prefetch_related("skills", "attendance_records")
    if is_admin(user):
        qs = qs.filter(scope_q(user, "event__university_id", "event__college_id", include_unscoped=True))
    elif has_role(user, Role.VOLUNTEER):
        qs = qs.filter(volunteer=user)
    elif has_role(user, Role.NSS_COORDINATOR):
        qs = qs.filter(Q(event__organizer=user) | Q(nss_unit__coordinator=user))
    else:
        qs = qs.filter(event__organizer=user)
    p = request.query_params
    if p.get("status"):
        qs = qs.filter(status=p["status"])
    if p.get("event"):
        qs = qs.filter(event_id=p["event"])
    if p.get("category"):
        qs = qs.filter(event__category=p["category"])
    if p.get("search"):
        s = p["search"]
        qs = qs.filter(Q(volunteer__email__icontains=s) | Q(volunteer__first_name__icontains=s) | Q(event__title__icontains=s))
    from core.pagination import StandardPagination

    paginator = StandardPagination()
    page = paginator.paginate_queryset(qs.order_by("-application_date"), request)
    return paginator.get_paginated_response(ApplicationSerializer(page, many=True).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def decide_group_application(request, pk, decision):
    ga = get_object_or_404(GroupApplication.objects.select_related("event", "nss_unit"), pk=pk)
    event = ga.event
    if not can_manage_event(request.user, event):
        raise PermissionDenied("Only the organizer or administrators can decide group applications.")
    if ga.status != GroupApplication.Status.PENDING:
        raise ValidationError({"detail": f"Group application is already {ga.status.lower()}."})
    ga.status = GroupApplication.Status.ACCEPTED if decision == "accept" else GroupApplication.Status.REJECTED
    ga.decided_at = timezone.now()
    ga.save()
    unit = ga.nss_unit
    if unit.coordinator:
        notify(unit.coordinator, NotificationType.GROUP_APPLICATION, f"Group application {ga.status.lower()}",
               f"{event.organizer_display} {ga.status.lower()} {unit}'s request for {ga.requested_volunteer_count} volunteers at {event.title}.",
               link=f"/events/{event.id}", email=True)
    if ga.status == GroupApplication.Status.ACCEPTED:
        members = [vp.user for vp in unit.volunteers.select_related("user")]
        notify_many(members, NotificationType.NSS_INVITATION, f"Your unit is going to {event.title}",
                    f"{unit} was accepted for {event.title} on {event.date:%d %b}. Register individually on the drive page to be counted.",
                    link=f"/events/{event.id}")
    return Response(GroupApplicationSerializer(ga).data)


# ---------------------------------------------------------------------- emergency requests
class EmergencyRequestViewSet(viewsets.ModelViewSet):
    serializer_class = EmergencyRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = EmergencyVolunteerRequest.objects.select_related("event", "created_by").prefetch_related("required_skills")
        if self.request.query_params.get("active") in ("1", "true"):
            qs = qs.filter(expires_at__gt=timezone.now())
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        event = serializer.validated_data.get("event")
        if event is not None:
            if not can_manage_event(user, event):
                raise PermissionDenied("You can only raise emergency requests for your own events.")
        elif not (is_admin(user) or has_role(user, Role.NGO_ORGANIZER, Role.NSS_COORDINATOR)):
            raise PermissionDenied("Only organizers and administrators can raise emergency requests.")
        req = serializer.save(created_by=user)
        req.notified_count = broadcast_emergency(req)
        req.save(update_fields=["notified_count"])

    def perform_destroy(self, instance):
        if not (instance.created_by_id == self.request.user.id or is_admin(self.request.user)):
            raise PermissionDenied()
        instance.delete()


def broadcast_emergency(req, radius_km=50):
    """Notify matching volunteers: those with a required skill or matching interest, within radius of the
    request (by their NSS unit's location) where both locations are known. Coordinators of nearby verified
    units are always notified. HIGH/CRITICAL requests also go out by email."""
    from accounts.models import VolunteerProfile

    skills = set(req.required_skills.values_list("id", flat=True))
    lat, lng = req.latitude, req.longitude
    if (lat is None or lng is None) and req.event_id:
        lat, lng = req.event.latitude, req.event.longitude
    interests = {req.event.category, req.event.theme} if req.event_id else set()

    def near(obj):
        d = haversine_km(lat, lng, getattr(obj, "latitude", None), getattr(obj, "longitude", None))
        return d is None or d <= radius_km

    recipients = {}
    for vp in VolunteerProfile.objects.filter(user__is_active=True).select_related("user", "nss_unit").prefetch_related("skills"):
        if vp.nss_unit and not near(vp.nss_unit):
            continue
        has_skill = bool(skills & {s.id for s in vp.skills.all()})
        likes = bool(interests & set(vp.interests or []))
        # With required skills: skill or interest match. Without: everyone nearby (it's an emergency).
        if has_skill or likes or not skills:
            recipients[vp.user_id] = vp.user
    for unit in NSSUnit.objects.filter(verification_status=VerificationStatus.VERIFIED, coordinator__isnull=False).select_related("coordinator"):
        if near(unit):
            recipients[unit.coordinator_id] = unit.coordinator
    recipients.pop(req.created_by_id, None)
    email = req.priority in (EmergencyVolunteerRequest.Priority.HIGH, EmergencyVolunteerRequest.Priority.CRITICAL)
    link = f"/events/{req.event_id}" if req.event_id else "/dashboard"
    return notify_many(
        recipients.values(), NotificationType.EMERGENCY_REQUEST, f"[{req.priority}] {req.title}",
        f"{req.required_volunteers} volunteers needed at {req.location} before {timezone.localtime(req.expires_at):%d %b %H:%M}. {req.description}",
        link=link, email=email,
    )


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def delete_photo(request, pk):
    photo = get_object_or_404(EventPhoto, pk=pk)
    if not (photo.uploaded_by_id == request.user.id or can_manage_event(request.user, photo.event)):
        raise PermissionDenied("You can only delete your own photos.")
    photo.photo.delete(save=False)
    photo.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
