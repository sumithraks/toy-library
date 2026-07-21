from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("", views.DonationViewSet, basename="donation")

urlpatterns = router.urls
