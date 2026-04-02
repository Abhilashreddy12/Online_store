# Testing Razorpay Checkout Flow - Step by Step

## Prerequisites
- Django dev server running: `python manage.py runserver`
- Razorpay test credentials configured in `.env`
- Test user account created and logged in
- Cart has items

---

## Test Flow 1: Successful Payment ✅

### Step 1: Navigate to Checkout
```
1. Go to: http://127.0.0.1:8000/orders/checkout/
2. You should see:
   - One or more shipping addresses (if none, add one first)
   - Payment method options (COD, Razorpay, Card)
   - Order summary on the right
```

**Verify:**
- [ ] Shipping addresses load correctly
- [ ] Payment methods visible
- [ ] Order total displayed

---

### Step 2: Select Shipping Address & Payment Method
```
1. Click on a shipping address (radio button)
   → It should highlight with blue border
   
2. Click on "Razorpay Secure Payment" 
   → It should highlight with blue border
   → Shows "Credit/Debit Card, UPI, Digital Wallets"
   
3. Verify "Place Order" button is enabled
```

**Verify:**
- [ ] Address selection works
- [ ] Payment method selection works
- [ ] Button is active/clickable

---

### Step 3: Click "Place Order"
```
1. Click the "Place Order" button
2. Expected: Button changes to "Processing..."
3. Expected: NO page reload
4. Expected: NO JSON display
5. Expected: Within 2-3 seconds, Razorpay modal appears
```

**Check Browser Console (F12 → Console):**
```
Should see:
✓ Order created: ORD-20260402-C7ADEC58, ID: 17
✓ Razorpay order created: order_ABC123XYZ
```

**If JSON shows instead:**
- [ ] Force refresh browser: Ctrl+Shift+R
- [ ] Check file edits were saved: `grep "X-Requested-With" templates/orders/checkout.html`
- [ ] Restart Django server

---

### Step 4: Razorpay Modal Opens
```
1. Modal window appears with payment options:
   ✓ Credit/Debit Card
   ✓ UPI (Google Pay, PhonePe, etc.)
   ✓ Wallets
   ✓ Net Banking
   
2. Modal shows:
   - Order number (ORD-20260402-C7ADEC58)
   - Amount in INR
   - Online Store branding
```

**Verify:**
- [ ] Modal appears (not redirect to new page)
- [ ] Payment options visible
- [ ] Amount is correct

---

### Step 5: Complete Test Payment
```
1. Click on "Credit Card" option
2. Enter card details:
   - Card Number: 4111111111111111
   - Expiry: 12/25
   - CVV: 123
   - Cardholder Name: John Doe
   
3. Click "Pay" button
4. OTP page appears (Razorpay test OTP flow)
5. Enter OTP: 000000
6. Click "Submit"
7. Success page shows in modal (usually closes automatically)
```

**Check Browser Console During Payment:**
```
Should see:
✓ Payment success callback: {razorpay_payment_id: "pay_...", ...}
✓ Verifying Payment...
```

---

### Step 6: Backend Verifies Signature
```
1. Frontend sends signature to backend
2. Backend verifies HMAC SHA256
3. Expected: 2-3 seconds processing time
4. Button shows "Verifying Payment..."
```

**Check Server Terminal Output:**
```
Expected logs:
INFO: Payment verified and captured for order ORD-20260402-C7ADEC58
INFO: Invoice generated for order ORD-20260402-C7ADEC58
INFO: Cart cleared for customer john_doe after payment
```

---

### Step 7: Success Message & Redirect
```
1. Alert shows: "Payment successful! Your order has been confirmed. Redirecting..."
2. After 1.5 seconds, page redirects to Order Detail
3. Order shows:
   - Order number: ORD-20260402-C7ADEC58
   - Status: PROCESSING
   - Payment Status: PAID ← Important!
   - Items listed
   - Download Invoice button available
```

**Verify in Database:**
```bash
python manage.py shell
>>> from orders.models import Order, RazorpayPayment
>>> o = Order.objects.get(order_number='ORD-20260402-C7ADEC58')
>>> o.payment_status
'PAID' ← Should be PAID, not PENDING
>>> o.status
'PROCESSING'
>>> from cart.models import Cart
>>> c = Cart.objects.get(customer=o.customer)
>>> c.items.count()
0 ← Cart should be cleared
>>> rp = o.razorpay_payment
>>> rp.signature_verified
True ← Signature verified
>>> rp.payment_status
'CAPTURED'
```

**Verify Cart is Empty:**
```
1. Go to: http://127.0.0.1:8000/cart/
2. Cart should show "Your cart is empty"
3. OR click "Continue Shopping" to verify cart items gone
```

---

## Test Flow 2: Payment Cancelled by User ⚠️

