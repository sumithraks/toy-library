from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import IsOwnerOrStaff, IsStaff
from apps.inventory.models import Toy

from . import services
from .models import CheckoutRecord
from .serializers import (
    CheckoutRecordSerializer,
    ComplimentaryExtensionSerializer,
    CreateCheckoutSerializer,
    ExtensionSerializer,
    PaidExtensionSerializer,
    ReturnCheckoutSerializer,
)

User = get_user_model()


class CheckoutViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = CheckoutRecordSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "member", "toy"]

    def get_queryset(self):
        qs = CheckoutRecord.objects.all()
        if self.request.user.is_staff:
            return qs
        return qs.filter(member=self.request.user)

    def get_permissions(self):
        if self.action in ("create", "return_toy"):
            return [IsStaff()]
        if self.action in ("extend_paid",):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsOwnerOrStaff()]

    def create(self, request, *args, **kwargs):
        serializer = CreateCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        toy = Toy.objects.get(id=serializer.validated_data["toy"])
        member = User.objects.get(id=serializer.validated_data["member"])
        try:
            checkout = services.create_checkout(toy, member, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(checkout).data, status=201)

    @action(detail=True, methods=["post"], url_path="return")
    def return_toy(self, request, pk=None):
        checkout = self.get_object()
        serializer = ReturnCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            checkout = services.return_checkout(
                checkout,
                serializer.validated_data["condition"],
                request.user,
                damaged_status=serializer.validated_data.get("damaged_status"),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(checkout).data)

    @action(detail=True, methods=["post"], url_path="extend/complimentary")
    def extend_complimentary(self, request, pk=None):
        checkout = self.get_object()
        try:
            checkout = services.apply_complimentary_extension(checkout, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(checkout).data)

    @action(detail=True, methods=["post"], url_path="extend/paid")
    def extend_paid(self, request, pk=None):
        checkout = self.get_object()
        serializer = PaidExtensionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            extension = services.apply_paid_extension(checkout, serializer.validated_data["days"], request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(ExtensionSerializer(extension).data, status=201)

    @action(detail=True, methods=["get"])
    def extensions(self, request, pk=None):
        checkout = self.get_object()
        return Response(ExtensionSerializer(checkout.extensions.all(), many=True).data)
