"""
Django Signals for Customer-related Email Notifications
Automatically triggers email sending on customer events:
- Welcome email when a new user registers
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

# Import email service
from orders.email_service import CustomerEmailService


@receiver(post_save, sender=User)
def send_welcome_email_on_registration(sender, instance, created, **kwargs):
    """
    Signal: Sends welcome email when a new user is created
    SECURITY: Runs asynchronously with error handling
    
    Args:
        instance: User instance
        created: Boolean - True if user was just created
    """
    if created and instance.email:
        try:
            # Send welcome email to new user
            CustomerEmailService.send_welcome_email(instance)
            logger.info(f"Welcome email sent to new user {instance.username}")
        except Exception as e:
            logger.error(f"Error sending welcome email to {instance.username}: {str(e)}")
