from django.db import models

class Room(models.Model):
    room_number = models.CharField(max_length=10, unique=True)
    floor = models.PositiveIntegerField()
    capacity = models.PositiveIntegerField()
    rent = models.PositiveIntegerField()
    has_attached_washroom = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.room_number}"

    @property
    def available_slots(self):
        return self.capacity - self.register_set.count()  # links to Register model


class Register(models.Model):
    full_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    joined_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    payment_status = models.CharField(
        max_length=50,
        choices=[('Paid', 'Paid'), ('Unpaid', 'Unpaid')],
        default='Unpaid'
    )
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True)
    paid_amount = models.PositiveIntegerField(default=0)  # ✅ New field

    def __str__(self):
        return self.full_name

    @property
    def total_rent(self):
        return self.room.rent if self.room else 0

    @property
    def due_amount(self):
        return max(self.total_rent - self.paid_amount, 0)

    class Meta:
        verbose_name = "Add Member"
        verbose_name_plural = "Add Members"


# ✅ Proxy models for custom admin views
class ChangeRoomProxy(Room):
    class Meta:
        proxy = True
        verbose_name = "🔁 Change Room"
        verbose_name_plural = "🔁 Change Room"

class SwapRoomProxy(Room):
    class Meta:
        proxy = True
        verbose_name = "🔄 Swap Room"
        verbose_name_plural = "🔄 Swap Room"
