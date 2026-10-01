"""Single entry point for creating notifications (DB row + optional email)."""
import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Notification

logger = logging.getLogger(__name__)


def send_email(to, subject, body):
    """Send an email via the configured Django backend. Never raises to the caller."""
    if not to:
        return False
    recipients = [to] if isinstance(to, str) else list(to)
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
        return True
    except Exception:  # SMTP outages must not break the business workflow
        logger.exception("Email to %s failed", recipients)
        return False


def notify(recipient, notification_type, title, message, link="", email=False, email_body=None):
    if recipient is None or not recipient.is_active:
        return None
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title[:200],
        message=message,
        link=link,
    )
    if email:
        body = email_body or message
        if link:
            from core.utils import frontend_base_url

            body += f"\n\nOpen in NSS Connect: {frontend_base_url()}{link}"
        send_email(recipient.email, f"[NSS Connect] {title}", body)
    return notification


def notify_many(recipients, notification_type, title, message, link="", email=False):
    created = 0
    for user in recipients:
        if notify(user, notification_type, title, message, link=link, email=email):
            created += 1
    return created
