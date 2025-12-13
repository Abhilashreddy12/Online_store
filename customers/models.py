from django.db import models
from django.contrib.auth.models import User


class Customer(models.Model):
    """Extended customer profile"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    
    profile_picture = models.ImageField(upload_to='customers/', blank=True, null=True)
    
    # Newsletter and marketing
    newsletter_subscribed = models.BooleanField(default=False)
    sms_notifications = models.BooleanField(default=False)
    
    # Customer segmentation
    is_vip = models.BooleanField(default=False)
    loyalty_points = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"

    @property
    def total_orders(self):
        return self.user.orders.count()

    @property
    def total_spent(self):
        from orders.models import Order
        return self.user.orders.filter(
            status='DELIVERED'
        ).aggregate(models.Sum('total_amount'))['total_amount__sum'] or 0


class Address(models.Model):
    """Customer addresses"""
    ADDRESS_TYPES = [
        ('BILLING', 'Billing'),
        ('SHIPPING', 'Shipping'),
    ]

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES)
    
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    
    address_line1 = models.CharField(max_length=300)
    address_line2 = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='USA')
    
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Addresses'
        ordering = ['-is_default', '-created_at']

    def save(self, *args, **kwargs):
        # Ensure only one default address per type per customer
        if self.is_default:
            Address.objects.filter(
                customer=self.customer,
                address_type=self.address_type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} - {self.address_line1}, {self.city}"