### Steps:
```
1. Go to checkout
2. Select address & Razorpay
3. Click "Place Order"
4. Razorpay modal opens
5. Click X button to close modal WITHOUT completing payment
```

**Expected Behavior:**
```
✓ Modal closes
✓ Error: "User closed Razorpay modal without completing payment" in console
✓ Button resets to "Place Order"
✓ Button is NOT disabled
✓ Page stays on checkout
```

**Verify Database:**
```bash
python manage.py shell
>>> o = Order.objects.latest('created_at')
>>> o.payment_status
'PENDING' ← Still PENDING, not PAID
>>> from cart.models import Cart
>>> c = Cart.objects.get(customer=o.customer)
>>> c.items.count()
> 0 ← Cart NOT cleared, items still there
```

**Verify You Can Retry:**
```
1. Button still shows "Place Order"
2. Click it again
3. Razorpay modal opens again (can retry payment)
4. Complete payment this time
5. Should succeed normally
```

---

## Test Flow 3: Payment Fails ❌

### Steps:
```
1. Go to checkout
2. Select address & Razorpay
3. Click "Place Order"
4. Razorpay modal opens
5. Enter invalid test card: Use a declined test card
   OR interrupt the payment process

Razorpay provides declined test cards for testing failure.
Check Razorpay docs for current declined card numbers.
```

**Expected Behavior:**
```
✓ Modal shows error: "Payment failed: [error description]"
✓ Modal closes
✓ Button resets to "Place Order"
✓ No redirect happens
✓ Page stays on checkout
```

**Verify Database:**
```bash
python manage.py shell
>>> o = Order.objects.latest('created_at')
>>> o.payment_status
'PENDING' ← Still PENDING
>>> rp = o.razorpay_payment
>>> rp.payment_status
'FAILED'
>>> rp.error_message
'Payment declined' or similar
```

**Verify Cart Preserved:**
```bash
>>> from cart.models import Cart
>>> c = Cart.objects.get(customer=o.customer)
>>> c.items.count()
> 0 ← Items still in cart, can try again
```

---

## Test Flow 4: COD (Cash on Delivery) Should Still Work ✓

### Steps:
```
1. Go to: http://127.0.0.1:8000/orders/checkout/
2. Select shipping address
3. Click on "Cash on Delivery" ← NOT Razorpay
4. Click "Place Order"
```

**Expected Behavior:**
```
✓ Form submits normally (HTTP POST, not AJAX)
✓ Page redirects immediately (within 1 second)
✓ Redirects to Order Detail page
✓ SUCCESS message: "Order [number] placed successfully!"
✓ No modal appears
✓ No signature verification needed
```

**Verify Database:**
```bash
python manage.py shell
>>> o = Order.objects.latest('created_at')
>>> o.payment_method
'COD'
>>> o.payment_status
'PENDING' ← For COD, stays PENDING until paid on delivery
>>> from cart.models import Cart
>>> c = Cart.objects.get(customer=o.customer)
>>> c.items.count()
0 ← Cart should be cleared immediately for COD
```

---

## Test Flow 5: Missing Shipping Address Validation ⚠️

### Steps:
```
1. Go to: http://127.0.0.1:8000/orders/checkout/
2. DO NOT select any shipping address
3. Select "Razorpay Secure Payment"
4. Click "Place Order"
```

**Expected Behavior:**
```
✓ Alert appears: "Checkout Error: Please select a shipping address"
✓ NO API call is made (form validation prevents it)
✓ Button resets to "Place Order"
✓ Page stays on checkout
```

**Verify in Console:**
```
Should NOT see API calls:
✗ No fetch to /orders/place-order/
✗ No fetch to /orders/api/create-razorpay-order/
```

---

## Test Flow 6: Server Error Handling 🔥

### To test server error handling:

**Option A: Temporarily break backend**
```python
# In orders/views.py, temporarily add:
raise Exception("Test error")
```

**Then test:**
```
1. Go to checkout
2. Select all required fields
3. Click "Place Order"
4. Expected: Alert shows "Server error: 500"
5. Button resets
6. Page stays on checkout
7. Cart NOT cleared
```

**Option B: Invalid Razorpay credentials**
```python
# In settings.py, set:
RAZORPAY_KEY_ID = 'invalid'
RAZORPAY_KEY_SECRET = 'invalid'
```

**Then test:**
```
1. Go to checkout
2. Select all required fields
3. Click "Place Order"
4. Modal tries to open but shows error
5. Expected: Alert or console error about invalid credentials
```

---

## Browser Console Monitoring

### During Test Flow 1 (Successful), console should show in order:

