#!/usr/bin/env python
"""
Django Email Send Test
Tests sending a real email through Django's email system
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shopping_store.settings')
sys.path.insert(0, str(Path(__file__).parent))

django.setup()

from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings

print("=" * 60)
print("DJANGO EMAIL SEND TEST")
print("=" * 60)

print(f"\nEmail Configuration:")
print(f"  Backend: {settings.EMAIL_BACKEND}")
print(f"  Host: {settings.EMAIL_HOST}")
print(f"  Port: {settings.EMAIL_PORT}")
print(f"  TLS: {settings.EMAIL_USE_TLS}")
print(f"  SSL: {settings.EMAIL_USE_SSL}")
print(f"  From: {settings.DEFAULT_FROM_EMAIL}")

test_recipient = settings.EMAIL_HOST_USER  # Send to self for testing

print(f"\nSending test email to: {test_recipient}")

try:
    # Simple send_mail test
    result = send_mail(
        subject="🧪 Test Email - Django Configuration",
        message="This is a test email sent through Django. If you received this, the configuration is working!",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[test_recipient],
        fail_silently=False,
    )
    
    print(f"✓ Email sent successfully (result: {result})")
    print("\n✓ DJANGO EMAIL TEST PASSED")
    
except Exception as e:
    print(f"❌ Email send failed: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
