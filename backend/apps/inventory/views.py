from django.db.models import Count, Min, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import IsStaffOrReadOnly

from . import services
from .filters import ToyFilter
from .models import Toy, ToyStatusLog
from .serializers import (
    ToyIntakeSerializer,
    ToySerializer,
    ToyStatusLogSerializer,
    ToyTransitionSerializer,
)


class ToyViewSet(viewsets.ModelViewSet):
    serializer_class = ToySerializer
    queryset = Toy.objects.all()
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = ToyFilter
    search_fields = ["model_name", "make", "description", "barcode_or_sku"]

    @action(detail=False, methods=["get"])
    def groups(self, request):
        qs = self.filter_queryset(self.get_queryset())
        groups = (
            qs.values("make", "model_name")
            .annotate(
                total_count=Count("id"),
                available_count=Count("id", filter=Q(status=Toy.Status.AVAILABLE)),
                # Assumes all toys sharing a (make, model_name) share the same min_age_years;
                # not enforced at the model level, so a divergent value is silently picked as
                # the minimum rather than surfaced as an inconsistency.
                min_age_years=Min("min_age_years"),
            )
            .order_by("make", "model_name")
        )
        return Response(list(groups))

    @action(detail=False, methods=["post"])
    def intake(self, request):
        serializer = ToyIntakeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        toy = services.intake_purchased_toy(staff_user=request.user, **serializer.validated_data)
        return Response(self.get_serializer(toy).data, status=201)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        toy = self.get_object()
        serializer = ToyTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            toy = services.transition_toy_status(
                toy,
                serializer.validated_data["new_status"],
                actor=request.user,
                reason=serializer.validated_data.get("reason", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(toy).data)

    @action(detail=True, methods=["get"], url_path="status-log")
    def status_log(self, request, pk=None):
        toy = self.get_object()
        logs = toy.status_logs.all()
        return Response(ToyStatusLogSerializer(logs, many=True).data)
