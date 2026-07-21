from celery import shared_task

from . import services


@shared_task
def expire_reservations():
    services.expire_reservations()


@shared_task
def send_reservation_reminders():
    services.send_reservation_reminders()
