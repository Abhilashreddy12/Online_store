# Razorpay Integration - Complete Setup Guide

## Overview
This guide covers the complete Razorpay payment integration for your online store. The integration is production-ready with security best practices implemented.

## Architecture

### Components Implemented

1. **RazorpayPayment Model** (`orders/models.py`)
   - Tracks all Razorpay transactions
   - Stores order_id, payment_id, and signature
   - Records signature verification status
   - Prevents duplicate payments with idempotency keys

2. **RazorpayPaymentService** (`orders/razorpay_service.py`)
   - Pure service layer for all Razorpay API interactions
   - Handles order creation, signature verification, payment capture
   - HMAC SHA256 signature verification for security
   - Proper error handling and logging

3. **Payment API Endpoints** (`orders/payment_views.py`)
   - `POST /api/create-razorpay-order/` - Create Razorpay order
   - `POST /api/verify-razorpay-payment/` - Verify payment signature
   - Payment success/failure handlers
   - Invoice download endpoint

4. **Invoice Generation** (`orders/invoice_service.py`)
   - Auto-generates professional PDF invoices
   - Uses ReportLab for PDF generation
   - Supports cloud storage (Cloudinary)
   - Invoice download tracking

5. **Frontend Integration** (`templates/orders/checkout.html`)
   - Razorpay Checkout.js integration
   - Secure frontend-backend communication
   - Payment status handling

## Security Considerations

### 1. Secret Key Management
✅ **NEVER expose Razorpay secret key in frontend**
- Secret key stored in `RAZORPAY_KEY_SECRET` environment variable only
- Only public key (`RAZORPAY_KEY_ID`) sent to frontend
- All signature verification happens on backend

### 2. Signature Verification
✅ **HMAC SHA256 verification prevents tampering**
```python
# Backend verification (secure)
expected_signature = hmac.new(
    secret_key.encode(),
    f"{order_id}|{payment_id}".encode(),
    hashlib.sha256
).hexdigest()

# Constant-time comparison prevents timing attacks
is_valid = hmac.compare_digest(expected_signature, provided_signature)
```

### 3. Idempotency
✅ **Prevents duplicate payment processing**
- Unique `idempotency_key` generated for each payment attempt
- Database constraint prevents duplicate processing

### 4. Authorization Checks
✅ **@login_required on all endpoints**
✅ **User can only verify their own payments**
```python
order = get_object_or_404(Order, id=order_id, customer=request.user)
```

### 5. CSRF Protection
✅ **Django CSRF middleware protects all POST endpoints**
- CSRF token required in form submissions
- JSON endpoints require X-CSRFToken header

## Environment Variables Required

Add to your `.env` file:

```
# Razorpay Credentials (from https://dashboard.razorpay.com/app/keys)
RAZORPAY_KEY_ID=rzp_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxx
```

## Database Schema

### RazorpayPayment Model
```
- order (OneToOne to Order)
- razorpay_order_id (unique, indexed)
- razorpay_payment_id (nullable)
- razorpay_signature (nullable)
- amount_paid (Decimal)
- currency (CharField, default='INR')
- payment_status (PENDING, AUTHORIZED, CAPTURED, FAILED, REFUNDED)
- signature_verified (Boolean, indexed)
- idempotency_key (unique)
- error_message (TextField)
- error_code (CharField)
- created_at / updated_at (timestamps)
- payment_captured_at (DateTime)
```

### Invoice Model
```
- order (OneToOne to Order)
- invoice_number (unique)
- invoice_date (DateField)
- pdf_file (FileField)
- pdf_url (URLField, for cloud storage)
- downloaded_count (PositiveIntegerField)
- generated_at / updated_at (timestamps)
```

## API Endpoints

### 1. Create Razorpay Order
**POST** `/orders/api/create-razorpay-order/`

**Request (Form Data):**
```
order_id: <order_id>
```

**Response (JSON):**
```json
{
  "success": true,
  "razorpay_order_id": "order_1a2b3c4d5e6f",
  "key_id": "rzp_xxxxxxxxxxxxx",  // Public key only
  "amount": 115000,  // Amount in paise
  "currency": "INR",
  "order_details": {
    "order_number": "ORD-20260401-ABC123",
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "total_amount": 1150.00
  }
}
```

### 2. Verify Payment
**POST** `/orders/api/verify-razorpay-payment/`

**Request (JSON):**
```json
{
  "razorpay_payment_id": "pay_1a2b3c4d5e6f",
  "razorpay_order_id": "order_1a2b3c4d5e6f",
  "razorpay_signature": "signature_hash",
  "order_id": 123
}
```

**Response (JSON):**
```json
{
  "success": true,
  "message": "Payment successful! Order confirmed.",
  "redirect_url": "/orders/order/ORD-20260401-ABC123/"
}
```

### 3. Download Invoice
**GET** `/orders/order/<order_number>/download-invoice/`

Returns PDF file with invoice.

