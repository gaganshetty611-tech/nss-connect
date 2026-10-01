from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class VerificationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"
    SUSPENDED = "SUSPENDED", "Suspended"


class University(TimeStampedModel):
    name = models.CharField(max_length=200, unique=True)
    short_name = models.CharField(max_length=40, blank=True)
    city = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "universities"

    def __str__(self):
        return self.name


class College(TimeStampedModel):
    university = models.ForeignKey(University, on_delete=models.PROTECT, related_name="colleges")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=40, blank=True)
    city = models.CharField(max_length=120, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["university", "name"], name="uniq_college_per_university")]

    def __str__(self):
        return self.name


class NSSUnit(TimeStampedModel):
    college = models.ForeignKey(College, on_delete=models.PROTECT, related_name="nss_units")
    university = models.ForeignKey(University, on_delete=models.PROTECT, related_name="nss_units")
    unit_number = models.CharField(max_length=40)
    coordinator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinated_units"
    )
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    volunteer_count = models.PositiveIntegerField(default=0, help_text="Kept in sync with linked volunteer profiles.")
    verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=12, choices=VerificationStatus.choices, default=VerificationStatus.PENDING, db_index=True
    )

    class Meta:
        ordering = ["college__name", "unit_number"]
        constraints = [models.UniqueConstraint(fields=["college", "unit_number"], name="uniq_unit_per_college")]

    def __str__(self):
        return f"{self.college.name} – NSS Unit {self.unit_number}"

    def save(self, *args, **kwargs):
        if self.college_id and not self.university_id:
            self.university_id = self.college.university_id
        self.verified = self.verification_status == VerificationStatus.VERIFIED
        super().save(*args, **kwargs)

    def refresh_volunteer_count(self):
        count = self.volunteers.filter(user__is_active=True).count()
        NSSUnit.objects.filter(pk=self.pk).update(volunteer_count=count)
        self.volunteer_count = count
