#!/usr/bin/env python
"""
Test Order Creation and Email Signal
Simulates creating an order and checks if the email signal fires
"""

import os
import sys
import django
from pathlib import Path
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shopping_store.settings')
sys.path.insert(0, str(Path(__file__).parent))

django.setup()

from django.contrib.auth.models import User
from orders.models import Order, OrderItem
from catalog.models import Product
from customers.models import Address

print("=" * 60)
print("ORDER CREATION AND EMAIL SIGNAL TEST")
print("=" * 60)

try:
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='test_customer',
        defaults={
            'email': 'info@madiriclet.com',
            'first_name': 'Test',
            'last_name': 'Customer'
        }
    )
    print(f"\n✓ User: {user.username} ({user.email})")
    
    # Get or create address
    address, _ = Address.objects.get_or_create(
        customer=user,
        address_type='shipping',
        defaults={
            'full_name': 'Test Customer',
            'phone': '9999999999',
            'address_line1': 'Test Address',
            'city': 'Test City',
            'state': 'Test State',
            'postal_code': '123456',
            'country': 'IN',
            'is_default': True
        }
    )
    print(f"✓ Address: {address.full_name}")
    
    # Create an order
    print(f"\nCreating new order...")
    order = Order.objects.create(
        customer=user,
        shipping_address=address,
        subtotal=Decimal('1000.00'),
        tax_amount=Decimal('100.00'),
        shipping_cost=Decimal('50.00'),
        discount_amount=Decimal('0.00'),
        total_amount=Decimal('1150.00'),
        status='PENDING',
        payment_method='RAZORPAY'
    )
    
    print(f"✓ Order Created:")
    print(f"  - Order Number: {order.order_number}")
    print(f"  - Customer: {order.customer.email}")
    print(f"  - Total: {order.total_amount}")
    print(f"  - Status: {order.status}")
    
    print(f"\n✓ ORDER CREATION TEST PASSED")
    print(f"  If you received an email to {user.email}, the signal worked!")
    
except Exception as e:
    print(f"\n❌ TEST FAILED: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
