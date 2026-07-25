from django.db.models import Count, Min, Q
from django_filters.rest_framework import DjangoFilterBackend
from pgvector.django import CosineDistance
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import IsStaffOrReadOnly

from . import embeddings, services, vision
from .filters import ToyFilter
from .models import Toy, ToyStatusLog
from .serializers import (
    ToyIdentifyImageSerializer,
    ToyIntakeSerializer,
    ToySerializer,
    ToyStatusLogSerializer,
    ToyTransitionSerializer,
)

SEMANTIC_SEARCH_RESULT_LIMIT = 20


class ToyViewSet(viewsets.ModelViewSet):
    serializer_class = ToySerializer
    queryset = Toy.objects.all()
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = ToyFilter
    search_fields = ["model_name", "make", "description", "barcode_or_sku"]

    def perform_update(self, serializer):
        description_changed = (
            "description" in serializer.validated_data
            and serializer.validated_data["description"] != serializer.instance.description
        )
        toy = serializer.save()
        if description_changed:
            services.embed_toy_description(toy)

    @action(detail=False, methods=["get"], url_path="semantic-search")
    def semantic_search(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"detail": "q query parameter is required"}, status=400)
        try:
            query_vector = embeddings.embed_text(query, input_type="query")
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        except Exception:
            return Response({"detail": "Semantic search is temporarily unavailable."}, status=502)

        qs = (
            self.filter_queryset(self.get_queryset())
            .exclude(description_embedding__isnull=True)
            .annotate(similarity_distance=CosineDistance("description_embedding", query_vector))
            .order_by("similarity_distance")[:SEMANTIC_SEARCH_RESULT_LIMIT]
        )
        return Response(self.get_serializer(qs, many=True).data)

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

    @action(detail=False, methods=["post"])
    def identify(self, request):
        serializer = ToyIdentifyImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = serializer.validated_data["image"]
        try:
            result = vision.identify_toy_from_image(
                image.read(), mime_type=image.content_type or "image/jpeg"
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        except Exception:
            return Response(
                {"detail": "Could not identify the toy from this photo. Enter details manually."},
                status=502,
            )
        return Response(result.model_dump())

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
