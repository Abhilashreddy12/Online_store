"""
Django Signals for Order-related Email Notifications
Automatically triggers email sending on order events:
- Order confirmation when order is created
- Payment confirmation when payment is received
- Invoice email when invoice is generated

SECURITY: All emails are sent asynchronously with error handling
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
import logging

logger = logging.getLogger(__name__)

from .models import Order
from .email_service import OrderEmailService


@receiver(post_save, sender=Order)
def send_order_confirmation_email(sender, instance, created, **kwargs):
    """
    Signal: Sends order confirmation email when a new order is created
    SECURITY: Runs asynchronously with error handling
    
    Args:
        instance: Order instance
        created: Boolean - True if order was just created
    """
    if created:
        try:
            # Send order confirmation email to customer
            OrderEmailService.send_order_confirmation(instance)
            logger.info(f"Order confirmation email triggered for order {instance.order_number}")
        except Exception as e:
            logger.error(f"Error sending order confirmation email: {str(e)}")


@receiver(post_save, sender=Order)
def send_payment_confirmation_email(sender, instance, created, update_fields, **kwargs):
    """
    Signal: Sends payment confirmation email when order status changes to PAID
    
    Args:
        instance: Order instance
        created: Boolean - True if order was just created
        update_fields: Set of field names that were updated
    """
    # Check if order status was updated and is now PAID
    if not created and update_fields and 'status' in update_fields:
        if instance.status == 'PAID':
            try:
                # Send payment received email
                OrderEmailService.send_payment_received_email(instance)
                logger.info(f"Payment confirmation email sent for order {instance.order_number}")
            except Exception as e:
                logger.error(f"Error sending payment confirmation email: {str(e)}")


# Note: Invoice emails are sent from the invoice generation handler in views.py
# This ensures the invoice PDF is attached to the email
