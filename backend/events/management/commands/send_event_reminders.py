"""Send EVENT_REMINDER notifications + emails for approved registrations of drives happening tomorrow.

Schedule daily, e.g. cron:  0 18 * * *  cd backend && python manage.py send_event_reminders
Idempotent: a volunteer gets at most one reminder per event.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from events.models import ApplicationStatus, EventApplication, EventStatus
from notifications.models import Notification, NotificationType
from notifications.services import notify


class Command(BaseCommand):
    help = "Send reminders for drives happening in the next N days (default 1)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=1)

    def handle(self, *args, days, **options):
        today = timezone.localdate()
        apps = EventApplication.objects.filter(
            status=ApplicationStatus.APPROVED,
            event__status=EventStatus.APPROVED,
            event__date__gt=today,
            event__date__lte=today + timedelta(days=days),
        ).select_related("event", "volunteer")
        sent = 0
        for app in apps:
            e = app.event
            link = f"/events/{e.id}"
            if Notification.objects.filter(recipient=app.volunteer, notification_type=NotificationType.EVENT_REMINDER, link=link).exists():
                continue
            notify(app.volunteer, NotificationType.EVENT_REMINDER, f"Reminder: {e.title}",
                   f"{e.title} is on {e.date:%a %d %b} at {e.start_time:%H:%M}, {e.location}."
                   + (f" Meeting point: {e.meeting_point}." if e.meeting_point else "")
                   + " Scan the event QR at the venue to check in.", link=link, email=True)
            sent += 1
        self.stdout.write(self.style.SUCCESS(f"Sent {sent} reminder(s)."))
