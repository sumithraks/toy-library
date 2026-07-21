from rest_framework.routers import DefaultRouter

from django.urls import path

from . import views

router = DefaultRouter()
router.register("", views.MembershipViewSet, basename="membership")

urlpatterns = [
    path("tiers/", views.MembershipTierListView.as_view(), name="membership-tiers"),
    path("me/", views.MyMembershipView.as_view(), name="my-membership"),
    path("signup/", views.MembershipSignupView.as_view(), name="membership-signup"),
] + router.urls
