from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("", views.CheckoutViewSet, basename="checkout")

urlpatterns = router.urls
