from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("", views.WaitlistViewSet, basename="waitlist")

urlpatterns = router.urls
