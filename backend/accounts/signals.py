from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Role, User, UserProfile, VolunteerProfile


@receiver(post_save, sender=User)
def ensure_profiles(sender, instance, created, **kwargs):
    UserProfile.objects.get_or_create(user=instance)
    if instance.role == Role.VOLUNTEER:
        VolunteerProfile.objects.get_or_create(user=instance)


@receiver(pre_save, sender=VolunteerProfile)
def remember_old_unit(sender, instance, **kwargs):
    old = None
    if instance.pk:
        old = VolunteerProfile.objects.filter(pk=instance.pk).values_list("nss_unit_id", flat=True).first()
    instance._old_unit_id = old


@receiver(post_save, sender=VolunteerProfile)
def sync_unit_counts(sender, instance, **kwargs):
    from nss_units.models import NSSUnit

    for unit_id in {getattr(instance, "_old_unit_id", None), instance.nss_unit_id} - {None}:
        unit = NSSUnit.objects.filter(pk=unit_id).first()
        if unit:
            unit.refresh_volunteer_count()


@receiver(post_delete, sender=VolunteerProfile)
def sync_unit_counts_on_delete(sender, instance, **kwargs):
    from nss_units.models import NSSUnit

    unit = NSSUnit.objects.filter(pk=instance.nss_unit_id).first() if instance.nss_unit_id else None
    if unit:
        unit.refresh_volunteer_count()
