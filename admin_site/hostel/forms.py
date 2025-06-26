from django import forms
from .models import Register, Room
from django_select2.forms import Select2Widget

class FloorRoomForm(forms.Form):
    floor = forms.ChoiceField(label="Select Floor", choices=[(i, f"Floor {i}") for i in range(1, 7)])
    room = forms.ChoiceField(label="Select Room", choices=[], required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'floor' in self.data:
            try:
                floor = int(self.data.get('floor'))
                from .models import Room  # imported here to avoid circular import
                self.fields['room'].choices = [
                    (r.id, r.room_number) for r in Room.objects.filter(floor=floor).order_by('room_number')
                ]
            except (ValueError, TypeError):
                self.fields['room'].choices = []


class RoomSwapForm(forms.Form):
    member1 = forms.ModelChoiceField(
        queryset=Register.objects.all(),
        widget=Select2Widget,
        label="Member 1"
    )
    member2 = forms.ModelChoiceField(
        queryset=Register.objects.all(),
        widget=Select2Widget,
        label="Member 2"
    )

    def clean(self):
        cleaned_data = super().clean()
        m1 = cleaned_data.get('member1')
        m2 = cleaned_data.get('member2')
        if m1 and m2 and m1.room == m2.room:
            raise forms.ValidationError("Both members are already in the same room.")

        
from django_select2.forms import Select2AdminMixin

class ChangeRoomForm(forms.Form):
    member = forms.ModelChoiceField(
        queryset=Register.objects.all(),
        widget=Select2Widget,
        label="Select Member"
    )
    new_room = forms.ModelChoiceField(
        queryset=Room.objects.all(),
        label="Select New Room"
    )
