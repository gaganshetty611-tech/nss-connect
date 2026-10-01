"""Role-based and object-level permission helpers. The frontend hides buttons for UX only;
every rule that matters is enforced here."""
from django.db.models import Q
from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import ADMIN_ROLES, Role


def has_role(user, *roles):
    return bool(user and user.is_authenticated and (user.role in roles or (user.is_superuser and Role.SUPER_ADMIN in roles)))


def is_admin(user):
    return bool(user and user.is_authenticated and (user.role in ADMIN_ROLES or user.is_superuser))


def is_super(user):
    return bool(user and user.is_authenticated and (user.role == Role.SUPER_ADMIN or user.is_superuser))


def _profile(user):
    return getattr(user, "profile", None)


def admin_scope(user):
    """Return (university_id, college_id) scope for an admin. (None, None) means global."""
    if is_super(user):
        return None, None
    prof = _profile(user)
    if user.role == Role.UNIVERSITY_ADMIN:
        return (prof.university_id if prof else -1), None
    if user.role == Role.COLLEGE_ADMIN:
        return None, (prof.college_id if prof else -1)
    return -1, -1


def scope_q(user, university_field, college_field, include_unscoped=False):
    """Q filter limiting a queryset to an admin's university/college.

    include_unscoped: also include rows whose university is NULL (e.g. NGO-hosted events),
    for university admins.
    """
    uni, col = admin_scope(user)
    if uni is None and col is None:
        return Q()
    if col is not None:
        return Q(**{college_field: col})
    q = Q(**{university_field: uni})
    if include_unscoped:
        q |= Q(**{f"{university_field}__isnull": True})
    return q


def admin_can_manage_event(user, event):
    if not is_admin(user):
        return False
    uni, col = admin_scope(user)
    if uni is None and col is None:
        return True
    if col is not None:
        return event.college_id == col
    return event.university_id == uni or event.university_id is None


def admin_can_manage_unit(user, unit):
    if not is_admin(user):
        return False
    uni, col = admin_scope(user)
    if uni is None and col is None:
        return True
    if col is not None:
        return unit.college_id == col
    return unit.university_id == uni


def can_manage_event(user, event):
    """Organizer of the event or an admin whose scope covers it."""
    if not (user and user.is_authenticated):
        return False
    return event.organizer_id == user.id or admin_can_manage_event(user, event)


class IsPlatformAdmin(BasePermission):
    message = "Administrator access required."

    def has_permission(self, request, view):
        return is_admin(request.user)


class IsSuperAdmin(BasePermission):
    message = "Super administrator access required."

    def has_permission(self, request, view):
        return is_super(request.user)


class IsVolunteer(BasePermission):
    message = "Only volunteer accounts can do this."

    def has_permission(self, request, view):
        return has_role(request.user, Role.VOLUNTEER)


class ReadOnlyOrAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or (request.user and request.user.is_authenticated)
