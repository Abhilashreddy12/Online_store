from django.core.management.base import BaseCommand
from catalog.models import Product, ProductVariant, Size, Color


class Command(BaseCommand):
    help = 'Generate default variants for products without any variants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Generate variants for all products',
        )
        parser.add_argument(
            '--product-id',
            type=int,
            help='Generate variants for specific product by ID',
        )

    def handle(self, *args, **options):
        if options['product_id']:
            products = Product.objects.filter(id=options['product_id'])
            if not products.exists():
                self.stdout.write(self.style.ERROR(f"Product with ID {options['product_id']} not found"))
                return
        elif options['all']:
            products = Product.objects.all()
        else:
            products = Product.objects.filter(variants__isnull=True).distinct()

        if not products.exists():
            self.stdout.write(self.style.WARNING('No products found that need variants'))
            return

        # Get or create default sizes
        sizes = Size.objects.all()
        if not sizes.exists():
            default_sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
            for idx, size_name in enumerate(default_sizes):
                Size.objects.get_or_create(
                    name=size_name,
                    defaults={'code': size_name, 'display_order': idx}
                )
            sizes = Size.objects.all()
            self.stdout.write(self.style.SUCCESS(f'Created {len(default_sizes)} default sizes'))

        # Get or create default colors
        colors = Color.objects.all()
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
            self.stdout.write(self.style.SUCCESS(f'Created {len(default_colors)} default colors'))

        # Generate variants for each product
        total_variants_created = 0
        for product in products:
            if product.variants.exists():
                self.stdout.write(self.style.WARNING(f'Skipping {product.name} - already has {product.variants.count()} variants'))
                continue

            variants_created = 0
            for size in sizes:
                for color in colors:
                    if not ProductVariant.objects.filter(
                        product=product,
                        size=size,
                        color=color
                    ).exists():
                        sku = f"{product.sku}-{size.code}-{color.code}".upper()
                        ProductVariant.objects.create(
                            product=product,
                            size=size,
                            color=color,
                            sku=sku,
                            price_adjustment=0,
                            stock_quantity=product.stock_quantity,
                            is_active=True
                        )
                        variants_created += 1

            total_variants_created += variants_created
            self.stdout.write(
                self.style.SUCCESS(f'✓ {product.name}: Created {variants_created} variants')
            )

        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Total: {total_variants_created} variants created for {products.count()} products')
        )
