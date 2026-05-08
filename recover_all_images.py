#!/usr/bin/env python
"""Create placeholder images for all products"""

import os
import django
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shopping_store.settings')
django.setup()

from catalog.models import ProductImage, Product

print("=" * 70)
print("GENERATING PLACEHOLDER IMAGES FOR ALL PRODUCTS")
print("=" * 70)

def create_product_image(product_name, filename, color_bg=(230, 230, 250), color_accent=(212, 175, 55)):
    """Create a beautiful placeholder image"""
    try:
        # Create image with white background
        img = Image.new('RGB', (500, 500), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # Draw gradient-like background (simplified with rectangle)
        draw.rectangle([0, 0, 500, 500], fill=color_bg)
        
        # Draw gold border
        border_width = 8
        draw.rectangle(
            [border_width, border_width, 500-border_width, 500-border_width],
            outline=color_accent,
            width=border_width
        )
        
        # Draw inner border
        draw.rectangle(
            [border_width+4, border_width+4, 500-border_width-4, 500-border_width-4],
            outline=(200, 200, 200),
            width=2
        )
        
        # Add text
        text = product_name
        try:
            # Try to use a better font
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        # Draw text with shadow effect
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        x = (500 - text_width) // 2
        y = (500 - text_height) // 2
        
        # Shadow
        draw.text((x+3, y+3), text, fill=(150, 150, 150), font=font)
        # Main text
        draw.text((x, y), text, fill=(50, 50, 50), font=font)
        
        # Add logo indicator
        draw.ellipse([20, 20, 80, 80], outline=color_accent, width=3)
        draw.text((50, 50), "🛍️", fill=color_accent)
        
        # Save to file
        media_path = Path('media') / filename
        media_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save as JPEG
        if filename.endswith('.webp'):
            filename = filename.replace('.webp', '.jpg')
            media_path = Path('media') / filename
        
        img.save(media_path, 'JPEG', quality=90)
        print(f"  ✓ Created: {filename} ({media_path.stat().st_size} bytes)")
        return filename
    except Exception as e:
        print(f"  ✗ Error creating {filename}: {e}")
        return None

# Color palette for different products
colors = [
    ((230, 230, 250), (212, 175, 55)),  # Blue + Gold
    ((250, 240, 230), (212, 175, 55)),  # Peach + Gold
    ((240, 250, 240), (212, 175, 55)),  # Green + Gold
    ((250, 230, 240), (212, 175, 55)),  # Pink + Gold
]

print("\n[GENERATING IMAGES]")
print("-" * 70)

for idx, product in enumerate(Product.objects.all()):
    images = product.images.all()
    if images.exists():
        img = images.first()
        # Check if it's a Cloudinary image
        if str(img.image).startswith(('yz', 'myd', 'https')):
            print(f"\n📦 {product.name}")
            color = colors[idx % len(colors)]
            new_filename = f"products/product_{product.id}.jpg"
            new_path = create_product_image(product.name, new_filename, color[0], color[1])
            if new_path:
                img.image = new_path
                img.save()
                print(f"   ✓ Database updated with local image")

print("\n" + "=" * 70)
print("VERIFICATION")
print("=" * 70)

# Final verification
for product in Product.objects.all():
    images = product.images.all()
    print(f"\n📦 {product.name}")
    for img in images:
        media_path = Path('media') / str(img.image)
        exists = "✓" if media_path.exists() else "✗"
        size = f"({media_path.stat().st_size} bytes)" if media_path.exists() else "(missing)"
        print(f"   {exists} {img.image} {size}")

print("\n" + "=" * 70)
print("✓ IMAGE RECOVERY COMPLETE!")
print("=" * 70)
