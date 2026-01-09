from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from cloudinary.models import CloudinaryField


class Category(models.Model):
    """Product categories for organizing clothing items"""
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = CloudinaryField('image', blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug: 
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(models.Model):
    """Clothing brands"""
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    logo = CloudinaryField('logo', blank=True, null=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    """Main product model for clothing items"""
    GENDER_CHOICES = [
        ('M', 'Men'),
        ('F', 'Women'),
        ('U', 'Unisex'),
        ('K', 'Kids'),
    ]

    name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    sku = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True)
    
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                                       validators=[MinValueValidator(0)], 
                                       help_text="Original price for discount display")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     validators=[MinValueValidator(0)],
                                     help_text="Cost for profit calculation")
    
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='U')
    
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, 
                                help_text="Weight in kg")
    
    material = models.CharField(max_length=200, blank=True)
    care_instructions = models.TextField(blank=True)
    
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)
    meta_keywords = models.CharField(max_length=300, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['sku']),
            models.Index(fields=['is_active', 'is_featured']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def discount_percentage(self):
        if self.compare_price and self.compare_price > self.price:
            return int(((self.compare_price - self.price) / self.compare_price) * 100)
        return 0

    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.low_stock_threshold

    def __str__(self):
        return self.name



class ProductImage(models.Model):
    """Multiple images for each product"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = CloudinaryField('image')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'created_at']

    def __str__(self):
        return f"{self.product.name} - Image {self.id}"


class Size(models.Model):
    """Available sizes"""
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.name


class Color(models.Model):
    """Available colors"""
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True, help_text="Hex color code")
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    """Product variants for different sizes and colors"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.ForeignKey(Size, on_delete=models.PROTECT)
    color = models.ForeignKey(Color, on_delete=models.PROTECT)
    sku = models.CharField(max_length=100, unique=True)
    
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                          help_text="Additional price for this variant")
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['product', 'size', 'color']
        ordering = ['product', 'size', 'color']

    @property
    def final_price(self):
        return self.product.price + self.price_adjustment

    def __str__(self):
        return f"{self.product.name} - {self.size.name} - {self.color.name}"


class Review(models.Model):
    """Product reviews"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200)
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} - {self.rating} stars by {self.customer_name}"


class Banner(models.Model):
    """Promotional banners and offers displayed on the site"""
    BANNER_TYPES = [
        ('OFFER', 'Special Offer'),
        ('SALE', 'Sale'),
        ('ANNOUNCEMENT', 'Announcement'),
        ('INFO', 'Information'),
    ]
    
    title = models.CharField(max_length=200, help_text="Banner title (e.g., 'Weekend Sale')")
    message = models.TextField(help_text="Banner message/description")
    banner_type = models.CharField(max_length=20, choices=BANNER_TYPES, default='INFO')
    
    # Optional link
    link_url = models.URLField(blank=True, help_text="Optional link URL")
    link_text = models.CharField(max_length=100, blank=True, default="Learn More")
    
    # Styling
    background_color = models.CharField(max_length=7, default='#667eea', 
                                       help_text="Hex color code (e.g., #667eea)")
    text_color = models.CharField(max_length=7, default='#ffffff',
                                  help_text="Hex color code (e.g., #ffffff)")
    
    # Scheduling
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True, 
                                    help_text="Leave empty for no end date")
    
    # Display order (higher = shown first)
    display_order = models.IntegerField(default=0, help_text="Higher numbers appear first")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-display_order', '-created_at']
        verbose_name = 'Banner/Offer'
        verbose_name_plural = 'Banners/Offers'
    
    def __str__(self):
        return self.title
    
    @property
    def is_valid(self):
        """Check if banner should be displayed"""
        if not self.is_active:
            return False
        now = timezone.now()
        if self.start_date > now:
            return False
        if self.end_date and self.end_date < now:
            return False
        return True
