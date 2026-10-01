from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from core.models import TimeStampedModel
from core.validators import SafeUploadTo, validate_image_file


class EventCategory(models.TextChoices):
    ABP1 = "ABP1", "ABP 1"
    ABP2 = "ABP2", "ABP 2"
    COLLEGE_EVENT = "COLLEGE_EVENT", "College Event"
    UNIVERSITY_EVENT = "UNIVERSITY_EVENT", "University Event"


class EventTheme(models.TextChoices):
    """Finer-grained theme (used by AI categorisation). ABP1 = Environmental & Community Service,
    ABP2 = Health, Education & Awareness (per the NSS Connect proposal)."""

    ENVIRONMENT = "ENVIRONMENT", "Environment"
    COMMUNITY = "COMMUNITY", "Community Service"
    HEALTH = "HEALTH", "Health"
    EDUCATION = "EDUCATION", "Education"
    AWARENESS = "AWARENESS", "Awareness"
    OTHER = "OTHER", "Other"


THEME_TO_ABP = {
    EventTheme.ENVIRONMENT: EventCategory.ABP1,
    EventTheme.COMMUNITY: EventCategory.ABP1,
    EventTheme.HEALTH: EventCategory.ABP2,
    EventTheme.EDUCATION: EventCategory.ABP2,
    EventTheme.AWARENESS: EventCategory.ABP2,
}


class EventStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    ONGOING = "ONGOING", "Ongoing"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


# Statuses visible to the public. PENDING/REJECTED/CANCELLED are private.
PUBLIC_EVENT_STATUSES = [EventStatus.APPROVED, EventStatus.ONGOING, EventStatus.COMPLETED]


class EventSkill(models.Model):
    name = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = self.name.strip().title()
        super().save(*args, **kwargs)


class Event(TimeStampedModel):
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=EventCategory.choices, db_index=True)
    theme = models.CharField(max_length=20, choices=EventTheme.choices, default=EventTheme.OTHER, db_index=True)
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="organized_events")
    ngo = models.ForeignKey("ngos.NGO", on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    nss_unit = models.ForeignKey("nss_units.NSSUnit", on_delete=models.SET_NULL, null=True, blank=True, related_name="hosted_events")
    college = models.ForeignKey("nss_units.College", on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    university = models.ForeignKey("nss_units.University", on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    maximum_volunteers = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    required_skills = models.ManyToManyField(EventSkill, blank=True, related_name="events")
    requirements = models.TextField(blank=True)
    meeting_point = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20, blank=True)
    event_image = models.ImageField(upload_to=SafeUploadTo("events"), blank=True, null=True, validators=[validate_image_file])
    instructions = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=EventStatus.choices, default=EventStatus.PENDING, db_index=True)
    review_note = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_events"
    )
    organizer_notes = models.TextField(blank=True, help_text="Post-event notes used for the summary report.")
    summary = models.TextField(blank=True, help_text="Post-event summary (generated, editable).")

    class Meta:
        ordering = ["date", "start_time"]
        indexes = [
            models.Index(fields=["status", "date"]),
            models.Index(fields=["category", "status"]),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(maximum_volunteers__gte=1), name="event_max_volunteers_positive"),
        ]

    def __str__(self):
        return self.title

    @property
    def organizer_display(self):
        if self.ngo_id:
            return self.ngo.name
        if self.nss_unit_id:
            return str(self.nss_unit)
        return self.organizer.display_name

    @property
    def is_public(self):
        return self.status in PUBLIC_EVENT_STATUSES


class ApplicationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    WAITLISTED = "WAITLISTED", "Waitlisted"
    CANCELLED = "CANCELLED", "Cancelled"
    COMPLETED = "COMPLETED", "Completed"


ACTIVE_APPLICATION_STATUSES = [ApplicationStatus.PENDING, ApplicationStatus.APPROVED, ApplicationStatus.WAITLISTED, ApplicationStatus.COMPLETED]


class EventApplication(TimeStampedModel):
    volunteer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="applications")
    college = models.ForeignKey("nss_units.College", on_delete=models.SET_NULL, null=True, blank=True)
    nss_unit = models.ForeignKey("nss_units.NSSUnit", on_delete=models.SET_NULL, null=True, blank=True, related_name="member_applications")
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    skills = models.ManyToManyField(EventSkill, blank=True)
    motivation = models.TextField(blank=True, max_length=1000)
    application_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=12, choices=ApplicationStatus.choices, default=ApplicationStatus.PENDING, db_index=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-application_date"]
        constraints = [models.UniqueConstraint(fields=["volunteer", "event"], name="uniq_application_per_volunteer_event")]

    def __str__(self):
        return f"{self.volunteer.email} → {self.event.title} ({self.status})"


class GroupApplication(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    nss_unit = models.ForeignKey("nss_units.NSSUnit", on_delete=models.CASCADE, related_name="group_applications")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="group_applications")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    requested_volunteer_count = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    skills = models.ManyToManyField(EventSkill, blank=True)
    message = models.TextField(blank=True, max_length=2000)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["nss_unit", "event"], name="uniq_group_application")]

    def __str__(self):
        return f"{self.nss_unit} → {self.event} ({self.status})"


class EventPhoto(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="photos")
    photo = models.ImageField(upload_to=SafeUploadTo("gallery"), validators=[validate_image_file])
    caption = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    # Real evidence location, per the "geo-tagged photograph" requirement — set from
    # either the uploader's browser Geolocation API (preferred, since it reflects where
    # the phone actually is right now) or the photo's own EXIF GPS tags as a fallback
    # (see events/views.py EventViewSet.photos / core/utils.py extract_exif_gps).
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_source = models.CharField(
        max_length=10,
        choices=[("DEVICE", "Uploader's device"), ("EXIF", "Photo metadata"), ("", "Not available")],
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]


class EmergencyVolunteerRequest(models.Model):
    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    title = models.CharField(max_length=200)
    description = models.TextField()
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True, related_name="emergency_requests")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    required_volunteers = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    required_skills = models.ManyToManyField(EventSkill, blank=True)
    location = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.HIGH)
    notified_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
