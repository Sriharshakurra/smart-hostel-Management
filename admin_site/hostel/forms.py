from django import forms
from .models import Register, Room, Payment
from django_select2.forms import Select2Widget, HeavySelect2Widget


class FloorRoomForm(forms.Form):
    floor = forms.ChoiceField(label="Select Floor", choices=[(i, f"Floor {i}") for i in range(1, 7)])
    room = forms.ChoiceField(label="Select Room", choices=[], required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'floor' in self.data:
            try:
                floor = int(self.data.get('floor'))
                self.fields['room'].choices = [
                    (r.id, r.room_number) for r in Room.objects.filter(floor=floor).order_by('room_number')
                ]
            except (ValueError, TypeError):
                self.fields['room'].choices = []


class RoomSwapForm(forms.Form):
    member1 = forms.ModelChoiceField(
        queryset=Register.objects.none(),
        widget=HeavySelect2Widget(data_view='select2_register'),
        label="Member 1"
    )
    member2 = forms.ModelChoiceField(
        queryset=Register.objects.none(),
        widget=HeavySelect2Widget(data_view='select2_register'),
        label="Member 2"
    )

    def clean(self):
        cleaned_data = super().clean()
        m1 = cleaned_data.get('member1')
        m2 = cleaned_data.get('member2')
        if m1 and m2 and m1.room == m2.room:
            raise forms.ValidationError("Both members are already in the same room.")


class MemberWidget(HeavySelect2Widget):
    data_view = 'select2_register'
    attrs = {
        'data-placeholder': 'Type surname…',
        'data-minimum-input-length': 1,
        'style': 'width: 350px;',
        'data-ajax--cache': 'true'
    }


class RoomWidget(HeavySelect2Widget):
    data_view = 'select2_room'
    attrs = {
        'data-placeholder': 'Enter 3-digit room number',
        'data-minimum-input-length': 3,
        'style': 'width: 300px;',
        'data-ajax--cache': 'true'
    }


class ChangeRoomForm(forms.Form):
    member = forms.ModelChoiceField(
        queryset=Register.objects.none(),
        widget=MemberWidget,
        label="Select Member"
    )
    new_room = forms.ModelChoiceField(
        queryset=Room.objects.none(),
        widget=RoomWidget,
        label="Select New Room"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['member'].queryset = Register.objects.filter(is_active=True)
        self.fields['new_room'].queryset = Room.objects.all()


class NewPaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['member', 'amount', 'payment_date', 'notes']
        widgets = {
            'member': Select2Widget,
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.TextInput(attrs={'placeholder': 'Optional'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['member'].queryset = Register.objects.filter(is_active=True)


class BalancePaymentForm(forms.Form):
    member = forms.ModelChoiceField(
        queryset=Register.objects.none(),
        label="Select Member",
        widget=Select2Widget
    )
    amount = forms.IntegerField(label="Enter Payment Amount")

    def __init__(self, *args, **kwargs):
        floor = kwargs.pop('floor', None)
        super().__init__(*args, **kwargs)

        if floor:
            self.fields['member'].queryset = Register.objects.filter(
                room__floor=floor,
                is_active=True
            )
        else:
            self.fields['member'].queryset = Register.objects.filter(is_active=True)


class RegisterForm(forms.ModelForm):
    class Meta:
        model = Register
        fields = ('__all__')
        js = ('js/room_rent.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'total_rent' in self.fields:
            self.fields['total_rent'].widget.attrs.update({
                'readonly': True,
                'id': 'id_total_rent'
            })

        self.fields['room'].widget = forms.Select(
            choices=[('', '--------')] + [(room.id, str(room)) for room in Room.objects.all()]
        )


class VacateMemberForm(forms.Form):
    room = forms.ModelChoiceField(queryset=Room.objects.all(), label="Room Number")
    member = forms.ModelChoiceField(queryset=Register.objects.none(), label="Member", required=False)
    balance = forms.DecimalField(label="Balance Amount", required=False, disabled=True)

    final_payment_option = forms.ChoiceField(
        label="Final Payment Option",
        choices=[
            ("paid", "Paid"),
            ("waived", "Waived"),
            ("partial", "Partially Paid")
        ],
        widget=forms.RadioSelect,
        required=False
    )

    note = forms.CharField(widget=forms.Textarea, required=False, label="Note")

    def __init__(self, *args, **kwargs):
        room_id = kwargs.pop('room_id', None)
        super().__init__(*args, **kwargs)
        if room_id:
            self.fields['member'].queryset = Register.objects.filter(room_id=room_id, is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        payment_status = cleaned_data.get('final_payment_option')
        note = cleaned_data.get('note')

        if payment_status in ['waived', 'partial'] and not note:
            self.add_error('note', 'Note is required for waived or partially paid balances.')
