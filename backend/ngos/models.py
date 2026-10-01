from django.conf import settings
from django.db import models

from core.models import TimeStampedModel
from core.validators import SafeUploadTo, validate_document_file, validate_image_file
from nss_units.models import VerificationStatus


class NGO(TimeStampedModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="ngos")
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to=SafeUploadTo("ngo_logos"), blank=True, null=True, validators=[validate_image_file])
    location = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    focus_areas = models.JSONField(default=list, blank=True, help_text='e.g. ["ENVIRONMENT", "HEALTH"]')
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    registration_number = models.CharField(max_length=80, blank=True)
    verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=12, choices=VerificationStatus.choices, default=VerificationStatus.PENDING, db_index=True
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "NGO"
        verbose_name_plural = "NGOs"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.verified = self.verification_status == VerificationStatus.VERIFIED
        super().save(*args, **kwargs)


class VerificationDocument(models.Model):
    class DocumentType(models.TextChoices):
        REGISTRATION_CERTIFICATE = "REGISTRATION_CERTIFICATE", "Registration Certificate"
        PAN = "PAN", "PAN Card"
        TAX_EXEMPTION_12A = "12A", "12A Certificate"
        TAX_EXEMPTION_80G = "80G", "80G Certificate"
        FCRA = "FCRA", "FCRA Registration"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    ngo = models.ForeignKey(NGO, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    file = models.FileField(upload_to=SafeUploadTo("ngo_documents"), validators=[validate_document_file])
    original_filename = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_documents"
    )
    review_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.ngo.name} – {self.get_document_type_display()}"
