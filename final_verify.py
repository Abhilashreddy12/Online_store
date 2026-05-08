#!/usr/bin/env python
"""Final verification of all product images"""

import os
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shopping_store.settings')
django.setup()

from catalog.models import ProductImage, Product

print("\n" + "=" * 70)
print("FINAL IMAGE VERIFICATION")
print("=" * 70 + "\n")

all_good = True

for product in Product.objects.all().order_by('name'):
    images = product.images.all()
    print(f"📦 {product.name}")
    
    if not images.exists():
        print("   ⚠ NO IMAGES FOUND!")
        all_good = False
    else:
        for img in images:
            media_path = Path('media') / str(img.image)
            status = "✓" if media_path.exists() else "✗"
            size = f"({media_path.stat().st_size} bytes)" if media_path.exists() else "(MISSING)"
            print(f"   {status} {img.image} {size}")
            if not media_path.exists():
                all_good = False
    print()

print("=" * 70)
if all_good:
    print("✓ ALL IMAGES RECOVERED AND VERIFIED!")
    print("  - All products have images")
    print("  - All image files exist on disk")
    print("  - Database references are correct")
else:
    print("⚠ Some images are still missing")
print("=" * 70 + "\n")
