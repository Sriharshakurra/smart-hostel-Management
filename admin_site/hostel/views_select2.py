from django_select2.views import AutoResponseView
from .models import Register, Room

class RegisterSelect2View(AutoResponseView):
    def get_queryset(self):
        return Register.objects.filter(is_active=True)

    def filter_queryset(self, term, queryset=None, **dependent_fields):
        return queryset.filter(sur_name__icontains=term).order_by('sur_name')

class RoomSelect2View(AutoResponseView):
    def get_queryset(self):
        return Room.objects.all()

    def filter_queryset(self, term, queryset=None, **dependent_fields):
        return queryset.filter(room_number__icontains=term).order_by('room_number')
