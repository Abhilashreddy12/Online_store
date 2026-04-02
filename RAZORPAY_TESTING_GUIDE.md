# 🧪 Razorpay Integration - Testing Guide

## Pre-Testing Checklist
- [ ] `.env` file has RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET
- [ ] Migrations applied: `python manage.py migrate`
- [ ] Django runserver started: `python manage.py runserver`
- [ ] Browser ready (Chrome/Firefox recommended)

---

## Test Case 1: Successful Payment ✅

### Setup
1. Create test user account
2. Add product to cart
3. Navigate to checkout

### Test Steps
1. **Select Razorpay Payment**
   - [ ] Check "Razorpay Secure Payment" option appears
   - [ ] Click to select (should highlight)

2. **Create Order**
   - [ ] Click "Place Order" button
   - [ ] Razorpay checkout modal should open
   - [ ] Modal should show order amount and currency

3. **Enter Payment Details**
   - Card: `4111 1111 1111 1111`
   - Expiry: `12/25` (or any future date)
   - Name: Any name
   - CVV: `123`
   - [ ] Click "Pay" or submit

4. **Verify Payment**
   - [ ] OTP field appears (enter `111111`)
   - [ ] Payment processes (may take 2-3 seconds)
   - [ ] Razorpay closes
   - [ ] Page redirects to order detail
   - [ ] Success message shows

5. **Verify Backend Updates**
   - [ ] Order status shows as "PAID"
   - [ ] Payment status shows as "Paid"
   - [ ] Transaction ID is populated
   - [ ] Invoice is generated and available for download

### Expected Results
```
✓ Order created successfully
✓ Razorpay order_id generated
✓ Payment processed
✓ Signature verified (no error logs)
✓ Order status → PAID
✓ Invoice generated
✓ Download invoice link available
```

---

## Test Case 2: Failed Payment ❌

### Test Steps
1. Navigate to checkout
2. Select Razorpay payment
3. Click "Place Order"
4. Use invalid card: `4000 0000 0000 0002` (declined card)
5. Complete checkout flow

### Expected Results
```
✓ Razorpay shows payment failed
✓ User redirected to order detail
✓ Error message displays
✓ Order status → PENDING
✓ Payment status → FAILED
✓ RazorpayPayment record shows error message
```

---

## Test Case 3: Invalid Signature Detection 🔐

### Backend Test (Manual)
```python
from orders.razorpay_service import RazorpayPaymentService

service = RazorpayPaymentService()

# Test with invalid signature
is_valid = service.verify_payment_signature(
    'order_1a2b3c4d',
    'pay_1a2b3c4d',
    'invalid_signature_12345'
)
print(is_valid)  # Should print: False
```

### Expected Results
```
✓ Returns False for invalid signature
✓ Logs warning: "Signature verification FAILED"
✓ Creates error entry in RazorpayPayment
✓ Order status remains PENDING
```

---

## Test Case 4: Duplicate Payment Prevention 🛡️

### Test Steps
1. Create an order and process payment successfully
2. Try to create another payment for same order

### Expected Results
```
✓ Second payment creation fails
✓ Error message: "Payment already initiated"
✓ No duplicate RazorpayPayment records created
✓ Idempotency key prevents duplicate processing
```

---

## Test Case 5: Invoice Generation 📄

### Test Steps
1. Complete successful payment (Test Case 1)
2. Go to order detail page
3. Look for invoice download button

### Expected Results
```
✓ Invoice link available on order detail
✓ Click download → PDF file downloads
✓ Invoice filename: "Invoice-{invoice_number}.pdf"
✓ PDF contains:
  - Order number
  - Invoice number and date
  - Customer details
  - Shipping address
  - Order items with prices
  - Tax and total amounts
  - Payment status
  
✓ Invoice record created in database
✓ Download count increments
```

---

## Test Case 6: User Authorization Check 👤

### Test Steps
1. User A completes a payment
2. User B tries to access User A's payment endpoint

