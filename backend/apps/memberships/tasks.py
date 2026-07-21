from celery import shared_task
from django.utils import timezone

from apps.notifications.services import notify

from .models import Membership

RENEWAL_REMINDER_DAYS_BEFORE = 14


@shared_task
def send_renewal_reminders():
    target_date = timezone.now().date() + timezone.timedelta(days=RENEWAL_REMINDER_DAYS_BEFORE)
    memberships = Membership.objects.filter(
        status=Membership.Status.ACTIVE, renewed_through=target_date
    ).select_related("user", "tier")
    for membership in memberships:
        notify(
            membership.user,
            event_type="MEMBERSHIP_RENEWAL_DUE",
            title="Your Toy Library membership renews soon",
            body=f"Renewal fee: ${membership.tier.renewal_fee}. Renews on {membership.renewed_through}.",
            action_url="/membership",
        )
