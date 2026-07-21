from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("toys", views.ToyViewSet, basename="toy")

urlpatterns = router.urls
