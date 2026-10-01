from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

from core.models import TimeStampedModel
from core.validators import SafeUploadTo, validate_image_file


class Role(models.TextChoices):
    VOLUNTEER = "VOLUNTEER", "Volunteer"
    NSS_COORDINATOR = "NSS_COORDINATOR", "NSS Coordinator"
    NGO_ORGANIZER = "NGO_ORGANIZER", "NGO Organizer"
    COLLEGE_ADMIN = "COLLEGE_ADMIN", "College Admin"
    UNIVERSITY_ADMIN = "UNIVERSITY_ADMIN", "University Admin"
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"


ADMIN_ROLES = {Role.COLLEGE_ADMIN, Role.UNIVERSITY_ADMIN, Role.SUPER_ADMIN}
SELF_REGISTER_ROLES = {Role.VOLUNTEER, Role.NSS_COORDINATOR, Role.NGO_ORGANIZER}


class Gender(models.TextChoices):
    MALE = "MALE", "Male"
    FEMALE = "FEMALE", "Female"
    OTHER = "OTHER", "Other"
    UNDISCLOSED = "UNDISCLOSED", "Prefer not to say"


class NSSUserManager(UserManager):
    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.SUPER_ADMIN)
        extra_fields.setdefault("is_email_verified", True)
        return super().create_superuser(username or email, email, password, **extra_fields)


class User(AbstractUser):
    """Custom user. Login is by email; `username` is kept for Django admin compatibility."""

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VOLUNTEER, db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=12, choices=Gender.choices, default=Gender.UNDISCLOSED)
    is_email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = NSSUserManager()

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.get_full_name() or self.email} ({self.role})"

    @property
    def is_platform_admin(self):
        return self.role in ADMIN_ROLES or self.is_superuser

    @property
    def is_super_admin(self):
        return self.role == Role.SUPER_ADMIN or self.is_superuser

    @property
    def display_name(self):
        return self.get_full_name() or self.email


class UserProfile(TimeStampedModel):
    """Common profile for every user (photo, location, institutional affiliation)."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    photo = models.ImageField(upload_to=SafeUploadTo("profiles"), blank=True, null=True, validators=[validate_image_file])
    bio = models.TextField(blank=True, max_length=1000)
    city = models.CharField(max_length=120, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    # Admin scope + volunteer affiliation
    university = models.ForeignKey("nss_units.University", on_delete=models.SET_NULL, null=True, blank=True, related_name="user_profiles")
    college = models.ForeignKey("nss_units.College", on_delete=models.SET_NULL, null=True, blank=True, related_name="user_profiles")

    def __str__(self):
        return f"Profile of {self.user.email}"


class VolunteerProfile(TimeStampedModel):
    WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="volunteer_profile")
    nss_unit = models.ForeignKey("nss_units.NSSUnit", on_delete=models.SET_NULL, null=True, blank=True, related_name="volunteers")
    roll_number = models.CharField(max_length=40, blank=True)
    year_of_study = models.PositiveSmallIntegerField(null=True, blank=True)
    skills = models.ManyToManyField("events.EventSkill", blank=True, related_name="volunteers")
    # Interest areas: event categories (ABP1/ABP2/...) and/or themes (ENVIRONMENT, HEALTH, ...)
    interests = models.JSONField(default=list, blank=True)
    # Weekdays the volunteer is generally available, e.g. ["SAT", "SUN"]
    availability = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Volunteer {self.user.email}"
