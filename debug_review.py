import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shopping_store.settings')
django.setup()

from django.contrib.auth.models import User
from orders.models import OrderItem
from catalog.models import Product, Review

user = User.objects.first()
print(f"User: {user.username}")
print(f"Email: '{user.email}'")
print(f"Email is empty: {not user.email}")

# Get a product from delivered order
product = Product.objects.filter(
    orderitem__order__customer=user,
    orderitem__order__status='DELIVERED'
).first()

if product:
    print(f"\nProduct: {product.name}")
    
    # Check has_purchased
    has_purchased = OrderItem.objects.filter(
        order__customer=user,
        order__status='DELIVERED',
        product=product
    ).exists()
    print(f"Has purchased: {has_purchased}")
    
    # Check has_reviewed (current logic)
    has_reviewed_with_email = Review.objects.filter(
        product=product,
        customer_email=user.email
    ).exists()
    print(f"Has reviewed (using email): {has_reviewed_with_email}")
    
    # Check if can_review
    can_review = has_purchased and not has_reviewed_with_email
    print(f"Can review: {can_review}")
    
    # Better check - using user directly
    has_reviewed_better = Review.objects.filter(
        product=product,
        customer_name__icontains=user.username
    ).exists()
    print(f"Has reviewed (using username): {has_reviewed_better}")
