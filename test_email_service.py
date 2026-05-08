#!/usr/bin/env python
"""
Test Email Service
Tests the OrderEmailService directly
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shopping_store.settings')
sys.path.insert(0, str(Path(__file__).parent))

django.setup()

import logging
from django.contrib.auth.models import User
from orders.models import Order
from customers.models import Address
from decimal import Decimal
from orders.email_service import OrderEmailService

# Enable logging to see what's happening
logging.basicConfig(level=logging.DEBUG)

print("=" * 60)
print("EMAIL SERVICE TEST")
print("=" * 60)

try:
    # Get the last created order
    order = Order.objects.latest('created_at')
    print(f"\nTesting with order: {order.order_number}")
    print(f"Customer: {order.customer.email}")
    
    # Test email service
    print(f"\nCalling OrderEmailService.send_order_confirmation()...")
    result = OrderEmailService.send_order_confirmation(order)
    
    if result:
        print(f"✓ Email service returned True (success)")
        print(f"\n✓ EMAIL SERVICE TEST PASSED")
    else:
        print(f"❌ Email service returned False (failed)")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ TEST FAILED: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
