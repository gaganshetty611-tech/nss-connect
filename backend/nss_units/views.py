from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from accounts.models import Role
from core.permissions import admin_can_manage_unit, has_role, is_admin, is_super, scope_q
from notifications.models import NotificationType
from notifications.services import notify

from .models import College, NSSUnit, University, VerificationStatus
from .serializers import CollegeSerializer, NSSUnitSerializer, UniversitySerializer


class UniversityViewSet(viewsets.ModelViewSet):
    serializer_class = UniversitySerializer
    pagination_class = None

    def get_queryset(self):
        return University.objects.annotate(college_count=Count("colleges"))

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in permissions.SAFE_METHODS and not is_super(request.user):
            raise PermissionDenied("Only super admins can manage universities.")


class CollegeViewSet(viewsets.ModelViewSet):
    serializer_class = CollegeSerializer
    pagination_class = None

    def get_queryset(self):
        qs = College.objects.select_related("university")
        if self.request.query_params.get("university"):
            qs = qs.filter(university_id=self.request.query_params["university"])
        return qs

    def _check_write(self, university_id):
        user = self.request.user
        if is_super(user):
            return
        if has_role(user, Role.UNIVERSITY_ADMIN) and user.profile.university_id == int(university_id or 0):
            return
        raise PermissionDenied("Only super admins or the university's admin can manage colleges.")

    def perform_create(self, serializer):
        self._check_write(serializer.validated_data["university"].id)
        serializer.save()

    def perform_update(self, serializer):
        self._check_write(serializer.instance.university_id)
        serializer.save()

    def perform_destroy(self, instance):
        self._check_write(instance.university_id)
        instance.delete()


class NSSUnitViewSet(viewsets.ModelViewSet):
    """Public list shows VERIFIED units. Coordinators see their own; admins see units in scope."""

    serializer_class = NSSUnitSerializer

    def get_queryset(self):
        user = self.request.user
        qs = NSSUnit.objects.select_related("college", "university", "coordinator")
        visible = Q(verification_status=VerificationStatus.VERIFIED)
        if user.is_authenticated:
            visible |= Q(coordinator=user)
            if is_admin(user):
                visible |= scope_q(user, "university_id", "college_id")
        qs = qs.filter(visible)
        p = self.request.query_params
        if p.get("status"):
            qs = qs.filter(verification_status=p["status"])
        if p.get("college"):
            qs = qs.filter(college_id=p["college"])
        if p.get("university"):
            qs = qs.filter(university_id=p["university"])
        if p.get("mine") in ("1", "true") and user.is_authenticated:
            qs = qs.filter(coordinator=user)
        if p.get("search"):
            s = p["search"]
            qs = qs.filter(Q(college__name__icontains=s) | Q(unit_number__icontains=s) | Q(location__icontains=s))
        return qs.order_by("college__name", "unit_number")

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        user = self.request.user
        if not (has_role(user, Role.NSS_COORDINATOR) or is_admin(user)):
            raise PermissionDenied("Only NSS coordinators or admins can register NSS units.")
        college = serializer.validated_data["college"]
        extra = {}
        if has_role(user, Role.NSS_COORDINATOR):
            extra["coordinator"] = user
        unit = serializer.save(university=college.university, **extra)
        if is_admin(user) and admin_can_manage_unit(user, unit):
            unit.verification_status = VerificationStatus.VERIFIED
            unit.save()
        if has_role(user, Role.NSS_COORDINATOR):
            prof = user.profile
            prof.college, prof.university = college, college.university
            prof.save()

    def _check_owner_or_admin(self, unit):
        user = self.request.user
        if unit.coordinator_id == user.id or admin_can_manage_unit(user, unit):
            return
        raise PermissionDenied("You cannot modify this NSS unit.")

    def perform_update(self, serializer):
        self._check_owner_or_admin(serializer.instance)
        college = serializer.validated_data.get("college", serializer.instance.college)
        serializer.save(university=college.university)

    def perform_destroy(self, instance):
        if not admin_can_manage_unit(self.request.user, instance):
            raise PermissionDenied("Only admins can delete NSS units.")
        instance.delete()

    def _set_status(self, request, pk, new_status):
        unit = get_object_or_404(NSSUnit, pk=pk)
        if not admin_can_manage_unit(request.user, unit):
            raise PermissionDenied("You cannot verify NSS units outside your scope.")
        unit.verification_status = new_status
        unit.save()
        note = request.data.get("note", "")
        if unit.coordinator:
            if new_status == VerificationStatus.VERIFIED:
                notify(unit.coordinator, NotificationType.NSS_UNIT_VERIFIED, "NSS unit verified",
                       f"{unit} has been verified. You can now host drives and apply as a group.", link=f"/nss-units/{unit.id}", email=True)
            else:
                notify(unit.coordinator, NotificationType.NSS_UNIT_STATUS_CHANGED, f"NSS unit {new_status.lower()}",
                       f"{unit} was marked {new_status.lower()}. {note}".strip(), link=f"/nss-units/{unit.id}", email=True)
        return Response(NSSUnitSerializer(unit).data)

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        return self._set_status(request, pk, VerificationStatus.VERIFIED)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._set_status(request, pk, VerificationStatus.REJECTED)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        return self._set_status(request, pk, VerificationStatus.SUSPENDED)

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        unit = self.get_object()
        if not (unit.coordinator_id == request.user.id or admin_can_manage_unit(request.user, unit)):
            raise PermissionDenied("Only the unit coordinator or admins can view members.")
        from accounts.serializers import UserSerializer

        users = [vp.user for vp in unit.volunteers.select_related("user").order_by("user__first_name")]
        return Response(UserSerializer(users, many=True, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        """Public, aggregate-only statistics for the unit detail page."""
        from attendance.models import Attendance, VolunteerHours
        from django.db.models import Sum

        unit = self.get_object()
        members = unit.volunteers.values_list("user_id", flat=True)
        att = Attendance.objects.filter(volunteer_id__in=members)
        total = att.count()
        attended = att.exclude(status="ABSENT").count()
        hours = VolunteerHours.objects.filter(volunteer_id__in=members, verified=True)
        by_cat = {row["category"]: float(row["h"] or 0) for row in hours.values("category").annotate(h=Sum("hours"))}
        return Response({
            "volunteer_count": unit.volunteer_count,
            "events_attended": attended,
            "attendance_rate": round(100 * attended / total, 1) if total else None,
            "verified_hours": float(hours.aggregate(h=Sum("hours"))["h"] or 0),
            "hours_by_category": by_cat,
            "group_applications": unit.group_applications.count(),
        })