### Test Code
```python
# As User B, try to verify User A's payment:
POST /orders/api/verify-razorpay-payment/
{
    "razorpay_payment_id": "pay_from_user_a",
    "razorpay_order_id": "order_from_user_a",
    "razorpay_signature": "sig_from_user_a",
    "order_id": "order_id_belonging_to_user_a"
}
```

### Expected Results
```
✓ Request returns 404 (order not found for this user)
✓ No order update occurs
✓ Error message in response
✓ No payment record created
```

---

## Test Case 7: CSRF Protection ✅

### Test Steps
1. Make POST request without CSRF token
2. Make POST request with valid CSRF token

### Test Code (Manual)
```python
# Without CSRF token - should fail
import requests
response = requests.post(
    'http://localhost:8000/orders/api/create-razorpay-order/',
    data={'order_id': 123}
)
print(response.status_code)  # Should be 403

# With CSRF token - should work (if authenticated)
```

### Expected Results
```
✓ Without CSRF token → 403 Forbidden
✓ With valid CSRF token → 200 OK
$  CSRF protection working correctly
```

---

## Test Case 8: Mobile Responsiveness 📱

### Test Steps
1. Open checkout on mobile device
2. Select Razorpay payment
3. Complete payment flow

### Expected Results
```
✓ Layout responsive on mobile
✓ Razorpay checkout modal works on mobile
✓ Payment fields readable and usable
✓ Tab focus works correctly
✓ Touch interactions responsive
```

---

## Test Case 9: Error Handling 🚨

### Test Steps
1. Disconnect internet before final payment
2. Try to process payment
3. Reconnect and retry

### Expected Results
```
✓ Network error handled gracefully
✓ User sees error message
✓ No corrupted order created
✓ Can retry payment
✓ No duplicate charges
```

---

## Test Case 10: Payment Status Transitions 🔄

### Verification Steps
1. Create order → status: PENDING (not yet paid)
2. Start payment → status: PENDING (payment in progress)
3. Complete payment → status: PAID (payment successful)
4. Verify invoice → status shows PAID

### Expected Results
```
✓ Order starts as PENDING
✓ Payment status updates correctly
✓ Final status: PAID
✓ paid_at timestamp set
✓ Order automatically moves to PROCESSING status
```

---

## Database Verification Tests 🗄️

### Check RazorpayPayment Table
```python
from orders.models import RazorpayPayment

# After successful payment
payment = RazorpayPayment.objects.latest('id')

print(f"Order ID: {payment.order.id}")
print(f"Razorpay Order ID: {payment.razorpay_order_id}")
print(f"Payment ID: {payment.razorpay_payment_id}")
print(f"Signature Verified: {payment.signature_verified}")
print(f"Payment Status: {payment.payment_status}")
print(f"Amount Paid: {payment.amount_paid}")
```

### Expected Results
```
✓ All fields populated
✓ signature_verified = True (for successful payment)
✓ payment_status = CAPTURED
✓ amount_paid = order.total_amount
✓ idempotency_key is unique
```

### Check Invoice Table
```python
from orders.models import Invoice

# After successful payment
invoice = Invoice.objects.latest('id')

print(f"Invoice Number: {invoice.invoice_number}")
print(f"Order: {invoice.order.order_number}")
print(f"PDF File: {invoice.pdf_file}")
print(f"Downloaded Count: {invoice.downloaded_count}")
```

### Expected Results
```
✓ Invoice created
✓ Unique invoice_number
✓ PDF file stored
✓ Generated_at timestamp set
```

---

## API Response Validation Tests 🔍

### Test /api/create-razorpay-order/ Response
```python
import json

response_json = {
    "success": True,
    "razorpay_order_id": "order_1a2b3c4d5e6f",
    "key_id": "rzp_test_xxxxx",          # Public key - OK
    "key_secret": None,                  # Should NOT be here
    "amount": 115000,                    # In paise
    "currency": "INR",
    "order_details": {
        "order_number": "ORD-20260402-ABC123",
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "total_amount": 1150.00
    }
}

# Verify secret key NOT in response
assert "key_secret" not in str(response_json)
assert "secret" not in str(response_json).lower()
```

