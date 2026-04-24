"""
Custom Email Backend for GoDaddy Titan Mail SMTP
Handles SSL certificate verification issues with self-signed certificates
"""

import ssl
from django.core.mail.backends.smtp import EmailBackend
import smtplib

class GoDaddySMTPBackend(EmailBackend):
    """
    Custom SMTP backend for GoDaddy Titan Mail.
    Overrides open() to bypass self-signed certificate verification.
    """

    def open(self):
        if self.connection:
            return False
        
        # Create SSL context that skips certificate verification
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        try:
            if self.use_ssl:
                # Port 465 — direct SSL connection
                self.connection = smtplib.SMTP_SSL(
                    self.host,
                    self.port,
                    timeout=self.timeout,
                    context=ssl_context,
                )
            else:
                # Port 587 — STARTTLS upgrade
                self.connection = smtplib.SMTP(
                    self.host,
                    self.port,
                    timeout=self.timeout,
                )
                self.connection.ehlo()
                self.connection.starttls(context=ssl_context)
                self.connection.ehlo()

            if self.username and self.password:
                self.connection.login(self.username, self.password)

            return True

        except Exception:
            if not self.fail_silently:
                raise
            return False


class SecureGoDaddySMTPBackend(EmailBackend):
    """
    More secure variant that only disables hostname checking but still validates certs.
    Use this if possible, fallback to GoDaddySMTPBackend if this doesn't work.
    """
    
    def _init_connection(self):
        """Initialize SMTP connection with minimal SSL context modifications."""
        if self.connection is not None:
            return False
        
        try:
            # Create SSL context that validates certs but doesn't check hostname
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            
            if self.use_ssl:
                self.connection = self.connection_class(
                    self.host,
                    self.port,
                    timeout=self.timeout,
                    context=ssl_context,
                )
            else:
                self.connection = self.connection_class(
                    self.host,
                    self.port,
                    timeout=self.timeout,
                )
                self.connection.starttls(context=ssl_context)
            
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            
            return True
        except Exception as e:
            if not self.fail_silently:
                raise
            return False
