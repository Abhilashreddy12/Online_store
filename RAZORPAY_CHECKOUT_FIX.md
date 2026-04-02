# Razorpay Checkout Flow - Critical Fixes

## Issues Fixed

### Issue 1: Raw JSON Displaying in Browser Instead of Payment UI ❌ → ✅

**Root Cause:**
- Frontend form was doing a traditional HTTP POST submission
- Backend returned JSON response
- Browser tried to render JSON as a page instead of being captured by JavaScript

**Solution:**
- Changed form submission to **AJAX with `X-Requested-With` header**
- JavaScript now captures the JSON response and processes it
- Razorpay modal opens in a modal dialog (no page navigation)
- User never sees raw JSON

**Changes Made:**
1. `templates/orders/checkout.html` - Updated `createAndProcessRazorpayOrder()` to:
   - Send `X-Requested-With: XMLHttpRequest` header
   - Wait for JSON response with proper error handling
   - Check Content-Type header before parsing JSON
   - Pass order IDs to Razorpay modal

2. `orders/views.py` - Added explicit JSON response headers:
   ```python
   response = JsonResponse({...})
   response['Content-Type'] = 'application/json'
   return response
   ```

---

### Issue 2: Order Placed Without Payment (Critical Bug) ❌ → ✅

**Root Cause:**
- Order was created immediately in `place_order()` view
- Cart was cleared immediately after order creation
- No payment verification before marking order as complete
- Users could refresh/close and still have their order confirmed without paying

**Solution:**
- **Separated DB order creation from payment confirmation**
- Order created with `status=PENDING, payment_status=PENDING`
- Cart is **NOT cleared** until payment is verified
- On successful payment verification: `status=PROCESSING, payment_status=PAID`
- On payment failure: Order remains `PENDING`, user can retry or abandon

**Payment Flow Now:**
```
1. User selects shipping address & payment method
2. Click "Place Order"
   ↓
3. Backend creates Order (PENDING, PENDING) ← Cart NOT cleared
   ↓
4. Razorpay modal opens (still in-page, no redirect)
   ↓
5. User completes payment in modal
   ↓
6. Razorpay sends success callback to frontend
   ↓
7. Frontend verifies signature on BACKEND
   ↓
8. Backend verifies HMAC SHA256 signature
   ├─ If valid → Order (PROCESSING, PAID), clear cart, generate invoice ✓
   └─ If invalid → Order remains PENDING, cart preserved ✗
   ↓
9. Frontend redirected to Order Detail page
```

**Changes Made:**

1. **orders/views.py - place_order()**:
   ```python
   # For RAZORPAY: DON'T clear cart yet
   if payment_method == 'RAZORPAY':
       return JsonResponse({'success': True, 'order_id': order.id, ...})
   
   # For COD: Clear cart immediately (no payment needed)
   else:
       cart.items.all().delete()
   ```

2. **orders/payment_views.py - verify_razorpay_payment()**:
   ```python
   # Only after signature verification succeeds:
   cart = Cart.objects.get(customer=request.user)
   cart.items.all().delete()  # Clear only after payment confirmed
   ```

---

## Security Improvements ✅

### 1. **No Raw JSON Rendering**
- AJAX prevents browser from rendering JSON as page
- Users see Razorpay UI only

### 2. **HMAC SHA256 Signature Verification** (Backend Only)
```python
# Backend NEVER trusts frontend payment claims
razorpay_service.verify_payment_signature(
    razorpay_order_id,
    razorpay_payment_id, 
    razorpay_signature  # Verified using SECRET KEY (not in frontend)
)
```

**Why this matters:**
- Frontend signature is just a payload
- Secret key only on backend
- Even if attacker tempers with frontend response, backend verification fails
- Uses `hmac.compare_digest()` for timing-attack safety

### 3. **Cart Protection**
- Cart only cleared after payment is VERIFIED
- If payment fails/invalid signature → Cart preserved
- User can retry without losing items

### 4. **Idempotency & Duplicate Prevention**
- Each payment attempt has unique `idempotency_key`
- Prevents duplicate charges if user refreshes mid-payment
- Razorpay service layer validates before processing

---

## API Endpoints Overview

### 1. **POST /orders/place-order/**
Creates order skeleton with payment method selection.

**Request:**
```
Form Data:
- shipping_address (required)
- payment_method: "RAZORPAY" or "COD"
- coupon_code (optional)
- X-Requested-With: XMLHttpRequest (for AJAX)
```