## Payment Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    PAYMENT FLOW DIAGRAM                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [User selects payment method]                                  │
│           ↓                                                      │
│  [Frontend: POST /place-order/] ────→ [Backend: Create Order]  │
│           ↓                                                      │
│  [Frontend: POST /create-razorpay-order/]                       │
│           ↓ (returns order_id + public key)                     │
│  [Backend: Create Razorpay order] ────→ [Razorpay API]         │
│           ↓                                                      │
│  [Frontend: Open Razorpay Checkout Modal]                       │
│           ↓                                                      │
│  [User: Enter payment details] ────→ [Razorpay Processing]     │
│           ↓                                                      │
│  [Razorpay: Returns payment_id + signature]                     │
│           ↓                                                      │
│  [Frontend: POST /verify-razorpay-payment/]                     │
│  (with payment_id, order_id, signature)                         │
│           ↓                                                      │
│  [Backend: Verify HMAC SHA256 signature] ✅ CRITICAL            │
│           ↓                                                      │
│  [If valid: Update order status → PAID]                         │
│  [Generate invoice PDF]                                         │
│  [Return success + redirect URL]                                │
│           ↓                                                      │
│  [If invalid: Payment marked FAILED]                            │
│  [Return error message]                                         │
│           ↓                                                      │
│  [Frontend: Redirect to order detail / show success]            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Testing Payment Locally

### 1. Using Razorpay Test Credentials
Get test credentials from: https://dashboard.razorpay.com/app/test-mode/keys

Add to `.env`:
```
RAZORPAY_KEY_ID=rzp_test_xxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxx
```

### 2. Test Payment Details
**Use these in Razorpay Checkout:**
- Card: 4111111111111111 (Visa)
- Expiry: Any future date
- CVV: Any 3 digits
- OTP: 111111

### 3. Run Tests
```bash
# Run all payment tests
python manage.py test orders.test_razorpay

# Run specific test
python manage.py test orders.test_razorpay.RazorpayPaymentAPITestCase.test_create_razorpay_order_authenticated
```

## Production Deployment Checklist

### Environment Variables
- [ ] Set `RAZORPAY_KEY_ID` in Render dashboard
- [ ] Set `RAZORPAY_KEY_SECRET` in Render dashboard
- [ ] Set `DEBUG=False` in production
- [ ] Set `SECURE_SSL_REDIRECT=True`
- [ ] Set `SESSION_COOKIE_SECURE=True`
- [ ] Set `CSRF_COOKIE_SECURE=True`

### Security Settings
- [ ] X_FRAME_OPTIONS set to 'SAMEORIGIN' (allow admin popups)
- [ ] HTTPS enabled on domain
- [ ] Database backed up before deploying
- [ ] Monitor error logs for payment failures

### Testing
- [ ] Test successful payment flow
- [ ] Test failed payment handling
- [ ] Test invoice download
- [ ] Test payment signature verification
- [ ] Test duplicate payment prevention

## Troubleshooting

### Error: "Signature verification failed"
- Verify RAZORPAY_KEY_SECRET is correct
- Check that signature string format is correct: `{order_id}|{payment_id}`
- Ensure backend receives exact signature from Razorpay

### Error: "Order not found"
- Verify order was created successfully
- Check user authorization (order must belong to logged-in user)
- View Django admin to debug order creation

### Error: "Payment method not RAZORPAY"
- Check that payment_method form field is set to 'RAZORPAY'
- Verify frontend is posting correct value

### Invoice not generating
- Check file permissions on media/ directory
- Verify CLOUDINARY_URL if using cloud storage
- Check Django logs for ReportLab errors

## Refunds

To process refunds (admin operation):

```python
from orders.razorpay_service import RazorpayPaymentService

service = RazorpayPaymentService()

# Full refund
service.refund_payment(payment_id)

# Partial refund (amount in paise)
service.refund_payment(payment_id, amount=50000)
```

## WebHook Integration (Optional)

For receiving payment status updates via Razorpay webhooks:

```python
# In orders/views.py
@csrf_exempt
@require_http_methods(["POST"])
def razorpay_webhook(request):
    """Handle Razorpay webhook events"""
    payload = json.loads(request.body)
    event = payload['event']
    
    if event == 'payment.authorized':
        # Handle authorized payment
        pass
    elif event == 'payment.failed':
        # Handle failed payment
        pass
    elif event == 'payment.captured':
        # Handle captured payment
        pass
```

## Support & Resources

- Razorpay Documentation: https://razorpay.com/docs/
- Razorpay Dashboard: https://dashboard.razorpay.com/
- Razorpay API Reference: https://razorpay.com/docs/api/orders/
- ReportLab PDF Guide: https://docs.reportlab.com/

## Maintenance & Monitoring

### Monitor These Metrics
- Payment success rate
- Average payment processing time
- Failed signature verifications (security indicator)
- Invoice generation failures
- Duplicate payment attempts (should be 0)

### Regular Tasks
- Review RazorpayPayment records for failed payments
- Check Invoice.downloaded_count for usage patterns
- Monitor error logs for payment-related issues
- Verify Razorpay credentials are still valid

---

**Integration Completed Successfully!** ✅

All components are production-ready with comprehensive security measures implemented.
