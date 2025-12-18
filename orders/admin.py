from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Order, OrderItem, Coupon, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['line_total', 'product_name', 'product_sku', 'variant_details']
    fields = ['product', 'variant', 'quantity', 'unit_price', 'line_total']


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ['status', 'created_by', 'created_at', 'notes']
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer_name', 'status_badge', 'payment_status_badge', 
                   'total_amount_display', 'items_count', 'created_at']
    list_filter = ['status', 'payment_status', 'created_at', 'payment_method']
    search_fields = ['order_number', 'customer__username', 'customer__email', 'tracking_number']
    readonly_fields = ['order_number', 'created_at', 'updated_at', 'paid_at', 
                      'shipped_at', 'delivered_at', 'total_amount_display']
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    actions = ['mark_as_processing', 'mark_as_shipped', 'mark_as_delivered']
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'customer', 'status', 'payment_status')
        }),
        ('Addresses', {
            'fields': ('shipping_address', 'billing_address')
        }),
        ('Pricing', {
            'fields': ('subtotal', 'tax_amount', 'shipping_cost', 'discount_amount', 
                      'total_amount', 'total_amount_display')
        }),
        ('Payment', {
            'fields': ('payment_method', 'transaction_id', 'paid_at')
        }),
        ('Shipping', {
            'fields': ('tracking_number', 'carrier', 'shipped_at', 'delivered_at')
        }),
        ('Notes', {
            'fields': ('customer_notes', 'admin_notes'),
            'classes': ('collapse',)
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

    def status_badge(self, obj):
        colors = {
            'PENDING': 'orange',
            'PROCESSING': 'blue',
            'SHIPPED': 'purple',
            'DELIVERED': 'green',
            'CANCELLED': 'red',
            'REFUNDED': 'gray',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'gray'), obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def payment_status_badge(self, obj):
        colors = {
            'PENDING': 'orange',
            'PAID': 'green',
            'FAILED': 'red',
            'REFUNDED': 'gray',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            colors.get(obj.payment_status, 'gray'), obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Payment'

    def total_amount_display(self, obj):
        return format_html('<strong style="font-size: 14px;">₹{}</strong>', f'{obj.total_amount:,.2f}')
    total_amount_display.short_description = 'Total'

    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'Items'

    def mark_as_processing(self, request, queryset):
        for order in queryset:
            order.status = 'PROCESSING'
            order.save()
            OrderStatusHistory.objects.create(
                order=order,
                status='PROCESSING',
                notes='Status changed via admin action',
                created_by=request.user
            )
        self.message_user(request, f'{queryset.count()} orders marked as processing.')
    mark_as_processing.short_description = 'Mark as Processing'

    def mark_as_shipped(self, request, queryset):
        for order in queryset:
            order.status = 'SHIPPED'
            order.shipped_at = timezone.now()
            order.save()
            OrderStatusHistory.objects.create(
                order=order,
                status='SHIPPED',
                notes='Status changed via admin action',
                created_by=request.user
            )
        self.message_user(request, f'{queryset.count()} orders marked as shipped.')
    mark_as_shipped.short_description = 'Mark as Shipped'

    def mark_as_delivered(self, request, queryset):
        for order in queryset:
            order.status = 'DELIVERED'
            order.delivered_at = timezone.now()
            order.save()
            OrderStatusHistory.objects.create(
                order=order,
                status='DELIVERED',
                notes='Status changed via admin action',
                created_by=request.user
            )
        self.message_user(request, f'{queryset.count()} orders marked as delivered.')
    mark_as_delivered.short_description = 'Mark as Delivered'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product_name', 'variant_details', 'quantity', 'unit_price', 'line_total']
    list_filter = ['order__status', 'created_at']
    search_fields = ['order__order_number', 'product__name', 'product_sku']
    readonly_fields = ['line_total', 'product_name', 'product_sku', 'variant_details']


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_display', 'usage_display', 'validity_status', 
                   'is_active', 'valid_from', 'valid_to']
    list_filter = ['is_active', 'discount_type', 'valid_from', 'valid_to']
    search_fields = ['code', 'description']
    readonly_fields = ['times_used', 'created_at']
    
    list_editable = ['is_active']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'description', 'is_active')
        }),
        ('Discount', {
            'fields': ('discount_type', 'discount_value', 'maximum_discount')
        }),
        ('Conditions', {
            'fields': ('minimum_order_amount',)
        }),
        ('Usage Limits', {
            'fields': ('usage_limit', 'usage_per_customer', 'times_used')
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def discount_display(self, obj):
        if obj.discount_type == 'PERCENTAGE':
            return f'{obj.discount_value}%'
        return f'₹{obj.discount_value}'
    discount_display.short_description = 'Discount'

    def usage_display(self, obj):
        if obj.usage_limit:
            return f'{obj.times_used} / {obj.usage_limit}'
        return f'{obj.times_used} / Unlimited'
    usage_display.short_description = 'Usage'

    def validity_status(self, obj):
        is_valid, message = obj.is_valid()
        color = 'green' if is_valid else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, message
        )
    validity_status.short_description = 'Status'


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['order', 'status', 'created_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order__order_number', 'notes']
    readonly_fields = ['order', 'status', 'notes', 'created_by', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