### Expected Results
```
✓ Response contains all required fields
✓ Secret key NOT included
✓ Amount in paise (not rupees)
✓ Order summary included
✓ Public key included
```

### Test /api/verify-razorpay-payment/ Response
```python
success_response = {
    "success": True,
    "message": "Payment successful! Order confirmed.",
    "redirect_url": "/orders/order/ORD-20260402-ABC123/"
}

failure_response = {
    "success": False,
    "error": "Payment verification failed"
}

# Verify no sensitive data in error messages
assert "secret" not in str(failure_response).lower()
```

### Expected Results
```
✓ Success response has redirect_url
✓ Error messages don't expose sensitive data
✓ No credentials in response
✓ Proper HTTP status codes (200, 400, 404, 500)
```

---

## Performance Tests ⚡

### Test1: Order Creation Speed
```
Expected: < 2 seconds
- Database insert
- UUID generation
- Razorpay API call
```

### Test 2: Signature Verification Speed
```
Expected: < 100ms
- HMAC-SHA256 computation
- Database lookup
```

### Test 3: Invoice Generation Speed
```
Expected: < 3 seconds
- PDF creation
- File storage
- Database save
```

---

## Security Audit Checklist 🔒

- [ ] Razorpay secret key NOT visible in any logs
- [ ] Frontend console shows NO payment credentials
- [ ] Response headers secure (no sensitive data)
- [ ] Database passwords not in error messages
- [ ] Users can't access other users' payments
- [ ] CSRF token required for state-changing operations
- [ ] SQL injection attempts fail safely
- [ ] XSS attempts fail safely
- [ ] Signature verification fails for tampered data

---

## Troubleshooting During Tests

### Issue: Razorpay Modal Not Opening
```
Solution:
1. Check JavaScript console for errors
2. Verify Razorpay script loaded (F12 → Network)
3. Check browser console for payment_views errors
4. Verify order_id returned from backend
```

### Issue: Signature Verification Failing
```
Solution:
1. Check RAZORPAY_KEY_SECRET in .env
2. Look at logs: "Signature verification FAILED"
3. Compare expected vs actual signature in logs
4. Ensure order_id and payment_id are correct
```

### Issue: Invoice Not Generating
```
Solution:
1. Check media/ directory exists and writable
2. Check ReportLab installed: pip list | grep reportlab
3. Look at Django logs for errors
4. Check file permissions on media/ directory
```

### Issue: 404 When Accessing Payment Endpoint
```
Solution:
1. Verify order exists in database
2. Check order belongs to logged-in user
3. Verify order_id is correct
4. Check URLs are updated: python manage.py check
```

---

## Test Results Template

```
Test Suite: Razorpay Integration
Date: ________________
Tester: ________________

Test Case 1 - Successful Payment: [ ] PASS [ ] FAIL
Test Case 2 - Failed Payment: [ ] PASS [ ] FAIL
Test Case 3 - Invalid Signature: [ ] PASS [ ] FAIL
Test Case 4 - Duplicate Prevention: [ ] PASS [ ] FAIL
Test Case 5 - Invoice Generation: [ ] PASS [ ] FAIL
Test Case 6 - User Authorization: [ ] PASS [ ] FAIL
Test Case 7 - CSRF Protection: [ ] PASS [ ] FAIL
Test Case 8 - Mobile Responsive: [ ] PASS [ ] FAIL
Test Case 9 - Error Handling: [ ] PASS [ ] FAIL
Test Case 10 - Status Transitions: [ ] PASS [ ] FAIL

Overall Status: ________________
Issues Found: 
- (List any issues)

Sign Off: _________________
```

---

## Final Sign-Off

When all tests pass:
✅ Integration is production-ready
✅ Security measures verified
✅ User flow tested
✅ Error handling confirmed
✅ Authorization checks working
✅ Invoice generation functional
✅ Ready for Render deployment

---

**Happy Testing!** 🎉
