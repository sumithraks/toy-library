from celery import shared_task
from django.utils import timezone

from . import services
from .models import CheckoutRecord


@shared_task
def assess_late_fees():
    services.assess_late_fees()


@shared_task
def send_due_date_reminders():
    from apps.notifications.services import notify

    today = timezone.now().date()
    reminder_offsets = [3, 1]
    for offset in reminder_offsets:
        target_date = today + timezone.timedelta(days=offset)
        checkouts = CheckoutRecord.objects.filter(
            status=CheckoutRecord.Status.ACTIVE, current_due_date=target_date
        ).select_related("member", "toy")
        for checkout in checkouts:
            complimentary_available = not checkout.complimentary_extension_used
            notify(
                checkout.member,
                event_type="DUE_DATE_REMINDER",
                title=f"'{checkout.toy}' is due in {offset} day(s)",
                body=(
                    "You're eligible for a free extension."
                    if complimentary_available
                    else "Request a paid extension if you need more time."
                ),
                action_url=f"/checkouts?highlight={checkout.id}",
            )
