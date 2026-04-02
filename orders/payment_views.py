"""
Razorpay Payment API Views

Handles all payment-related endpoints:
- Creating Razorpay orders
- Verifying payment signatures
- Handling payment success/failure
- Invoice download

SECURITY CRITICAL:
- All endpoints require authentication
- CSRF protection enabled
- Signature verification before updating order status
- Proper error handling with logging
"""

import json
import logging
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, FileResponse, HttpResponseForbidden
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from decimal import Decimal

from .models import Order, RazorpayPayment, Invoice
from .razorpay_service import RazorpayPaymentService, verify_idempotency
from .invoice_service import InvoiceGenerator
from cart.models import Cart

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def create_razorpay_order(request):
    """
    Create a Razorpay order for checkout.
    
    This endpoint:
    - Creates order if payment_method is RAZORPAY
    - Never exposes secret key to frontend
    - Returns only essential frontend data (order_id, key_id, amount)
    
    Request POST data:
    - order_id: Order ID to process
    
    Returns JSON:
    - razorpay_order_id: Order ID for Razorpay
    - key_id: Public key for frontend
    - amount: Amount in paise
    - currency: Currency (INR)
    - order_details: Order summary
    """
    try:
        order_id = request.POST.get('order_id')
        order = get_object_or_404(Order, id=order_id, customer=request.user)

        # Check if order already has a payment
        if hasattr(order, 'razorpay_payment'):
            return JsonResponse({
                'success': False,
                'error': 'Payment already initiated for this order'
            }, status=400)

        # Check if payment method is Razorpay
        if order.payment_method != 'RAZORPAY':
            return JsonResponse({
                'success': False,
                'error': 'Invalid payment method'
            }, status=400)

        # Initialize Razorpay service
        razorpay_service = RazorpayPaymentService()

        # Create Razorpay order
        razorpay_response = razorpay_service.create_order(order)

        # Save RazorpayPayment record (status: PENDING)
        razorpay_payment = RazorpayPayment.objects.create(
            order=order,
            razorpay_order_id=razorpay_response['razorpay_order_id'],
            amount_paid=order.total_amount,
            currency=razorpay_response['currency'],
            idempotency_key=razorpay_response['idempotency_key'],
            payment_status='PENDING'
        )

        # Update order to indicate Razorpay payment initiated
        order.payment_method = 'RAZORPAY'
        order.save()

        logger.info(f"Razorpay order created for Order #{order.order_number}")

        # Return ONLY frontend-safe data (secret key is NOT included)
        return JsonResponse({
            'success': True,
            'razorpay_order_id': razorpay_response['razorpay_order_id'],
            'key_id': razorpay_service.key_id,  # Public key only
            'amount': razorpay_response['amount'],
            'currency': razorpay_response['currency'],
            'order_details': {
                'order_number': order.order_number,
                'customer_name': order.customer.get_full_name() or order.customer.username,
                'customer_email': order.customer.email,
                'total_amount': float(order.total_amount),
            }
        })

    except Exception as e:
        logger.error(f"Error creating Razorpay order: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to create payment. Please try again.'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def verify_razorpay_payment(request):
    """
    Verify Razorpay payment signature and update order status.
    
    CRITICAL SECURITY: This endpoint verifies HMAC SHA256 signature
    to ensure payment data hasn't been tampered with.
    
    Request POST data (from frontend):
    - razorpay_payment_id: Payment ID from Razorpay
    - razorpay_order_id: Order ID from Razorpay
    - razorpay_signature: Signature from Razorpay
    - order_id: Order ID from our database
    
    Returns JSON:
    - success: Boolean
    - message: Status message
    - redirect_url: Redirect to order detail page on success
    """
    try:
        data = json.loads(request.body)

        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')
        order_id = data.get('order_id')

        # Validate all required fields
        if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature, order_id]):
            return JsonResponse({
                'success': False,
                'error': 'Missing payment information'
            }, status=400)

        # Get order with authorization check
        order = get_object_or_404(Order, id=order_id, customer=request.user)

        # Get RazorpayPayment record
        razorpay_payment = get_object_or_404(
            RazorpayPayment,
            razorpay_order_id=razorpay_order_id,
            order=order
        )

        # CRITICAL: Verify signature using HMAC SHA256
        # This prevents tampering with payment data
        razorpay_service = RazorpayPaymentService()
        is_valid = razorpay_service.verify_payment_signature(
            razorpay_order_id,
            razorpay_payment_id,
            razorpay_signature
        )

        if not is_valid:
            # Signature verification failed - potential attack
            logger.warning(f"Signature verification FAILED for order {order.order_number}")
            
            razorpay_payment.payment_status = 'FAILED'
            razorpay_payment.error_message = 'Signature verification failed'
            razorpay_payment.error_code = 'SIGNATURE_MISMATCH'
            razorpay_payment.save()

            return JsonResponse({
                'success': False,
                'error': 'Payment verification failed. Please contact support.'
            }, status=400)

        # Signature verified successfully
        razorpay_payment.razorpay_payment_id = razorpay_payment_id
        razorpay_payment.razorpay_signature = razorpay_signature
        razorpay_payment.signature_verified = True
        razorpay_payment.payment_captured_at = timezone.now()
        razorpay_payment.payment_status = 'CAPTURED'
        razorpay_payment.save()

        # Update order status
        order.payment_status = 'PAID'
        order.transaction_id = razorpay_payment_id
        order.paid_at = timezone.now()
        order.status = 'PROCESSING'  # Move to processing after payment
        order.save()

        logger.info(f"Payment verified and captured for order {order.order_number}")

        # Generate invoice
        try:
            invoice_generator = InvoiceGenerator()
            invoice_generator.generate_invoice(order)
            logger.info(f"Invoice generated for order {order.order_number}")
        except Exception as e:
            logger.error(f"Failed to generate invoice: {str(e)}")
            # Don't fail the payment if invoice generation fails

        # Clear cart only after successful payment verification
        try:
            cart = Cart.objects.get(customer=request.user)
            cart.items.all().delete()
            logger.info(f"Cart cleared for customer {request.user.username} after payment")
        except Cart.DoesNotExist:
            pass  # Cart might already be cleared

        return JsonResponse({
            'success': True,
            'message': f'Payment successful! Order {order.order_number} confirmed.',
            'redirect_url': reverse('orders:order_detail', kwargs={'order_number': order.order_number})
        })

    except order.DoesNotExist:
        logger.warning(f"Order not found for payment verification")
        return JsonResponse({
            'success': False,
            'error': 'Order not found'
        }, status=404)

    except Exception as e:
        logger.error(f"Error verifying payment: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred during payment verification'
        }, status=500)


