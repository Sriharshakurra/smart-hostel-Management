from django.contrib import admin
from django.urls import path, reverse, reverse_lazy
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin import AdminSite
from django.contrib.auth.models import Group, User
from django.contrib.admin.sites import NotRegistered
from django.db.models import Sum
from django.utils.timezone import now
from .models import RoomAvailabilityProxy
from hostel.views import room_availability_view
from django.contrib.admin.models import LogEntry

from .models import (
    Room, Register, ChangeRoomProxy, SwapRoomProxy,
    Payment, NewPaymentProxy, BalancePaymentProxy, VacateMemberProxy
)
from .forms import (
    FloorRoomForm, ChangeRoomForm, RoomSwapForm, VacateMemberForm, RegisterForm
)

# Unregister default auth models
for model in [Group, User]:
    try:
        admin.site.unregister(model)
    except NotRegistered:
        pass

# Calculate balance for a member
def calculate_member_balance(member):
    total_days = (now().date() - member.joined_date).days
    cycles = total_days // 30
    if total_days % 30 != 0:
        cycles += 1
    total_due = member.total_rent * cycles
    total_paid = Payment.objects.filter(member=member).aggregate(total=Sum('amount'))['total'] or 0
    return total_due - total_paid


class RoomAdmin(admin.ModelAdmin):
    change_list_template = "admin/hostel/room_filter.html"
    list_display = ('room_number', 'floor', 'capacity', 'rent', 'has_attached_washroom', 'admin_actions')
    list_filter = ['floor']
    readonly_fields = ('capacity', 'rent', 'has_attached_washroom')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('room_filter/', self.admin_site.admin_view(self.room_filter_view), name='room_filter_view'),
            path('change-room/', self.admin_site.admin_view(self.change_room_view), name='change_room_view'),
            path('swap-room/', self.admin_site.admin_view(self.room_swap_view), name='room_swap_view'),
            path('room-availability/', self.admin_site.admin_view(self.room_availability_view), name='room_availability_view'),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        return self.room_filter_view(request)

    def room_filter_view(self, request):
        form = FloorRoomForm(request.GET or None)
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
            form = ChangeRoomForm(request.POST)
            if form.is_valid():
                member = form.cleaned_data['member']
                new_room = form.cleaned_data['new_room']
                member.room = new_room
                member.save()
                message = f"{member.full_name()} has been moved to Room {new_room.room_number}"
        else:
            form = ChangeRoomForm()

        return render(request, 'admin/hostel/change_room.html', {
            'form': form,
            'message': message
        })

    def room_swap_view(self, request):
        message = ''
        if request.method == 'POST':
            form = RoomSwapForm(request.POST)
            if form.is_valid():
                m1 = form.cleaned_data['member1']
                m2 = form.cleaned_data['member2']
                m1.room, m2.room = m2.room, m1.room
                m1.save()
                m2.save()
                message = f"{m1.full_name()} and {m2.full_name()} have successfully swapped rooms."
        else:
            form = RoomSwapForm()

        return render(request, 'admin/hostel/room_swap.html', {
            'form': form,
            'message': message
        })

    def room_availability_view(self, request):
        rooms = Room.objects.all().order_by('floor', 'room_number')
        room_data = []

        for room in rooms:
            occupied = Register.objects.filter(room=room, is_active=True).count()
            vacancy = room.capacity - occupied
            room_data.append({
                'floor': room.floor,
                'room_number': room.room_number,
                'capacity': room.capacity,
                'occupied': occupied,
                'vacancy': vacancy,
                'has_washroom': "Yes" if room.has_attached_washroom else "No"
            })

        return render(request, 'admin/hostel/room_availability.html', {
            'room_data': room_data,
            'title': 'Room Availability Overview'
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


class RegisterAdmin(admin.ModelAdmin):
    form = RegisterForm
    change_form_template = 'admin/hostel/change_form.html'

    class Media:
        js = ('admin/js/update_rent.js',)

    list_display = ['first_name', 'sur_name', 'guardian_name', 'guardian_contact_number',
                    'contact_number', 'payment_status', 'room', 'joined_date']
    list_filter = ['payment_status', 'is_active', 'room__floor', 'joined_date']
    search_fields = ['first_name', 'sur_name', 'guardian_name', 'aadhar_number', 'contact_number', 'job_or_study']
    readonly_fields = ['joined_date', 'paid_amount']
    list_select_related = ('room',)
    actions = ['change_room_action']

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


class ChangeRoomLinkAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        return redirect('admin:change_room_view')


class SwapRoomLinkAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        return redirect('admin:room_swap_view')


class VacateMemberAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def changelist_view(self, request, extra_context=None):
        return redirect(reverse_lazy('vacate_member_view'))


@admin.register(NewPaymentProxy)
class NewPaymentAdmin(admin.ModelAdmin):
    list_display = ['member', 'get_room', 'amount', 'payment_date', 'get_balance_display', 'notes']

    def get_room(self, obj):
        return obj.member.room
    get_room.short_description = 'Room'

    def get_balance_display(self, obj):
        balance = calculate_member_balance(obj.member)
        if balance > 0:
            return mark_safe(f"<span style='color:red;'>Due ₹{balance:.2f}</span>")
        elif balance < 0:
            return mark_safe(f"<span style='color:green;'>Advance ₹{abs(balance):.2f}</span>")
        else:
            return mark_safe("<span style='color:gray;'>Fully Paid</span>")


@admin.register(BalancePaymentProxy)
class BalancePaymentAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        return redirect(reverse_lazy('balance_payment_view'))


class PaymentAdmin(admin.ModelAdmin):
    list_display = ('member', 'member_room', 'formatted_amount', 'payment_date', 'balance_remaining', 'notes')
    list_filter = ['member__room__room_number', 'member__room__floor']
    search_fields = ['member__first_name', 'member__sur_name', 'notes']

    def formatted_amount(self, obj):
        return mark_safe(f"₹{float(obj.amount):,.0f}")
    formatted_amount.short_description = "Amount (₹)"

    def member_room(self, obj):
        return obj.member.room.room_number if obj.member and obj.member.room else "—"
    member_room.short_description = "Room"

    def balance_remaining(self, obj):
        if obj.member:
            balance = calculate_member_balance(obj.member)
            if balance < 0:
                return mark_safe(f"<span style='color:green;'>Advance ₹{abs(balance):.2f}</span>")
            elif balance == 0:
                return mark_safe("<span style='color:gray;'>₹0</span>")
            else:
                return mark_safe(f"<span style='color:red;'>Due ₹{balance:.2f}</span>")
        return "-"


class RoomAvailabilityAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def changelist_view(self, request, extra_context=None):
        return redirect(reverse('room_availability_view'))


# ✅ FINAL: Custom AdminSite with template rendering
class CustomAdminSite(AdminSite):
    site_header = "Venu Hostel Admin"
    site_title = "Venu Hostel Admin Portal"
    index_title = "Welcome to Venu Hostel Admin"

    def index(self, request, extra_context=None):
        total_rooms = Room.objects.count()
        total_members = Register.objects.count()
        active_members = Register.objects.filter(is_active=True).count()
        vacant_rooms = total_rooms - active_members

        log_entries = LogEntry.objects.select_related('content_type', 'user').order_by('-action_time')

        context = {
        'title': self.index_title,
        'site_title': self.site_title,
        'site_header': self.site_header,
        'total_rooms': total_rooms,
        'total_members': total_members,
        'active_members': active_members,
        'vacant_rooms': vacant_rooms,
        'app_list': self.get_app_list(request),
        'log_entries': log_entries,  # must be a queryset
        }
        return render(request, 'admin/hostel/index.html', context)



# Register models with custom admin site
admin_site = CustomAdminSite(name='admin')
admin_site.register(Room, RoomAdmin)
admin_site.register(Register, RegisterAdmin)
admin_site.register(ChangeRoomProxy, ChangeRoomLinkAdmin)
admin_site.register(SwapRoomProxy, SwapRoomLinkAdmin)
admin_site.register(NewPaymentProxy, NewPaymentAdmin)
admin_site.register(BalancePaymentProxy, BalancePaymentAdmin)
admin_site.register(VacateMemberProxy, VacateMemberAdmin)
admin_site.register(Payment, PaymentAdmin)
admin_site.register(RoomAvailabilityProxy, RoomAvailabilityAdmin)
