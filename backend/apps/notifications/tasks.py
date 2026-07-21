from celery import shared_task
from django.utils import timezone

from .models import PushSubscription


@shared_task
def retry_failed_push():
    """Placeholder sweep: reactivation of push subscriptions is manual today
    (user re-subscribes from settings). This task deactivates subscriptions
    that have gone stale (no successful send in 90 days) to keep the table clean."""
    cutoff = timezone.now() - timezone.timedelta(days=90)
    PushSubscription.objects.filter(is_active=True, last_seen_at__lt=cutoff).update(is_active=False)
