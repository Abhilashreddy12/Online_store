#!/usr/bin/env python
"""Fix missing product images and references"""

import os
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shopping_store.settings')
django.setup()

from catalog.models import ProductImage, Product
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw
import io

print("=" * 60)
print("PRODUCT IMAGE RECOVERY SCRIPT")
print("=" * 60)

# Step 1: Fix image path references
print("\n[STEP 1] Fixing image path references...")
updates = [
    ('products/multi_col_kurthi', 'products/multi_col_kurthi.webp'),
    ('products/kurtha_1', 'products/kurtha_1.jpg'),
]

for old_path, new_path in updates:
    images = ProductImage.objects.filter(image=old_path)
    count = images.update(image=new_path)
    if count > 0:
        print(f"  ✓ Updated {count} image(s): {old_path} -> {new_path}")

# Step 2: Show all current images
print("\n[STEP 2] Current Product Images in Database:")
for img in ProductImage.objects.all():
    print(f"  - Product: {img.product.name}")
    print(f"    Image Path: {img.image}")
    print(f"    Is Primary: {img.is_primary}")
    print()

# Step 3: Generate placeholder images for Cloudinary images
print("[STEP 3] Generating placeholder images for missing local files...")

def create_placeholder_image(product_name, filename):
    """Create a simple placeholder image"""
    try:
        # Create image
        img = Image.new('RGB', (400, 400), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        
        # Draw border
        draw.rectangle([10, 10, 390, 390], outline=(212, 175, 55), width=3)
        
        # Add text
        text = product_name[:20] + "..." if len(product_name) > 20 else product_name
        draw.text((200, 200), text, fill=(100, 100, 100), anchor="mm")
        
        # Save to memory
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        # Save to file
        media_path = Path('media') / filename
        media_path.parent.mkdir(parents=True, exist_ok=True)
        with open(media_path, 'wb') as f:
            f.write(img_io.read())
        
        return True
    except Exception as e:
        print(f"  ✗ Error creating image: {e}")
        return False

# Check for missing local image files and create placeholders if needed
print("\n[STEP 4] Checking for missing image files...")
for img in ProductImage.objects.all():
    img_path = Path('media') / str(img.image)
    if not img_path.exists() and not str(img.image).startswith('yz') and not str(img.image).startswith('myd'):
        print(f"  ⚠ Missing local file: {img.image}")
        # Try to create placeholder
        if create_placeholder_image(img.product.name, str(img.image)):
            print(f"    ✓ Created placeholder: {img.image}")
    elif img_path.exists():
        print(f"  ✓ File exists: {img.image} ({img_path.stat().st_size} bytes)")

print("\n" + "=" * 60)
print("RECOVERY COMPLETE!")
print("=" * 60)
