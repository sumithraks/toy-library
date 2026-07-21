import django_filters
from django.db.models import Q

from .models import Toy


class ToyFilter(django_filters.FilterSet):
    make = django_filters.CharFilter(lookup_expr="icontains")
    model_name = django_filters.CharFilter(lookup_expr="icontains")
    age = django_filters.NumberFilter(method="filter_age")

    class Meta:
        model = Toy
        fields = ["status", "make", "model_name", "condition", "source", "age"]

    def filter_age(self, queryset, name, value):
        # A toy with no min_age_years set is assumed age-appropriate for everyone,
        # so it must always match rather than being excluded by NULL <= value.
        return queryset.filter(Q(min_age_years__isnull=True) | Q(min_age_years__lte=value))
