import secrets

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import TimeStampedModel


def generate_qr_token():
    return secrets.token_urlsafe(32)


class EventQR(models.Model):
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="qr_codes")
    token = models.CharField(max_length=64, unique=True, default=generate_qr_token)
    expires_at = models.DateTimeField()
    active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Event QR"

    def __str__(self):
        return f"QR for {self.event} ({'active' if self.active else 'inactive'})"


class Attendance(TimeStampedModel):
    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        LATE = "LATE", "Late"
        ABSENT = "ABSENT", "Absent"

    volunteer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendance_records")
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="attendance_records")
    application = models.ForeignKey("events.EventApplication", on_delete=models.SET_NULL, null=True, blank=True, related_name="attendance_records")
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, db_index=True)
    qr = models.ForeignKey(EventQR, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["volunteer", "event"], name="uniq_attendance_per_volunteer_event")]

    def __str__(self):
        return f"{self.volunteer.email} @ {self.event.title}: {self.status}"


class VolunteerHours(models.Model):
    volunteer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hours_records")
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="hours_records")
    attendance = models.OneToOneField(Attendance, on_delete=models.CASCADE, related_name="hours_record")
    hours = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)])
    category = models.CharField(max_length=20, db_index=True)  # copy of event.category at time of participation
    verified = models.BooleanField(default=False, help_text="Finalised after mandatory feedback is submitted.")
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "volunteer hours"
        constraints = [models.UniqueConstraint(fields=["volunteer", "event"], name="uniq_hours_per_volunteer_event")]

    def __str__(self):
        return f"{self.volunteer.email}: {self.hours}h ({self.category})"


class Feedback(models.Model):
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="feedback")
    volunteer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feedback_given")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comments = models.TextField(blank=True, max_length=2000)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [models.UniqueConstraint(fields=["volunteer", "event"], name="uniq_feedback_per_volunteer_event")]

    def __str__(self):
        return f"{self.volunteer.email} rated {self.event.title}: {self.rating}"
