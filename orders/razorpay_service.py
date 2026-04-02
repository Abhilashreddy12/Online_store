"""
Razorpay Payment Integration Service

This module handles all Razorpay API interactions securely:
- Creating orders on backend (never exposing secret)
- Verifying payment signatures using HMAC SHA256
- Updating payment status
- Preventing duplicate payments with idempotency keys
- Proper error handling and logging

SECURITY NOTES:
- Razorpay secret key is NEVER exposed to frontend
- All signature verification happens on backend
- Idempotency keys prevent duplicate payment processing
- Payment status is verified before order confirmation
"""

import logging
import hashlib
import hmac
import uuid
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
import razorpay

logger = logging.getLogger(__name__)


class RazorpayPaymentService:
    """
    Service class for Razorpay payment operations.
    Requires RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in environment variables.
    """

    def __init__(self):
        """Initialize Razorpay client with API credentials."""
        try:
            self.key_id = settings.RAZORPAY_KEY_ID
            self.key_secret = settings.RAZORPAY_KEY_SECRET
        except AttributeError:
            logger.error("Razorpay credentials not configured in settings")
            raise ValueError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be set in environment variables")

        # Initialize Razorpay client
        self.client = razorpay.Client(auth=(self.key_id, self.key_secret))

    def create_order(self, order):
        """
        Create a Razorpay order for the given Order instance.
        
        Args:
            order: Order instance with customer, total_amount, etc.
            
        Returns:
            dict: Contains razorpay_order_id and idempotency_key
            
        Raises:
            Exception: If order creation fails
        """
        try:
            # Generate idempotency key to prevent duplicate orders
            idempotency_key = str(uuid.uuid4())

            # Prepare order data (amounts in paise for Razorpay)
            amount_paise = int(order.total_amount * 100)

            order_data = {
                'amount': amount_paise,
                'currency': 'INR',
                'receipt': f"receipt#{order.order_number}",
                'payment_capture': 1,  # Auto-capture on authorization
                'notes': {
                    'order_number': order.order_number,
                    'customer_email': order.customer.email,
                    'customer_name': order.customer.get_full_name() or order.customer.username,
                }
            }

            # Create order via Razorpay API
            response = self.client.order.create(data=order_data)

            logger.info(f"Razorpay order created: {response.get('id')} for order {order.order_number}")

            return {
                'razorpay_order_id': response['id'],
                'idempotency_key': idempotency_key,
                'amount': amount_paise,
                'currency': response.get('currency', 'INR')
            }

        except Exception as e:
            logger.error(f"Failed to create Razorpay order for {order.order_number}: {str(e)}")
            raise

    def verify_payment_signature(self, razorpay_order_id, razorpay_payment_id, razorpay_signature):
        """
        Verify the Razorpay payment signature using HMAC SHA256.
        This is CRITICAL for security - prevents tampering with payment details.
        
        Args:
            razorpay_order_id: Order ID from Razorpay
            razorpay_payment_id: Payment ID from Razorpay
            razorpay_signature: Signed hash from Razorpay checkout
            
        Returns:
            bool: True if signature is valid, False otherwise
            
        SECURITY: Signature verification MUST be done before trusting any payment data
        """
        try:
            # Create the signature string as per Razorpay documentation
            signature_string = f"{razorpay_order_id}|{razorpay_payment_id}"

            # Create HMAC SHA256 hash using secret key
            expected_signature = hmac.new(
                self.key_secret.encode(),
                signature_string.encode(),
                hashlib.sha256
            ).hexdigest()

            # Constant-time comparison to prevent timing attacks
            is_valid = hmac.compare_digest(expected_signature, razorpay_signature)

            if is_valid:
                logger.info(f"Payment signature verified for order {razorpay_order_id}")
            else:
                logger.warning(f"Payment signature verification FAILED for order {razorpay_order_id}")
                logger.warning(f"Expected: {expected_signature}, Got: {razorpay_signature}")

            return is_valid

        except Exception as e:
            logger.error(f"Error verifying payment signature: {str(e)}")
            return False

    def get_payment_details(self, razorpay_payment_id):
        """
        Fetch payment details from Razorpay API.
        
        Args:
            razorpay_payment_id: Payment ID to fetch details for
            
        Returns:
            dict: Payment details from Razorpay
            
        Raises:
            Exception: If API call fails
        """
        try:
            payment = self.client.payment.fetch(razorpay_payment_id)
            logger.info(f"Fetched payment details for {razorpay_payment_id}")
            return payment
        except Exception as e:
            logger.error(f"Failed to fetch payment details: {str(e)}")
            raise

    def capture_payment(self, razorpay_payment_id, amount):
        """
        Capture an authorized payment (if not auto-captured).
        
        Args:
            razorpay_payment_id: Payment ID to capture
            amount: Amount in paise
            
        Returns:
            dict: Capture response from Razorpay
        """
        try:
            payment = self.client.payment.capture(razorpay_payment_id, amount)
            logger.info(f"Payment captured: {razorpay_payment_id}")
            return payment
        except Exception as e:
            logger.error(f"Failed to capture payment {razorpay_payment_id}: {str(e)}")
            raise

    def refund_payment(self, razorpay_payment_id, amount=None):
        """
        Refund a payment (full or partial).
        
        Args:
            razorpay_payment_id: Payment ID to refund
            amount: Amount in paise (None for full refund)
            
        Returns:
            dict: Refund response from Razorpay
        """
        try:
            refund_data = {}
            if amount:
                refund_data['amount'] = amount

            refund = self.client.refund.create(data={
                'payment_id': razorpay_payment_id,
                **refund_data
            })
            logger.info(f"Refund created for payment {razorpay_payment_id}")
            return refund
        except Exception as e:
            logger.error(f"Failed to refund payment {razorpay_payment_id}: {str(e)}")
            raise


def verify_idempotency(idempotency_key):
    """
    Check if a payment with this idempotency key already exists.
    Prevents duplicate payment processing.
    
    Args:
        idempotency_key: Unique key for idempotency
        
    Returns:
        bool: True if payment already exists, False otherwise
    """
    from .models import RazorpayPayment
    
    try:
        existing = RazorpayPayment.objects.filter(
            idempotency_key=idempotency_key
        ).exists()
        return existing
    except Exception as e:
        logger.error(f"Error checking idempotency: {str(e)}")
        return False
