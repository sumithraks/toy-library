import json
import logging

from django.conf import settings
from django.core.mail import send_mail
from pywebpush import WebPushException, webpush

from .models import CATEGORY_BY_EVENT_TYPE, NotificationLog, NotificationPreference, PushSubscription

logger = logging.getLogger(__name__)


def _get_or_create_preference(user):
    preference, _ = NotificationPreference.objects.get_or_create(user=user)
    return preference


def notify(user, event_type, title, body, action_url=None):
    preference = _get_or_create_preference(user)
    category = CATEGORY_BY_EVENT_TYPE.get(event_type)
    category_enabled = getattr(preference, category, True) if category else True

    NotificationLog.objects.create(
        user=user,
        event_type=event_type,
        channel=NotificationLog.Channel.IN_APP,
        title=title,
        body=body,
        action_url=action_url or "",
    )

    if category_enabled and preference.email_enabled:
        _send_email(user, title, body, action_url)
        NotificationLog.objects.create(
            user=user,
            event_type=event_type,
            channel=NotificationLog.Channel.EMAIL,
            title=title,
            body=body,
            action_url=action_url or "",
        )

    if category_enabled and preference.push_enabled:
        sent = _send_push(user, title, body, action_url)
        if sent:
            NotificationLog.objects.create(
                user=user,
                event_type=event_type,
                channel=NotificationLog.Channel.PUSH,
                title=title,
                body=body,
                action_url=action_url or "",
            )


def _send_email(user, title, body, action_url):
    if not user.email:
        return
    full_body = body
    if action_url:
        full_body = f"{body}\n\n{settings.FRONTEND_BASE_URL}{action_url}"
    try:
        send_mail(title, full_body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
    except Exception:
        logger.exception("Failed to send notification email to %s", user.email)


def _send_push(user, title, body, action_url):
    if not settings.VAPID_PRIVATE_KEY:
        return False
    subscriptions = PushSubscription.objects.filter(user=user, is_active=True)
    sent_any = False
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh_key, "auth": subscription.auth_key},
                },
                data=json.dumps({"title": title, "body": body, "url": action_url}),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{settings.VAPID_ADMIN_EMAIL}"},
            )
            sent_any = True
        except WebPushException as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code in (404, 410):
                subscription.is_active = False
                subscription.save(update_fields=["is_active", "updated_at"])
            else:
                logger.warning("Push send failed for %s: %s", user, exc)
    return sent_any
