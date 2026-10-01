import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.validators import SafeUploadTo


def generate_certificate_id():
    return f"NSSC-{timezone.now().year}-{secrets.token_hex(4).upper()}"


def generate_verification_token():
    return secrets.token_urlsafe(24)


class Certificate(models.Model):
    certificate_id = models.CharField(max_length=32, unique=True, default=generate_certificate_id, db_index=True)
    volunteer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificates")
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="certificates")
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to=SafeUploadTo("certificates"), blank=True)
    verification_token = models.CharField(max_length=64, unique=True, default=generate_verification_token)
    verify_url = models.URLField(max_length=500, blank=True)
    revoked = models.BooleanField(default=False)

    class Meta:
        ordering = ["-issued_at"]
        constraints = [models.UniqueConstraint(fields=["volunteer", "event"], name="uniq_certificate_per_volunteer_event")]

    def __str__(self):
        return f"{self.certificate_id} – {self.volunteer.email}"
