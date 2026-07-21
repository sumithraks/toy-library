from rest_framework.routers import DefaultRouter

from django.urls import path

from . import views

router = DefaultRouter()
router.register("notifications", views.NotificationLogViewSet, basename="notification")
router.register("push-subscriptions", views.PushSubscriptionViewSet, basename="push-subscription")

urlpatterns = [
    path(
        "notification-preferences/me/",
        views.NotificationPreferenceView.as_view(),
        name="notification-preferences-me",
    ),
] + router.urls
