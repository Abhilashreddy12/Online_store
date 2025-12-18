from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Brand, Product, ProductImage, Size, Color, ProductVariant, Review, Banner


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'is_active', 'product_count', 'created_at']
    list_filter = ['is_active', 'created_at', 'parent']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'parent')
        }),
        ('Media', {
            'fields': ('image',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'website', 'is_active', 'product_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at']

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'is_primary', 'display_order']


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ['size', 'color', 'sku', 'price_adjustment', 'stock_quantity', 'is_active']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'brand', 'price_display', 'stock_status', 
                   'is_active', 'is_featured', 'created_at']
    list_filter = ['is_active', 'is_featured', 'gender', 'category', 'brand', 'created_at']
    search_fields = ['name', 'sku', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'discount_percentage']
    inlines = [ProductImageInline, ProductVariantInline]
    
    list_editable = ['is_active', 'is_featured']
    list_per_page = 50
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'sku', 'category', 'brand', 'gender')
        }),
        ('Description', {
            'fields': ('short_description', 'description', 'material', 'care_instructions')
        }),
        ('Pricing', {
            'fields': ('price', 'compare_price', 'cost_price', 'discount_percentage')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'low_stock_threshold')
        }),
        ('Product Details', {
            'fields': ('weight',)
        }),
        ('Status & Features', {
            'fields': ('is_active', 'is_featured')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def price_display(self, obj):
        if obj.compare_price and obj.compare_price > obj.price:
            return format_html(
                '<span style="color: red; font-weight: bold;">₹{}</span> '
                '<span style="text-decoration: line-through; color: gray;">₹{}</span> '
                '<span style="color: green;">(-{}%)</span>',
                obj.price, obj.compare_price, obj.discount_percentage
            )
        return f'₹{obj.price}'
    price_display.short_description = 'Price'

    def stock_status(self, obj):
        if obj.stock_quantity == 0:
            color = 'red'
            status = 'Out of Stock'
        elif obj.is_low_stock:
            color = 'orange'
            status = f'Low Stock ({obj.stock_quantity})'
        else:
            color = 'green'
            status = f'In Stock ({obj.stock_quantity})'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, status
        )
    stock_status.short_description = 'Stock'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'image_preview', 'is_primary', 'display_order']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['product__name', 'alt_text']
    list_editable = ['display_order', 'is_primary']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Preview'


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'display_order']
    list_editable = ['display_order']
    search_fields = ['name', 'code']


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'color_preview', 'display_order']
    list_editable = ['display_order']
    search_fields = ['name', 'code']

    def color_preview(self, obj):
        return format_html(
            '<div style="width: 30px; height: 30px; background-color: {}; border: 1px solid #ccc;"></div>',
            obj.code
        )
    color_preview.short_description = 'Preview'


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'size', 'color', 'sku', 'final_price', 'stock_quantity', 'is_active']
    list_filter = ['is_active', 'size', 'color', 'product__category']
    search_fields = ['product__name', 'sku']
    list_editable = ['is_active']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'customer_name', 'rating_display', 'is_verified_purchase', 
                   'is_approved', 'created_at']
    list_filter = ['rating', 'is_verified_purchase', 'is_approved', 'created_at']
    search_fields = ['product__name', 'customer_name', 'customer_email', 'title', 'comment']
    list_editable = ['is_approved']
    readonly_fields = ['created_at']
    
    actions = ['approve_reviews', 'disapprove_reviews']

    def rating_display(self, obj):
        stars = '⭐' * obj.rating
        return format_html('<span style="color: gold;">{}</span>', stars)
    rating_display.short_description = 'Rating'

    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} reviews approved.')
    approve_reviews.short_description = 'Approve selected reviews'

    def disapprove_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} reviews disapproved.')
    disapprove_reviews.short_description = 'Disapprove selected reviews'


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'banner_type', 'status_display', 'is_active', 'display_order', 'start_date', 'end_date']
    list_filter = ['banner_type', 'is_active', 'start_date']
    search_fields = ['title', 'message']
    list_editable = ['is_active', 'display_order']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'message', 'banner_type')
        }),
        ('Link (Optional)', {
            'fields': ('link_url', 'link_text'),
            'classes': ('collapse',)
        }),
        ('Display Settings', {
            'fields': ('background_color', 'text_color', 'display_order'),
            'description': 'Use hex color codes (e.g., #667eea for background, #ffffff for text)'
        }),
        ('Scheduling', {
            'fields': ('is_active', 'start_date', 'end_date')
        }),
    )
    
    def status_display(self, obj):
        if obj.is_valid:
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">Active</span>',
                '#48bb78'
            )
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">Inactive</span>',
            '#cbd5e0', '#4a5568'
        )
    status_display.short_description = 'Status'
