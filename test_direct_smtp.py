#!/usr/bin/env python
"""
Direct SMTP Connection Test - No Django dependency
Tests if we can connect to Titan Mail SMTP server
"""

import smtplib
import ssl

HOST = 'smtpout.secureserver.net'
PORT = 465
USER = 'info@madiriclet.com'
PASSWORD = 'aBhi@12345.ab'

print("=" * 60)
print("DIRECT SMTP CONNECTION TEST")
print("=" * 60)
print(f"\nConnecting to {HOST}:{PORT} (SSL/Direct)")
print(f"User: {USER}")

try:
    # Create SSL context that skips certificate verification (like GoDaddySMTPBackend does)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    print("\nAttempting SMTP_SSL connection...")
    connection = smtplib.SMTP_SSL(
        HOST,
        PORT,
        timeout=30,
        context=ssl_context
    )
    print("✓ Connected via SMTP_SSL")
    
    print("\nAttempting login...")
    connection.login(USER, PASSWORD)
    print("✓ Login successful")
    
    # Check supported SMTP features
    print("\nSMTP Server capabilities:")
    print(f"  - ESMTP: {connection.has_extn('ESMTP')}")
    print(f"  - 8BITMIME: {connection.has_extn('8BITMIME')}")
    print(f"  - AUTH: {connection.has_extn('AUTH')}")
    
    connection.quit()
    print("\n✓ CONNECTION TEST PASSED")
    
except Exception as e:
    print(f"\n❌ CONNECTION TEST FAILED")
    print(f"Error: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
