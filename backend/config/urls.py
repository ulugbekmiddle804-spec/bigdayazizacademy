from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.core.views import health

admin.site.site_header = "Online Test — Django admin"
admin.site.site_title = "Online Test"

urlpatterns = [
    path("api/health/", health, name="health"),
    path("api/", include("apps.exams.urls")),
    path("api/admin/", include("apps.adminapi.urls")),
    path(settings.DJANGO_ADMIN_URL, admin.site.urls),
]
