from django.db import models
from django.utils import timezone
from datetime import date, timedelta
from django.db.models import Sum
from django.utils.timezone import now


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
        return self.capacity - self.register_set.count()

    def get_current_members(self):
        return self.register_set.filter(is_active=True)

    def total_due_amount(self):
        return sum(member.get_balance() for member in self.get_current_members())


class Register(models.Model):
    first_name = models.CharField(max_length=50)
    sur_name = models.CharField(max_length=50)
    contact_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    job_or_study = models.CharField(max_length=100)  
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True)
    advance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True)
    aadhar_number = models.CharField(max_length=12)
    guardian_name = models.CharField(max_length=100)
    guardian_contact_number = models.CharField(max_length=15)

    is_active = models.BooleanField(default=True)
    payment_status = models.CharField(
        max_length=10,
        choices=[('Paid', 'Paid'), ('Unpaid', 'Unpaid')],
        default='Unpaid'
    )
    total_rent = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    joined_date = models.DateField(auto_now_add=True)

    def full_name(self):
        return f"{self.sur_name} {self.first_name}"

    def __str__(self):
        room_str = f" | Room {self.room.room_number}" if self.room else ""
        return f"{self.sur_name} {self.first_name}{room_str}"


    def get_total_paid(self):
        return Payment.objects.filter(member=self).aggregate(total=Sum('amount'))['total'] or 0

    def get_total_due(self):
        """Return the total expected rent till now based on 30-day cycles"""
        today = date.today()
        days_stayed = (today - self.joined_date).days
        cycles = (days_stayed // 30) + 1
        return self.total_rent * cycles

    def get_balance(self):
        """Accurate balance: rent * cycles - total paid"""
        from django.utils.timezone import now
        today = now().date()
        days_stayed = (today - self.joined_date).days
        rent_cycles = (days_stayed // 30) + 1  # Always count current cycle
        expected_total = self.total_rent * rent_cycles

        paid_total = Payment.objects.filter(member=self).aggregate(
            total=Sum('amount'))['total'] or 0

        return expected_total - paid_total
    
    def save(self, *args, **kwargs):
        if self.room and not self.total_rent:
            self.total_rent = self.room.rent
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Add Member"
        verbose_name_plural = "Add Members"


class Payment(models.Model):
    member = models.ForeignKey(Register, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField()
    payment_date = models.DateField(default=timezone.now)
    notes = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.member.full_name()} - ₹{self.amount} on {self.payment_date}"


    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # After saving payment, update paid_amount field
        total_paid = Payment.objects.filter(member=self.member).aggregate(total=models.Sum('amount'))['total'] or 0
        self.member.paid_amount = total_paid
        self.member.save()


# ✅ Proxy Models for Custom Admin Views (unchanged)
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


class NewPaymentProxy(Payment):
    class Meta:
        proxy = True
        verbose_name = "➕ New Payment"
        verbose_name_plural = "➕ New Payment"


class BalancePaymentProxy(Payment):
    class Meta:
        proxy = True
        verbose_name = "📌 Balance Payments"
        verbose_name_plural = "📌 Balance Payments"


class VacateMemberProxy(Register):
    class Meta:
        proxy = True
        verbose_name = "🚪 Vacate Member"
        verbose_name_plural = "🚪 Vacate Members"

class RoomAvailabilityProxy(Room):
    class Meta:
        proxy = True
        verbose_name = "📊 Room Availability"
        verbose_name_plural = "📊 Room Availability"


