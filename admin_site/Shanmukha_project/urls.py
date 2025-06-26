from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from hostel.views import register_member, room_filter_view, change_room_view
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('register/', register_member, name='register'),
    path('room-filter/', room_filter_view, name='room_filter'),
    path('admin/select2/', include('django_select2.urls')),
    path('admin/change-room/', change_room_view, name='change-room'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