```javascript
// 1. Form submission detected
✓ "Checkout form submitted, payment method: RAZORPAY"

// 2. Validation passed
✓ "Address selected, validating..."

// 3. First API call
✓ "Creating order..."
✓ Fetch POST /orders/place-order/

// 4. Response received
✓ "Order created: ORD-20260402-C7ADEC58, ID: 17"
✓ JSON: {success: true, order_id: 17, ...}

// 5. Second API call
✓ "Creating Razorpay order..."
✓ Fetch POST /orders/api/create-razorpay-order/

// 6. Response received
✓ "Razorpay order created: order_ABC123XYZ"
✓ JSON: {success: true, razorpay_order_id: ..., key_id: ..., amount: ...}

// 7. Modal preparation
✓ "Opening Razorpay modal..."

// 8. (User completes payment in modal)
✓ "Payment success callback: {razorpay_payment_id: pay_..., ...}"

// 9. Third API call
✓ "Verifying payment..."
✓ Fetch POST /orders/verify-razorpay-payment/

// 10. Final response
✓ "Payment verified successfully"
✓ "Redirecting to order detail..."
```

### If any step is missing or shows errors ❌

Check sections in [RAZORPAY_DEBUGGING.md](RAZORPAY_DEBUGGING.md).

---

## Network Tab Monitoring (F12 → Network)

### During Test Flow 1, you should see 3 successful requests:

```
1. POST /orders/place-order/
   Status: 200
   Response: {"success": true, "order_id": 17, ...}
   Headers:
     Content-Type: application/json
     X-Requested-With: XMLHttpRequest

2. POST /orders/api/create-razorpay-order/
   Status: 200
   Response: {"success": true, "razorpay_order_id": "order_...", ...}

3. POST /orders/verify-razorpay-payment/
   Status: 200
   Response: {"success": true, "redirect_url": "/orders/order/ORD-.../"}
```

### If any request fails (status 400, 500):
- Click on the request
- Go to "Response" tab to see error details
- Check [RAZORPAY_DEBUGGING.md](RAZORPAY_DEBUGGING.md) for that error

---

## Performance Metrics

### Expected Timing:
```
Place Order click → Processing... (1-2 sec) → Razorpay modal opens
     ↓
User enters card → Complete payment (30 sec)
     ↓
Backend verification (1-2 sec) → "Verifying Payment..." 
     ↓
Signature check (< 500ms) → Success alert (1.5 sec) → Redirect
     ↓
Total: ~30-35 seconds (mostly user action)
```

### If any step takes > 5 seconds:
- Check server logs for database queries
- Check Razorpay API response time
- Monitor server CPU/memory usage

---

## Final Verification Checklist

After all test flows complete:

- [ ] Test Flow 1: Successful payment works
- [ ] Test Flow 2: Cancelled payment preserves cart
- [ ] Test Flow 3: Failed payment preserves cart
- [ ] Test Flow 4: COD payment still works
- [ ] Test Flow 5: Validation prevents empty address
- [ ] Test Flow 6: Server errors handled gracefully
- [ ] Browser console clear of JavaScript errors
- [ ] Network tab shows all requests succeeding (status 200)
- [ ] Database shows correct payment_status after payment
- [ ] Cart cleared only after successful payment verification
- [ ] Invoice PDF generated and downloadable
- [ ] No raw JSON in browser
- [ ] Razorpay modal appears (not page redirect)

---

## Troubleshooting Quick Links

| Issue | See |
|-------|-----|
| Raw JSON showing | RAZORPAY_DEBUGGING.md → "Raw JSON Still Appearing?" |
| Order without payment | RAZORPAY_DEBUGGING.md → "Order Placed Without Payment?" |
| Modal doesn't open | RAZORPAY_DEBUGGING.md → "Razorpay Modal Never Opens?" |
| Signature fails | RAZORPAY_DEBUGGING.md → "Signature Verification Failing?" |
| Unexpected error | RAZORPAY_DEBUGGING.md → Error in server logs |

---

## Deployment Verification

After deploying to production, run these tests:

```bash
# 1. Check credentials are correct
python manage.py shell
>>> from django.conf import settings
>>> print(settings.RAZORPAY_KEY_ID[:20] + "...")
>>> print(settings.RAZORPAY_KEY_SECRET[:20] + "...")

# 2. Check migrations applied
python manage.py migrate --list | grep orders

# 3. Test a real payment with live credentials
# (Use test card with live key to get test payments)

# 4. Monitor logs for errors
tail -f logs/django.log | grep -i "payment\|razorpay"

# 5. Verify invoice generation
ls -la media/invoices/
```

---

## Success! 🎉

When all tests pass:
- ✅ Raw JSON issue FIXED
- ✅ Order without payment issue FIXED
- ✅ Modal opens correctly
- ✅ Signature verification working
- ✅ Cart management correct
- ✅ Ready for production