@login_required
def payment_success(request, order_number):
    """
    Payment success page (after verification via JavaScript).
    Redirects to order detail for confirmation.
    """
    order = get_object_or_404(Order, order_number=order_number, customer=request.user)
    
    if order.payment_status == 'PAID':
        messages.success(request, f'Payment successful! Your order {order.order_number} has been confirmed.')
        return redirect('orders:order_detail', order_number=order.order_number)
    else:
        messages.warning(request, 'Payment status is pending verification.')
        return redirect('orders:order_detail', order_number=order.order_number)


@login_required
def payment_failure(request, order_number):
    """
    Payment failure page.
    Shows error message and allows user to retry.
    """
    order = get_object_or_404(Order, order_number=order_number, customer=request.user)
    
    error_message = request.GET.get('error', 'Payment failed. Please try again.')
    messages.error(request, error_message)
    
    return redirect('orders:order_detail', order_number=order.order_number)


@login_required
def download_invoice(request, order_number):
    """
    Download invoice PDF for an order.
    
    Only allows user to download their own invoices.
    Tracks download count for analytics.
    """
    try:
        order = get_object_or_404(Order, order_number=order_number, customer=request.user)

        # Check if order is paid
        if order.payment_status != 'PAID':
            messages.error(request, 'Invoice is only available for paid orders.')
            return redirect('orders:order_detail', order_number=order.order_number)

        # Get or generate invoice
        invoice, created = Invoice.objects.get_or_create(order=order)

        if not invoice.pdf_file:
            # Generate invoice if not already generated
            invoice_generator = InvoiceGenerator()
            invoice_generator.generate_invoice(order)
            # Refresh from database
            invoice.refresh_from_db()

        # Increment download count
        invoice.increment_download_count()

        # Return PDF file
        if invoice.pdf_file:
            response = FileResponse(
                invoice.pdf_file.open('rb'),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="Invoice-{invoice.invoice_number}.pdf"'
            return response
        else:
            messages.error(request, 'Invoice file not found.')
            return redirect('orders:order_detail', order_number=order.order_number)

    except Exception as e:
        logger.error(f"Error downloading invoice: {str(e)}")
        messages.error(request, 'Failed to download invoice. Please try again.')
        return redirect('orders:order_detail', order_number=order.order_number)
