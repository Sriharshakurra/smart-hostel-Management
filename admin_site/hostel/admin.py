from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.html import format_html

from .models import Room, Register, ChangeRoomProxy, SwapRoomProxy
from . import forms

from django.contrib.auth.models import Group, User
from django.contrib.admin.sites import NotRegistered

# Unregister default auth models safely
for model in [Group, User]:
    try:
        admin.site.unregister(model)
    except NotRegistered:
        pass

# Admin branding
admin.site.site_header = "Venu Administration"
admin.site.site_title = "Venu Admin Portal"
admin.site.index_title = "Welcome to Venu Hostel Admin"


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    change_list_template = "admin/hostel/room_filter.html"
    list_display = ('room_number', 'floor', 'capacity', 'rent', 'has_attached_washroom', 'admin_actions')
    list_filter = ('floor',)
    readonly_fields = ('capacity', 'rent', 'has_attached_washroom')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('room_filter/', self.admin_site.admin_view(self.room_filter_view), name='room_filter_view'),
            path('change-room/', self.admin_site.admin_view(self.change_room_view), name='change_room_view'),
            path('swap-room/', self.admin_site.admin_view(self.room_swap_view), name='room_swap_view'),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        return self.room_filter_view(request)

    def room_filter_view(self, request):
        form = forms.FloorRoomForm(request.GET or None)
        selected_room = None
        members = []

        if form.is_valid() and form.cleaned_data.get('room'):
            selected_room = Room.objects.get(id=form.cleaned_data['room'])
            members = Register.objects.filter(room=selected_room)

        return render(request, "admin/hostel/room_filter.html", {
            'form': form,
            'room_obj': selected_room,
            'members': members,
        })

    def change_room_view(self, request):
        message = ''
        if request.method == 'POST':
            form = forms.ChangeRoomForm(request.POST)
            if form.is_valid():
                member = form.cleaned_data['member']
                new_room = form.cleaned_data['new_room']
                member.room = new_room
                member.save()
                message = f"{member.full_name} has been moved to Room {new_room.room_number}"
        else:
            form = forms.ChangeRoomForm()

        return render(request, 'admin/hostel/change_room.html', {
            'form': form,
            'message': message
        })

    def room_swap_view(self, request):
        message = ''
        if request.method == 'POST':
            form = forms.RoomSwapForm(request.POST)
            if form.is_valid():
                m1 = form.cleaned_data['member1']
                m2 = form.cleaned_data['member2']
                m1.room, m2.room = m2.room, m1.room
                m1.save()
                m2.save()
                message = f"{m1.full_name} and {m2.full_name} have successfully swapped rooms."
        else:
            form = forms.RoomSwapForm()

        return render(request, 'admin/hostel/room_swap.html', {
            'form': form,
            'message': message
        })

    def admin_actions(self, obj):
        change_url = reverse('admin:change_room_view')
        swap_url = reverse('admin:room_swap_view')
        return format_html(
            '<a class="button" href="{}">Change Room</a>&nbsp;&nbsp;'
            '<a class="button" href="{}">Swap Room</a>',
            change_url,
            swap_url
        )
    admin_actions.short_description = 'Actions'


@admin.register(Register)
class RegisterAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 'room', 'contact_number', 'joined_date', 'is_active',
        'payment_status', 'paid_amount', 'total_rent_display', 'due_amount_display'
    )
    list_filter = ('room__floor', 'is_active', 'payment_status')
    search_fields = ('full_name', 'contact_number', 'email')
    list_select_related = ('room',)
    actions = ['change_room_action']

    def total_rent_display(self, obj):
        return obj.total_rent
    total_rent_display.short_description = "Total Rent (₹)"

    def due_amount_display(self, obj):
        return obj.due_amount
    due_amount_display.short_description = "Due Amount (₹)"

    def change_room_action(self, request, queryset):
        if 'apply' in request.POST:
            new_room_id = request.POST.get('room')
            try:
                new_room = Room.objects.get(id=new_room_id)
            except Room.DoesNotExist:
                self.message_user(request, "Invalid room selected.", level=messages.ERROR)
                return

            updated = 0
            for member in queryset:
                if new_room.available_slots > 0:
                    member.room = new_room
                    member.save()
                    updated += 1

            self.message_user(request, f"{updated} members moved to {new_room.room_number}")
            return redirect(request.get_full_path())

        rooms = Room.objects.all()
        context = {
            'members': queryset,
            'rooms': rooms,
            'title': "Change Room for Selected Members",
        }
        return render(request, 'admin/hostel/change_room.html', context)

    change_room_action.short_description = "Change Room for selected members"


# Proxy Admin links
@admin.register(ChangeRoomProxy)
class ChangeRoomLinkAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        return redirect('admin:change_room_view')


@admin.register(SwapRoomProxy)
class SwapRoomLinkAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        return redirect('admin:room_swap_view')
