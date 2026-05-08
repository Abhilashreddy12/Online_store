#!/usr/bin/env python
"""
Test and Debug Email Configuration
This script tests the Titan Mail SMTP connection and sends a test email
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shopping_store.settings')
sys.path.insert(0, str(Path(__file__).parent))

django.setup()

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
import smtplib
import ssl

print("=" * 60)
print("EMAIL CONFIGURATION DEBUG")
print("=" * 60)

# 1. Check environment variables
print("\n1. ENVIRONMENT VARIABLES:")
print(f"   EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"   EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"   EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"   EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}")
print(f"   EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"   DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
print(f"   EMAIL_BACKEND: {settings.EMAIL_BACKEND}")

# 2. Verify credentials exist
print("\n2. CREDENTIALS CHECK:")
if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
    print("   ❌ ERROR: Missing EMAIL_HOST_USER or EMAIL_HOST_PASSWORD")
    sys.exit(1)
else:
    print(f"   ✓ EMAIL_HOST_USER is set")
    print(f"   ✓ EMAIL_HOST_PASSWORD is set")

# 3. Test SMTP Connection
print("\n3. TESTING SMTP CONNECTION:")
try:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connection = smtplib.SMTP(
        settings.EMAIL_HOST,
        settings.EMAIL_PORT,
        timeout=30
    )
    print(f"   ✓ Connected to {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
    
    # Try STARTTLS
    connection.starttls(context=ssl_context)
    print(f"   ✓ STARTTLS successful")
    
    # Try login
    connection.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
    print(f"   ✓ Authentication successful")
    
    connection.quit()
    print("   ✓ SMTP connection test PASSED")
    
except Exception as e:
    print(f"   ❌ SMTP connection test FAILED: {str(e)}")
    sys.exit(1)

# 4. Test sending email
print("\n4. TESTING EMAIL SEND:")
try:
    test_email = settings.EMAIL_HOST_USER  # Send to self for testing
    
    subject = "🧪 TEST EMAIL - Titan Mail Configuration"
    message = """
    This is a test email to verify your Titan Mail SMTP configuration is working correctly.
    
    If you received this email, your email system is operational!
    
    Configuration Details:
    - Host: {host}
    - Port: {port}
    - TLS: {tls}
    - From: {from_email}
    """.format(
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        tls=settings.EMAIL_USE_TLS,
        from_email=settings.DEFAULT_FROM_EMAIL
    )
    
    result = send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[test_email],
        fail_silently=False
    )
    
    print(f"   ✓ Test email sent successfully to {test_email}")
    print(f"   ✓ EMAIL SEND TEST PASSED")
    
except Exception as e:
    print(f"   ❌ Email send test FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED - Email system is operational!")
print("=" * 60)
