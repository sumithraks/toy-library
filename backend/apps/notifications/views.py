from django.utils import timezone
from rest_framework import generics, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import NotificationLog, NotificationPreference, PushSubscription
from .serializers import (
    NotificationLogSerializer,
    NotificationPreferenceSerializer,
    PushSubscriptionSerializer,
)


class NotificationLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationLogSerializer

    def get_queryset(self):
        return NotificationLog.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        log = self.get_object()
        log.read_at = timezone.now()
        log.save(update_fields=["read_at"])
        return Response(self.get_serializer(log).data)


class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    serializer_class = NotificationPreferenceSerializer

    def get_object(self):
        preference, _ = NotificationPreference.objects.get_or_create(user=self.request.user)
        return preference


class PushSubscriptionViewSet(
    mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    serializer_class = PushSubscriptionSerializer

    def get_queryset(self):
        return PushSubscription.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription, _ = PushSubscription.objects.update_or_create(
            endpoint=serializer.validated_data["endpoint"],
            defaults={
                **serializer.validated_data,
                "user": request.user,
                "is_active": True,
            },
        )
        return Response(self.get_serializer(subscription).data, status=201)
