from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("ledger-entries", views.LedgerEntryViewSet, basename="ledger-entry")

urlpatterns = router.urls
