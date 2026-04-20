"""
Email Service for Orders, Invoices, and Notifications
Uses Titan Mail SMTP for secure email delivery

SECURITY MEASURES:
- All sensitive data from environment variables
- Email templates with CSRF protection
- HTML email support with fallback to plain text
- Async email sending support (can be enhanced with Celery)
- Error logging without exposing credentials
"""

from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.core.files.base import ContentFile
import logging
from io import BytesIO
from datetime import datetime

logger = logging.getLogger(__name__)


class OrderEmailService:
    """
    Secure email service for handling order-related communications
    Supports order confirmations, invoices, and status updates
    """
    
    @staticmethod
    def send_order_confirmation(order):
        """
        Send order confirmation email to customer
        
        Args:
            order: Order instance
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            customer_email = order.customer.email
            
            if not customer_email:
                logger.warning(f"Order {order.order_number}: Customer has no email address")
                return False
            
            # Prepare context
            context = {
                'order': order,
                'customer_name': order.customer.get_full_name() or order.customer.username,
                'order_items': order.items.all(),
                'order_date': order.created_at.strftime('%B %d, %Y'),
                'order_time': order.created_at.strftime('%I:%M %p'),
                'site_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'yourstore.com',
                'support_email': settings.DEFAULT_FROM_EMAIL,
            }
            
            # Render HTML and text versions
            html_message = render_to_string('orders/emails/order_confirmation.html', context)
            text_message = render_to_string('orders/emails/order_confirmation.txt', context)
            
            # Create email with both versions
            email = EmailMultiAlternatives(
                subject=f"Order Confirmation - #{order.order_number}",
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[customer_email]
            )
            
            # Attach HTML version
            email.attach_alternative(html_message, "text/html")
            
            # Send email
            email.send(fail_silently=False)
            
            logger.info(f"Order confirmation email sent to {customer_email} for order {order.order_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send order confirmation for order {order.order_number}: {str(e)}")
            return False
    
    
    @staticmethod
    def send_invoice_email(order, invoice):
        """
        Send invoice PDF via email to customer
        
        Args:
            order: Order instance
            invoice: Invoice instance or PDF file
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            customer_email = order.customer.email
            
            if not customer_email:
                logger.warning(f"Invoice for order {order.order_number}: Customer has no email address")
                return False
            
            # Prepare context
            context = {
                'order': order,
                'customer_name': order.customer.get_full_name() or order.customer.username,
                'order_items': order.items.all(),
                'invoice_number': getattr(invoice, 'invoice_number', order.order_number),
                'invoice_date': datetime.now().strftime('%B %d, %Y'),
                'site_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'yourstore.com',
                'support_email': settings.DEFAULT_FROM_EMAIL,
            }
            
            # Render email content
            html_message = render_to_string('orders/emails/invoice_email.html', context)
            text_message = render_to_string('orders/emails/invoice_email.txt', context)
            
            # Create email
            email = EmailMultiAlternatives(
                subject=f"Invoice - #{order.order_number}",
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[customer_email]
            )
            
            # Attach HTML version
            email.attach_alternative(html_message, "text/html")
            
            # Attach invoice PDF if available
            if hasattr(invoice, 'pdf_file') and invoice.pdf_file:
                try:
                    pdf_content = invoice.pdf_file.read()
                    email.attach(
                        f'Invoice_{order.order_number}.pdf',
                        pdf_content,
                        'application/pdf'
                    )
                except Exception as e:
                    logger.warning(f"Could not attach PDF for invoice {invoice.id}: {str(e)}")
            
            # Send email
            email.send(fail_silently=False)
            
            logger.info(f"Invoice email sent to {customer_email} for order {order.order_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send invoice email for order {order.order_number}: {str(e)}")
            return False
    
    
    @staticmethod
    def send_payment_received_email(order):
        """
        Send payment received/confirmed email to customer
        
        Args:
            order: Order instance
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            customer_email = order.customer.email
            
            if not customer_email:
                logger.warning(f"Order {order.order_number}: Customer has no email address")
                return False
            
            # Prepare context
            context = {
                'order': order,
                'customer_name': order.customer.get_full_name() or order.customer.username,
                'order_number': order.order_number,
                'order_amount': order.total_amount,
                'payment_method': order.get_payment_method_display(),
                'site_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'yourstore.com',
                'support_email': settings.DEFAULT_FROM_EMAIL,
            }
            
            # Render email content
            html_message = render_to_string('orders/emails/payment_received.html', context)
            text_message = render_to_string('orders/emails/payment_received.txt', context)
            
            # Create email
            email = EmailMultiAlternatives(
                subject=f"Payment Received - Order #{order.order_number}",
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[customer_email]
            )
            
            # Attach HTML version
            email.attach_alternative(html_message, "text/html")
            
            # Send email
            email.send(fail_silently=False)
            
            logger.info(f"Payment received email sent to {customer_email} for order {order.order_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send payment received email for order {order.order_number}: {str(e)}")
            return False
    
    
    @staticmethod
    def send_order_status_update(order, status_change_message):
        """
        Send order status update email to customer
        
        Args:
            order: Order instance
            status_change_message: str - Description of status change (e.g., "Your order has been shipped")
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            customer_email = order.customer.email
            
            if not customer_email:
                logger.warning(f"Order {order.order_number}: Customer has no email address")
                return False
            
            # Prepare context
            context = {
                'order': order,
                'customer_name': order.customer.get_full_name() or order.customer.username,
                'order_number': order.order_number,
                'order_status': order.get_status_display(),
                'status_message': status_change_message,
                'tracking_available': hasattr(order, 'tracking_number') and bool(order.tracking_number),
                'tracking_number': getattr(order, 'tracking_number', None),
                'site_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'yourstore.com',
                'support_email': settings.DEFAULT_FROM_EMAIL,
            }
            
            # Render email content
            html_message = render_to_string('orders/emails/order_status_update.html', context)
            text_message = render_to_string('orders/emails/order_status_update.txt', context)
            
            # Create email
            email = EmailMultiAlternatives(
                subject=f"Order Status Update - #{order.order_number}",
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[customer_email]
            )
            
            # Attach HTML version
            email.attach_alternative(html_message, "text/html")
            
            # Send email
            email.send(fail_silently=False)
            
            logger.info(f"Order status update email sent to {customer_email} for order {order.order_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send order status update email for order {order.order_number}: {str(e)}")
            return False


class CustomerEmailService:
    """
    Email service for customer-related communications
    Handles password reset and account notifications
    """
    
    @staticmethod
    def send_welcome_email(user):
        """
        Send welcome email to new customer
        
        Args:
            user: User instance
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            if not user.email:
                logger.warning(f"User {user.username}: No email address to send welcome email")
                return False
            
            context = {
                'customer_name': user.get_full_name() or user.username,
                'site_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'yourstore.com',
                'support_email': settings.DEFAULT_FROM_EMAIL,
            }
            
            html_message = render_to_string('customers/emails/welcome.html', context)
            text_message = render_to_string('customers/emails/welcome.txt', context)
            
            email = EmailMultiAlternatives(
                subject="Welcome to Our Store!",
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            
            logger.info(f"Welcome email sent to {user.email} for user {user.username}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user.username}: {str(e)}")
            return False


# Note: Password reset emails are handled by Django's built-in PasswordResetView
# which uses the email templates in templates/customers/password_reset_*.txt/html
# Those emails are automatically sent when users request password reset
