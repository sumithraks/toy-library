from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/memberships/", include("apps.memberships.urls")),
    path("api/", include("apps.billing.urls")),
    path("api/", include("apps.inventory.urls")),
    path("api/checkouts/", include("apps.checkouts.urls")),
    path("api/waitlist/", include("apps.waitlist.urls")),
    path("api/reservations/", include("apps.reservations.urls")),
    path("api/donations/", include("apps.donations.urls")),
    path("api/", include("apps.notifications.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
