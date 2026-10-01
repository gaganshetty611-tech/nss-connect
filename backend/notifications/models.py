from django.conf import settings
from django.db import models


class NotificationType(models.TextChoices):
    APPLICATION_CREATED = "APPLICATION_CREATED", "Application created"
    APPLICATION_APPROVED = "APPLICATION_APPROVED", "Application approved"
    APPLICATION_REJECTED = "APPLICATION_REJECTED", "Application rejected"
    APPLICATION_WAITLISTED = "APPLICATION_WAITLISTED", "Application waitlisted"
    APPLICATION_CANCELLED = "APPLICATION_CANCELLED", "Application cancelled"
    EVENT_APPROVED = "EVENT_APPROVED", "Event approved"
    EVENT_REJECTED = "EVENT_REJECTED", "Event rejected"
    EVENT_REMINDER = "EVENT_REMINDER", "Event reminder"
    EVENT_UPDATED = "EVENT_UPDATED", "Event updated"
    ATTENDANCE_CONFIRMED = "ATTENDANCE_CONFIRMED", "Attendance confirmed"
    CERTIFICATE_GENERATED = "CERTIFICATE_GENERATED", "Certificate generated"
    NGO_VERIFIED = "NGO_VERIFIED", "NGO verified"
    NGO_STATUS_CHANGED = "NGO_STATUS_CHANGED", "NGO status changed"
    NSS_UNIT_VERIFIED = "NSS_UNIT_VERIFIED", "NSS unit verified"
    NSS_UNIT_STATUS_CHANGED = "NSS_UNIT_STATUS_CHANGED", "NSS unit status changed"
    NSS_INVITATION = "NSS_INVITATION", "NSS invitation"
    GROUP_APPLICATION = "GROUP_APPLICATION", "Group application"
    EMERGENCY_REQUEST = "EMERGENCY_REQUEST", "Emergency request"
    FEEDBACK_REQUIRED = "FEEDBACK_REQUIRED", "Feedback required"


class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=32, choices=NotificationType.choices, db_index=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=300, blank=True, help_text="Frontend path, e.g. /events/12")
    read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "read"])]

    def __str__(self):
        return f"{self.notification_type} → {self.recipient.email}"
