from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import IsStaff

from . import services
from .models import LedgerEntry
from .serializers import LedgerEntrySerializer


class LedgerEntryViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = LedgerEntrySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "entry_type"]

    def get_queryset(self):
        qs = LedgerEntry.objects.all().order_by("-created_at")
        if not self.request.user.is_staff:
            return qs.filter(user=self.request.user)

        user_param = self.request.query_params.get("user")
        if user_param and user_param != "me":
            qs = qs.filter(user=user_param)
        return qs

    def get_permissions(self):
        if self.action == "mark_paid":
            return [IsStaff()]
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        entry = self.get_object()
        try:
            entry = services.mark_paid(entry, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(entry).data)
