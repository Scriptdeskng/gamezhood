from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from content.views import error404, error500


from django.conf.urls import handler404, handler500


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("u/", include("ums.urls", namespace="users")),
    path("", include("content.urls", namespace="core")),
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


handler404 = error404
handler500 = error500
