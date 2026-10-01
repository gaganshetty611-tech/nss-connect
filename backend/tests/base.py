import tempfile
from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, User
from events.models import Event, EventStatus
from ngos.models import NGO
from nss_units.models import College, NSSUnit, University, VerificationStatus

MEDIA = tempfile.mkdtemp(prefix="nss-test-media-")
PASSWORD = "Str0ng!Passw0rd"


@override_settings(
    MEDIA_ROOT=MEDIA,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_URL="https://nss.example.test",
    REQUIRE_EMAIL_VERIFICATION=True,
)
class BaseAPITest(APITestCase):
    def setUp(self):
        cache.clear()  # reset throttling counters between tests
        self.uni = University.objects.create(name="University of Mumbai")
        self.college = College.objects.create(university=self.uni, name="SIES College", latitude=Decimal("19.0433"), longitude=Decimal("72.8633"))
        self.super = self.make_user("super@test.in", Role.SUPER_ADMIN)
        self.coordinator = self.make_user("coord@test.in", Role.NSS_COORDINATOR)
        self.unit = NSSUnit.objects.create(college=self.college, unit_number="1", coordinator=self.coordinator,
                                           latitude=Decimal("19.0433"), longitude=Decimal("72.8633"),
                                           verification_status=VerificationStatus.VERIFIED)
        self.organizer = self.make_user("org@test.in", Role.NGO_ORGANIZER)
        self.ngo = NGO.objects.create(owner=self.organizer, name="Green Test NGO", email="ngo@test.in",
                                      verification_status=VerificationStatus.VERIFIED, latitude=Decimal("19.05"), longitude=Decimal("72.85"))
        self.volunteer = self.make_user("vol@test.in", Role.VOLUNTEER)
        vp = self.volunteer.volunteer_profile
        vp.nss_unit = self.unit
        vp.save()
        self.volunteer.profile.college = self.college
        self.volunteer.profile.university = self.uni
        self.volunteer.profile.save()

    def make_user(self, email, role, verified=True, **extra):
        return User.objects.create_user(username=email, email=email, password=PASSWORD, role=role,
                                        first_name=email.split("@")[0].title(), is_email_verified=verified, **extra)

    def make_event(self, organizer=None, status=EventStatus.APPROVED, starts_in=timedelta(days=3), duration=timedelta(hours=3), **kw):
        start = timezone.localtime(timezone.now() + starts_in)
        end = start + duration
        defaults = dict(
            title="Beach Clean-up", description="Cleanup drive at the beach", category="ABP1",
            organizer=organizer or self.organizer, ngo=self.ngo if (organizer or self.organizer) == self.organizer else None,
            date=start.date(), start_time=start.time().replace(microsecond=0), end_time=end.time().replace(microsecond=0),
            location="Juhu Beach", latitude=Decimal("19.0988"), longitude=Decimal("72.8265"), maximum_volunteers=5,
            contact_email="org@test.in", status=status,
        )
        defaults.update(kw)
        return Event.objects.create(**defaults)

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def login(self, email, password=PASSWORD):
        self.client.force_authenticate(user=None)
        res = self.client.post("/api/auth/login/", {"email": email, "password": password}, format="json")
        if res.status_code == 200:
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res