**Response (Razorpay):**
```json
{
  "success": true,
  "order_id": 17,
  "order_number": "ORD-20260402-C7ADEC58"
}
```

**Response (COD):**
```
HTTP 302 Redirect → Order Detail Page
```

**Order State After:**
- `status` = PENDING
- `payment_status` = PENDING  
- `payment_method` = "RAZORPAY" or "COD"
- Cart = **Not cleared** (Razorpay) / **Cleared** (COD)

---

### 2. **POST /orders/api/create-razorpay-order/**
Creates Razorpay-side order and returns payment parameters.

**Request:**
```json
POST Data:
order_id: 17
```

**Response:**
```json
{
  "success": true,
  "razorpay_order_id": "order_ABC123XYZ",
  "key_id": "rzp_live_1234567890",
  "amount": 1999500,  // in paise (₹19,995)
  "currency": "INR",
  "order_details": {
    "order_number": "ORD-20260402-C7ADEC58",
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "total_amount": 19995.00
  }
}
```

**Security Note:**
- `key_id` is **public key** (safe to send to frontend)
- Secret key is **NEVER included** in response

---

### 3. **POST /orders/api/verify-razorpay-payment/**
Verifies HMAC signature and confirms payment.

**Request:**
```json
{
  "razorpay_payment_id": "pay_1A2B3C4D5E6F",
  "razorpay_order_id": "order_ABC123XYZ",
  "razorpay_signature": "9ef4dffbfd84f1318f6739a3ce19f9d85851857ae648f114332d8401e0949a3d",
  "order_id": 17
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Payment successful! Order confirmed.",
  "redirect_url": "/orders/order/ORD-20260402-C7ADEC58/"
}
```

**Response (Failure):**
```json
{
  "success": false,
  "error": "Payment verification failed. Please contact support."
}
```

**Backend Actions on Success:**
1. Verify HMAC SHA256 signature ✓
2. Update order: `status=PROCESSING, payment_status=PAID`
3. Store payment details in `RazorpayPayment` table
4. **Clear cart** (only now!)
5. Generate PDF invoice
6. Return redirect URL

**Backend Actions on Failure:**
1. Update `RazorpayPayment.payment_status = FAILED`
2. Order remains PENDING
3. Cart remains intact
4. Return error message
5. User can retry

---

## Frontend Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│ Checkout Page                                           │
│ - Select Shipping Address                               │
│ - Select Payment Method (COD / Razorpay)               │
│ - Click "Place Order"                                   │
└────────────────┬──────────────────────────────────────┘
                 │
                 ├─── COD Selected ───→ Form Submit → Redirect
                 │
                 └─── RAZORPAY Selected ──┐
                                           ▼
                      ┌──────────────────────────────┐
                      │ createAndProcessRazorpay()   │
                      │ (AJAX - NO PAGE RELOAD)      │
                      └──────┬───────────────────────┘
                             │
                             ▼ POST /orders/place-order/
                      ┌──────────────────────────────┐
                      │ Backend creates Order        │
                      │ status=PENDING               │
                      │ payment_status=PENDING       │
                      │ Cart NOT cleared             │
                      └──────┬───────────────────────┘
                             │
                             ▼ JSON Response
                      ┌──────────────────────────────┐
                      │ order_id, order_number       │
                      └──────┬───────────────────────┘
                             │
                             ▼ POST /orders/api/create-razorpay-order/
                      ┌──────────────────────────────┐
                      │ Backend creates Razorpay     │
                      │ order via Razorpay API       │
                      └──────┬───────────────────────┘
                             │
                             ▼ JSON Response
                      ┌──────────────────────────────┐
                      │ razorpay_order_id, key_id,  │
                      │ amount, currency             │
                      └──────┬───────────────────────┘
                             │
                             ▼ openRazorpayCheckout()
                      ┌──────────────────────────────┐
                      │ RAZORPAY MODAL OPENS         │
                      │ User sees payment methods:   │
                      │ - Cards (Debit/Credit)      │
                      │ - UPI (GPay, PhonePe, etc)  │
                      │ - Wallets, Net Banking       │
                      └──────┬───────────────────────┘
                             │
                             ▼ User completes payment
                      ┌──────────────────────────────┐
                      │ Razorpay sends success       │
                      │ callback with signature      │
                      └──────┬───────────────────────┘
                             │
                             ▼ verifyPayment()
                      ┌──────────────────────────────┐
                      │ POST /orders/verify-payment/ │
                      │ Send: payment_id, order_id,  │
                      │       signature              │
                      └──────┬───────────────────────┘
                             │
                             ▼ Backend verifies signature
                      ┌────────────────────────────────────┐
                      │ HMAC SHA256 verification          │
                      │ (Uses SECRET KEY - never in JS)   │
                      └──────┬─────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
            ✓ Valid │                 │ ✗ Invalid
                    ▼                 ▼
            ┌────────────────┐  ┌──────────────┐
            │ Order PAID     │  │ Order PENDING │
            │ Cart cleared   │  │ Cart intact   │
            │ Invoice gen    │  │ Show error    │
            │ Redirect       │  │ Allow retry   │
            └────────────────┘  └──────────────┘
