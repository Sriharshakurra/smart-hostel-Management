from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.utils.timezone import now
from django.db.models import Sum

from .models import Room, Register, Payment
from .forms import (
    FloorRoomForm, ChangeRoomForm, RoomSwapForm,
    NewPaymentForm, BalancePaymentForm, VacateMemberForm
)

@staff_member_required
def room_filter_view(request):
    floor_form = FloorRoomForm(request.GET or None)
    room_data = None
    members = []

    if request.GET.get('floor') and request.GET.get('room'):
        try:
            room_data = Room.objects.get(id=request.GET['room'])
            members = Register.objects.filter(room=room_data)
        except Room.DoesNotExist:
            messages.warning(request, "Selected room not found.")

    context = {
        'floor_form': floor_form,
        'room_form': floor_form if request.GET.get('floor') else None,
        'room_data': room_data,
        'members': members,
    }
    return render(request, 'admin/hostel/room_filter.html', context)


@staff_member_required
def register_member(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        sur_name = request.POST.get('sur_name')
        contact_number = request.POST.get('contact_number')
        email = request.POST.get('email')
        job_or_study = request.POST.get('job_or_study')
        aadhar_number = request.POST.get('aadhar_number')
        guardian_name = request.POST.get('guardian_name')
        guardian_contact_number = request.POST.get('guardian_contact_number')
        room_id = request.POST.get('room')

        try:
            room = Room.objects.get(id=room_id)
            Register.objects.create(
                first_name=first_name,
                sur_name=sur_name,
                contact_number=contact_number,
                email=email,
                job_or_study=job_or_study,
                aadhar_number=aadhar_number,
                guardian_name=guardian_name,
                guardian_contact_number=guardian_contact_number,
                room=room,
            )
            messages.success(request, "Registration successful!")
            return redirect('register')
        except Room.DoesNotExist:
            messages.error(request, "Room not found.")

    rooms = Room.objects.all()
    return render(request, 'admin/hostel/register_member.html', {'rooms': rooms})


@staff_member_required
def room_swap_view(request):
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


@staff_member_required
def change_room_view(request):
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


@staff_member_required
def get_room_rent(request, room_id):
    try:
        room = Room.objects.get(room_number=room_id)
        return JsonResponse({'rent': room.rent})
    except Room.DoesNotExist:
        return JsonResponse({'error': 'Room not found'}, status=404)


@staff_member_required
def new_payment_view(request):
    if request.method == 'POST':
        form = NewPaymentForm(request.POST)
        if form.is_valid():
            member = form.cleaned_data['member']
            amount = form.cleaned_data['amount']
            Payment.objects.create(member=member, amount=amount)
            messages.success(request, "Payment recorded successfully!")
            return redirect('admin:hostel_newpaymentproxy_changelist')
    else:
        form = NewPaymentForm()

    return render(request, 'admin/hostel/new_payment.html', {'form': form})


def calculate_member_balance(member):
    total_days = (now().date() - member.joined_date).days
    cycles = total_days // 30 + 1
    total_due = member.total_rent * cycles

    total_paid = Payment.objects.filter(member=member).aggregate(total=Sum('amount'))['total'] or 0

    return total_due - total_paid


@staff_member_required
def balance_payment_view(request):
    floor = request.GET.get('floor')
    rooms = Room.objects.filter(floor=floor) if floor else Room.objects.all()

    room_data = []
    total_due_amount = 0

    for room in rooms:
        members = room.register_set.filter(is_active=True)
        member_data = []
        for m in members:
            balance = calculate_member_balance(m)
            if balance > 0:
                member_data.append({
                    'name': m.full_name(),
                    'contact': m.contact_number,
                    'paid': m.paid_amount,
                    'total': m.total_rent,
                    'balance': balance,
                })
                total_due_amount += balance
        if member_data:
            room_data.append({
                'room_number': room.room_number,
                'members': member_data
            })

    floors = Room.objects.values_list('floor', flat=True).distinct()
    return render(request, 'admin/hostel/balance_payment.html', {
        'room_data': room_data,
        'floors': sorted(set(floors)),
        'selected_floor': floor,
        'total_due_amount': total_due_amount,
    })


@staff_member_required
def vacate_member_view(request):
    room_id = request.GET.get('room') or request.POST.get('room')
    member_id = request.GET.get('member') or request.POST.get('member')

    selected_member = None
    balance = None

    room = Room.objects.filter(id=room_id).first() if room_id else None
    form = VacateMemberForm(request.POST or None, room_id=room.id if room else None)

    if request.method == 'POST':
        if form.is_valid():
            member = form.cleaned_data.get('member')
            note = form.cleaned_data.get('note', '').strip()
            payment_option = request.POST.get('payment_option')

            if not member:
                messages.error(request, "Please select a member before submitting.")
            else:
                balance = member.get_balance()

                if not payment_option:
                    messages.error(request, "Please select a payment option.")
                elif (payment_option in ['Waived', 'Partially Paid']) and not note:
                    messages.error(request, "Note is required for waiver or partial payment.")
                elif payment_option == 'Paid' and balance > 0:
                    messages.error(request, f"{member.full_name()} still has ₹{balance} pending. Mark it as Waived or Partial if needed.")
                else:
                    member.is_active = False
                    member.room = None
                    member.save()

                    if payment_option in ['Waived', 'Partially Paid'] or note:
                        Payment.objects.create(
                            member=member,
                            amount=0,
                            notes=f"[{payment_option}] {note or 'No note'}"
                        )

                    messages.success(request, f"{member.full_name()} has been successfully vacated.")
                    return redirect(request.path + f"?room={room_id}")

    if room_id:
        form.fields['member'].queryset = Register.objects.filter(room__id=room_id, is_active=True)

    if member_id:
        try:
            selected_member = Register.objects.get(id=member_id)
            balance = selected_member.get_balance()
            form.fields['balance'].initial = balance
        except Register.DoesNotExist:
            selected_member = None

    return render(request, 'admin/hostel/vacate_member.html', {
        'form': form,
        'selected_member': selected_member,
        'balance': balance,
    })


@staff_member_required
def get_members_by_room(request):
    room_id = request.GET.get('room_id')
    members = Register.objects.filter(room_id=room_id, is_active=True)

    member_options = [{'id': member.id, 'name': member.full_name()} for member in members]

    return JsonResponse({'members': member_options})


@staff_member_required
def get_balance_by_member(request):
    member_id = request.GET.get('member_id')
    try:
        member = Register.objects.get(id=member_id)
        balance = member.get_balance()
        return JsonResponse({'balance': balance})
    except Register.DoesNotExist:
        return JsonResponse({'error': 'Member not found'}, status=404)


@staff_member_required
def get_member_balance(request):
    member_id = request.GET.get('member_id')
    try:
        member = Register.objects.get(id=member_id)
        today = now().date()
        days_stayed = (today - member.joined_date).days
        rent_cycles = (days_stayed // 30) + 1
        expected = member.total_rent * rent_cycles
        paid = Payment.objects.filter(member=member).aggregate(total=Sum('amount'))['total'] or 0
        balance = expected - paid
        return JsonResponse({'balance': balance})
    except Register.DoesNotExist:
        return JsonResponse({'balance': 0})


from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from .models import Room

from django.shortcuts import render
from hostel.models import Room, Register

def room_availability_view(request):
    print("📢 room_availability_view called")
    all_floors = Room.objects.values_list('floor', flat=True).distinct().order_by('floor')
    print("✅ all_floors fetched:", list(all_floors))

    selected_floor = request.GET.get('floor')
    view_triggered = 'view' in request.GET
    room_data = []

    if view_triggered and selected_floor:
        try:
            selected_floor = int(selected_floor)
            rooms = Room.objects.filter(floor=selected_floor).order_by('room_number')
            for room in rooms:
                occupied = Register.objects.filter(room=room, is_active=True).count()
                room_data.append({
                    'floor': room.floor,
                    'room_number': room.room_number,
                    'capacity': room.capacity,
                    'occupied': occupied,
                    'vacancy': room.capacity - occupied,
                    'has_washroom': "Yes" if room.has_attached_washroom else "No"
                })
        except ValueError:
            selected_floor = None

    context = {
        'all_floors': all_floors,
        'selected_floor': selected_floor,
        'room_data': room_data,
        'view_triggered': view_triggered,
    }
    return render(request, 'admin/hostel/room_availability.html', context)









# ✅ Select2 Views
from django_select2.views import AutoResponseView

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
