from django.contrib import admin
from django.urls import include, path


admin.site.site_header = "Lottery administration"
admin.site.site_title = "Lottery"
admin.site.index_title = "Manage outcomes"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("lottery.urls")),
]

