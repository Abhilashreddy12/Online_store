from django.contrib import admin
from django.utils.html import format_html
from .models import Customer, Address


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['user_full_name', 'email', 'phone', 'is_vip', 'loyalty_points', 
                   'total_orders_count', 'newsletter_subscribed', 'created_at']
    list_filter = ['is_vip', 'newsletter_subscribed', 'gender', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'phone']
    readonly_fields = ['created_at', 'updated_at', 'total_orders_count', 'total_spent_amount']
    
    list_editable = ['is_vip']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Personal Details', {
            'fields': ('phone', 'date_of_birth', 'gender', 'profile_picture')
        }),
        ('Preferences', {
            'fields': ('newsletter_subscribed', 'sms_notifications')
        }),
        ('Customer Status', {
            'fields': ('is_vip', 'loyalty_points')
        }),
        ('Statistics', {
            'fields': ('total_orders_count', 'total_spent_amount'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    user_full_name.short_description = 'Name'
    user_full_name.admin_order_field = 'user__first_name'

    def email(self, obj):
        return obj.user.email
    email.short_description = 'Email'
    email.admin_order_field = 'user__email'

    def total_orders_count(self, obj):
        count = obj.total_orders
        return format_html('<strong>{}</strong>', count)
    total_orders_count.short_description = 'Total Orders'

    def total_spent_amount(self, obj):
        amount = obj.total_spent
        return format_html('<strong>${:,.2f}</strong>', amount)
    total_spent_amount.short_description = 'Total Spent'


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'customer_name', 'address_type', 'city', 'state', 
                   'is_default', 'is_active']
    list_filter = ['address_type', 'is_default', 'is_active', 'country', 'state']
    search_fields = ['full_name', 'customer__username', 'customer__email', 
                    'address_line1', 'city', 'postal_code']
    readonly_fields = ['created_at', 'updated_at']
    
    list_editable = ['is_default', 'is_active']

    fieldsets = (
        ('Customer', {
            'fields': ('customer', 'address_type')
        }),
        ('Contact Information', {
            'fields': ('full_name', 'phone')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Settings', {
            'fields': ('is_default', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def customer_name(self, obj):
        return obj.customer.get_full_name() or obj.customer.username
    customer_name.short_description = 'Customer'
    customer_name.admin_order_field = 'customer__first_name'

