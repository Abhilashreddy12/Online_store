from django.contrib import admin
from django.utils.html import format_html
from .models import Cart, CartItem, Wishlist, WishlistItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['unit_price', 'line_total']
    fields = ['product', 'variant', 'quantity', 'unit_price', 'line_total']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['customer', 'total_items_count', 'subtotal_display', 'updated_at']
    search_fields = ['customer__username', 'customer__email']
    readonly_fields = ['created_at', 'updated_at', 'total_items_count', 'subtotal_display']
    inlines = [CartItemInline]

    def total_items_count(self, obj):
        return obj.total_items
    total_items_count.short_description = 'Total Items'

    def subtotal_display(self, obj):
        return format_html('<strong>₹{:,.2f}</strong>', obj.subtotal)
    subtotal_display.short_description = 'Subtotal'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'variant', 'quantity', 'unit_price', 'line_total_display']
    list_filter = ['added_at']
    search_fields = ['cart__customer__username', 'product__name']
    readonly_fields = ['unit_price', 'line_total', 'added_at', 'updated_at']

    def line_total_display(self, obj):
        return format_html('<strong>₹{:,.2f}</strong>', obj.line_total)
    line_total_display.short_description = 'Line Total'


class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 0
    fields = ['product', 'added_at']
    readonly_fields = ['added_at']


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['customer', 'items_count', 'created_at']
    search_fields = ['customer__username', 'customer__email']
    readonly_fields = ['created_at', 'items_count']
    inlines = [WishlistItemInline]

    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'Items'


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ['wishlist', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['wishlist__customer__username', 'product__name']
    readonly_fields = ['added_at']

