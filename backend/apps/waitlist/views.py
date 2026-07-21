from rest_framework import mixins, viewsets
from rest_framework.response import Response

from apps.inventory.models import Toy

from . import services
from .models import WaitlistEntry
from .serializers import JoinWaitlistSerializer, WaitlistEntrySerializer


class WaitlistViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = WaitlistEntrySerializer

    def get_queryset(self):
        qs = WaitlistEntry.objects.all()
        if self.request.user.is_staff:
            return qs
        return qs.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = JoinWaitlistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        toy = Toy.objects.get(id=serializer.validated_data["toy"])
        try:
            entry = services.join_waitlist(toy, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(WaitlistEntrySerializer(entry).data, status=201)

    def destroy(self, request, *args, **kwargs):
        entry = self.get_object()
        try:
            services.leave_waitlist(entry)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(status=204)
