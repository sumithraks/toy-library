from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import IsStaff

from . import services
from .models import Donation, DonationItem
from .serializers import (
    CompleteIntakeSerializer,
    DonationRejectSerializer,
    DonationReceiptSerializer,
    DonationSerializer,
    DonationSubmitSerializer,
)


class DonationViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = (
        Donation.objects.select_related("donor").prefetch_related("items").order_by("-donated_at")
    )
    serializer_class = DonationSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_staff:
            return qs
        return qs.filter(donor__user=self.request.user)

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        if self.action in ("accept", "reject", "complete_item_intake"):
            return [IsStaff()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = DonationSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submitting_user = request.user if request.user.is_authenticated else None
        donation = services.submit_donation(
            serializer.validated_data["donor"], serializer.validated_data["items"], user=submitting_user
        )
        return Response(DonationSerializer(donation).data, status=201)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        donation = self.get_object()
        try:
            donation = services.accept_donation(donation, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(DonationSerializer(donation).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        donation = self.get_object()
        serializer = DonationRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            donation = services.reject_donation(donation, serializer.validated_data["reason"])
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(DonationSerializer(donation).data)

    @action(detail=True, methods=["post"], url_path="items/(?P<item_id>[^/.]+)/complete-intake")
    def complete_item_intake(self, request, pk=None, item_id=None):
        donation = self.get_object()
        item = donation.items.get(id=item_id)
        serializer = CompleteIntakeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            toy = services.complete_item_intake(item, request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        from apps.inventory.serializers import ToySerializer

        return Response(ToySerializer(toy).data, status=201)

    @action(detail=True, methods=["get"])
    def receipt(self, request, pk=None):
        donation = self.get_object()
        if not hasattr(donation, "receipt"):
            return Response({"detail": "No receipt issued yet"}, status=404)
        return Response(DonationReceiptSerializer(donation.receipt).data)
