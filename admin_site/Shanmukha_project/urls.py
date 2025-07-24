from django.contrib import admin
from hostel.admin import admin_site
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from hostel import admin, views
from hostel.views import RegisterSelect2View, RoomSelect2View 
from hostel.admin import admin_site  # ✅ if admin_site is declared in hostel/admin.py








from hostel.views import (
    register_member,
    room_filter_view,
    change_room_view,
    room_swap_view,
    new_payment_view,
    balance_payment_view,
    room_availability_view,
    get_room_rent,
    vacate_member_view
)

app_name = 'hostel'
urlpatterns = [
    # ✅ Move all custom admin views BEFORE this line
    path('admin/hostel/room-availability/', room_availability_view, name='room_availability_view'),
    path('admin/change-room/', change_room_view, name='change_room_view'),
    path('admin/swap-room/', room_swap_view, name='room_swap_view'),
    
    # Other custom paths
    path('custom/vacate-member/', views.vacate_member_view, name='vacate_member_view'),
    path('get-room-rent/<int:room_id>/', views.get_room_rent, name='get_room_rent'),
    path('register/', register_member, name='register'),
    path('room-filter/', room_filter_view, name='room_filter'),
    path('select2/', include('django_select2.urls')),
    path("select2/register/", RegisterSelect2View.as_view(), name="select2_register"),
    path("select2/room/", RoomSelect2View.as_view(), name="select2_room"),
    path('custom/new-payment/', new_payment_view, name='new_payment_view_fix'),
    path('custom/balance-payment/', balance_payment_view, name='balance_payment_view'),
    path('ajax/get-members-by-room/', views.get_members_by_room, name='get_members_by_room'),
    path('ajax/get-balance-by-member/', views.get_balance_by_member, name='get_balance_by_member'),

    # ✅ Custom admin site must be last
    path('admin/', admin_site.urls),
]



if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)