import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shopping_store.settings')
django.setup()

from orders.models import Order, OrderItem
from django.contrib.auth.models import User
from catalog.models import Review

print("=== Database Check ===")
print(f"Total orders: {Order.objects.count()}")
print(f"Delivered orders: {Order.objects.filter(status='DELIVERED').count()}")
print(f"Total users: {User.objects.count()}")
print(f"Total reviews: {Review.objects.count()}")

# Check specific orders
if Order.objects.exists():
    print("\n=== Order Details ===")
    for order in Order.objects.all()[:5]:
        print(f"Order {order.order_number}: Status={order.status}, Customer={order.customer.username}, Items={order.items.count()}")
        
# Check if any user has delivered orders
if User.objects.exists():
    print("\n=== User Delivered Orders ===")
    for user in User.objects.all():
        delivered = Order.objects.filter(customer=user, status='DELIVERED').count()
        if delivered > 0:
            print(f"User {user.username}: {delivered} delivered order(s)")
            # Check products in delivered orders
            items = OrderItem.objects.filter(order__customer=user, order__status='DELIVERED')
            print(f"  Products in delivered orders: {items.count()}")
            for item in items[:3]:
                has_review = Review.objects.filter(product=item.product, customer_email=user.email).exists()
                print(f"    - {item.product.name} (Reviewed: {has_review})")
