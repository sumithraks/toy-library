from django.core.management.base import BaseCommand
from django_celery_beat.models import IntervalSchedule, PeriodicTask

SCHEDULE = [
    dict(name="Assess late fees", task="apps.checkouts.tasks.assess_late_fees", every=1, period=IntervalSchedule.HOURS),
    dict(name="Send due date reminders", task="apps.checkouts.tasks.send_due_date_reminders", every=1, period=IntervalSchedule.DAYS),
    dict(name="Expire reservations", task="apps.reservations.tasks.expire_reservations", every=15, period=IntervalSchedule.MINUTES),
    dict(name="Send reservation reminders", task="apps.reservations.tasks.send_reservation_reminders", every=15, period=IntervalSchedule.MINUTES),
    dict(name="Send renewal reminders", task="apps.memberships.tasks.send_renewal_reminders", every=1, period=IntervalSchedule.DAYS),
    dict(name="Retry failed push", task="apps.notifications.tasks.retry_failed_push", every=15, period=IntervalSchedule.MINUTES),
]


class Command(BaseCommand):
    help = "Seed django-celery-beat periodic tasks for the toy library background jobs."

    def handle(self, *args, **options):
        for entry in SCHEDULE:
            schedule, _ = IntervalSchedule.objects.get_or_create(
                every=entry["every"], period=entry["period"]
            )
            PeriodicTask.objects.update_or_create(
                name=entry["name"],
                defaults={"task": entry["task"], "interval": schedule, "enabled": True},
            )
            self.stdout.write(self.style.SUCCESS(f"Seeded: {entry['name']}"))