```

---

## Testing Checklist

### ✅ Happy Path (Success Flow)
- [ ] Select shipping address
- [ ] Select "Razorpay Secure Payment"
- [ ] Click "Place Order"
- [ ] Razorpay modal appears (NO JSON rendering)
- [ ] Complete payment with test card (Razorpay test credentials)
- [ ] Modal closes
- [ ] "Verifying Payment..." shows on button
- [ ] Redirects to Order Detail page
- [ ] Order shows `status=PROCESSING, payment_status=PAID`
- [ ] Cart is empty
- [ ] Invoice PDF is generated and available for download

### ✅ Error Path (Signature Failure)
- [ ] Verify endpoint is tested with invalid signature
- [ ] Error message shows "Payment verification failed"
- [ ] Order remains `status=PENDING`
- [ ] Cart is NOT cleared
- [ ] User can retry payment
- [ ] Logs show "Signature verification FAILED"

### ✅ User Cancellation
- [ ] User opens modal but doesn't complete payment
- [ ] Click X to close modal
- [ ] No error shown, button resets
- [ ] Order remains PENDING
- [ ] Cart unchanged
- [ ] User can try again

### ✅ COD Flow (Not Impacted but Verify)
- [ ] Select "Cash on Delivery"
- [ ] Click "Place Order"
- [ ] Page redirects immediately (not AJAX)
- [ ] Order confirmed with status=PENDING
- [ ] Cart cleared

---

## Deployment Checklist

Before deploying to production:

1. **Environment Variables Set** ✓
   ```
   RAZORPAY_KEY_ID=rzp_live_xxxxx (production key)
   RAZORPAY_KEY_SECRET=xxxx (production secret)
   ```

2. **Database Migrations Applied** ✓
   ```bash
   python manage.py migrate orders
   ```

3. **Static Files Collected** ✓
   ```bash
   python manage.py collectstatic --noinput
   ```

4. **Tests Passed** ✓
   - Payment verification test
   - Signature validation test
   - Cart clearing logic test

5. **Logs Configured** ✓
   - Payment errors logged
   - Signature verification logged
   - Invoice generation logged

6. **HTTPS Enabled** ✓
   - All payment endpoints over HTTPS
   - Razorpay script loaded over HTTPS
   - CSRF protection enabled

---

## Common Errors & Solutions

### ❌ "Unexpected token '<', '<!Doctype html' is not valid JSON"
**Root Cause:** Form was submitting normally instead of AJAX
**Status:** FIXED ✓ - Now using proper AJAX with headers

### ❌ "Order placed without payment"
**Root Cause:** Cart cleared immediately, before payment verification
**Status:** FIXED ✓ - Cart only cleared after payment verified

### ❌ "Raw JSON showing in browser"
**Root Cause:** No AJAX headers, browser treating response as HTML
**Status:** FIXED ✓ - Using `X-Requested-With: XMLHttpRequest`

### ❌ "Signature verification failed"
**Root Cause:** Attacker tampered with frontend response
**Status:** EXPECTED ✓ - Backend rejects, order stays pending

---

## Security Summary

| Component | Security Measure | Status |
|-----------|------------------|--------|
| Payment | HMAC SHA256 signature verification (backend only) | ✅ Implemented |
| Secret Key | Never exposed to frontend | ✅ Implemented |
| Cart | Only cleared after verified payment | ✅ Implemented |
| Order | Only marked PAID after verification | ✅ Implemented |
| CSRF | Protected by Django middleware | ✅ Enabled |
| HTTPS | Required for all payment endpoints | ✅ Required |
| Idempotency | Duplicate prevention via unique keys | ✅ Implemented |
| Logging | All payment events logged | ✅ Implemented |

---

## Questions?

For issues or questions about payment flow:
1. Check server logs: `/shopping_store.log`
2. Check database payment records: `orders.RazorpayPayment`
3. Verify Razorpay dashboard shows payment attempt
4. Check CORS/HTTPS configuration if modal doesn't open

