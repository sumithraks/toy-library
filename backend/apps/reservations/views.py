from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import IsOwnerOrStaff, IsStaff
from apps.inventory.models import Toy

from . import services
from .models import Reservation
from .serializers import CreateReservationSerializer, ReservationSerializer


class ReservationViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ReservationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]

    def get_queryset(self):
        qs = Reservation.objects.all()
        if self.request.user.is_staff:
            return qs
        return qs.filter(user=self.request.user)

    def get_permissions(self):
        if self.action == "confirm_pickup":
            return [IsStaff()]
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsOwnerOrStaff()]

    def create(self, request, *args, **kwargs):
        serializer = CreateReservationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        toy = Toy.objects.get(id=serializer.validated_data["toy"])
        try:
            reservation = services.create_reservation(
                toy, request.user, serializer.validated_data["pickup_by_date"]
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(reservation).data, status=201)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        reservation = self.get_object()
        try:
            reservation = services.cancel_reservation(reservation, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(reservation).data)

    @action(detail=True, methods=["post"], url_path="confirm-pickup")
    def confirm_pickup(self, request, pk=None):
        reservation = self.get_object()
        try:
            reservation = services.confirm_pickup(reservation, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(reservation).data)
