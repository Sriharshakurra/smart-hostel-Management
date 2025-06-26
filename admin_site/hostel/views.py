from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required

from .models import Room, Register
from .forms import FloorRoomForm, ChangeRoomForm, RoomSwapForm


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
        full_name = request.POST.get('full_name')
        age = request.POST.get('age')
        contact_number = request.POST.get('contact_number')
        email = request.POST.get('email')
        room_id = request.POST.get('room')

        try:
            room = Room.objects.get(id=room_id)
            Register.objects.create(
                full_name=full_name,
                age=age,
                contact_number=contact_number,
                email=email,
                room=room,
            )
            messages.success(request, "Registration successful!")
            return redirect('register')
        except Room.DoesNotExist:
            messages.error(request, "Room not found.")

    rooms = Room.objects.all()
    return render(request, 'register_member.html', {'rooms': rooms})


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
            message = f"{m1.full_name} and {m2.full_name} have successfully swapped rooms."
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
            message = f"{member.full_name} has been moved to Room {new_room.room_number}"
    else:
        form = ChangeRoomForm()

    return render(request, 'admin/hostel/change_room.html', {
        'form': form,
        'message': message
    })
