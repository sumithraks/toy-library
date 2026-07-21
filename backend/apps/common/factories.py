from datetime import timedelta
from decimal import Decimal

import factory
from django.utils import timezone

from apps.accounts.models import User
from apps.inventory.models import Toy
from apps.memberships.models import Membership, MembershipTier


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = "Test"
    last_name = "User"
    is_email_verified = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or "testpass123")
        if create:
            self.save()


class MembershipTierFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MembershipTier
        django_get_or_create = ("code",)

    code = MembershipTier.Code.SILVER
    name = "Silver"
    joining_fee = Decimal("25.00")
    deposit_amount = Decimal("50.00")
    renewal_fee = Decimal("12.50")
    max_concurrent_checkouts = 1
    loan_period_days = 14
    complimentary_extension_days = 2


class MembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Membership

    user = factory.SubFactory(UserFactory)
    tier = factory.SubFactory(MembershipTierFactory)
    status = Membership.Status.ACTIVE
    joined_at = factory.LazyFunction(timezone.now)
    renewed_through = factory.LazyFunction(lambda: timezone.now().date() + timedelta(days=365))


class ToyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Toy

    model_name = factory.Sequence(lambda n: f"Toy {n}")
    make = "TestCo"
    status = Toy.Status.AVAILABLE
