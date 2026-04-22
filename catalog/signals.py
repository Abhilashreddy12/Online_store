from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Product, ProductVariant, Size, Color


@receiver(post_save, sender=Product)
def create_default_variants(sender, instance, created, **kwargs):
    """
    Automatically create default variants when a product is created.
    Creates one variant for each combination of default sizes and colors.
    """
    if created:
        # Get all active sizes and colors
        sizes = Size.objects.filter()
        colors = Color.objects.filter()
        
        # If no sizes or colors exist, create defaults
        if not sizes.exists():
            default_sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
            for idx, size_name in enumerate(default_sizes):
                Size.objects.get_or_create(
                    name=size_name,
                    defaults={'code': size_name, 'display_order': idx}
                )
            sizes = Size.objects.all()
        
        if not colors.exists():
            default_colors = [
                ('Black', '#000000'),
                ('White', '#FFFFFF'),
                ('Blue', '#0000FF'),
                ('Red', '#FF0000'),
                ('Green', '#00AA00'),
            ]
            for idx, (color_name, hex_code) in enumerate(default_colors):
                Color.objects.get_or_create(
                    name=color_name,
                    defaults={'code': hex_code, 'display_order': idx}
                )
            colors = Color.objects.all()
        
        # Create variants for each size and color combination
        for size in sizes:
            for color in colors:
                # Check if variant already exists
                if not ProductVariant.objects.filter(
                    product=instance,
                    size=size,
                    color=color
                ).exists():
                    sku = f"{instance.sku}-{size.code}-{color.code}".upper()
                    ProductVariant.objects.create(
                        product=instance,
                        size=size,
                        color=color,
                        sku=sku,
                        price_adjustment=0,
                        stock_quantity=instance.stock_quantity,
                        is_active=True
                    )
