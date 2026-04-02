# Razorpay Debugging Guide

## Issue: Raw JSON Still Appearing?

### Symptoms:
```
Browser shows:
{"success": true, "order_id": 17, "order_number": "ORD-20260402-C7ADEC58"}
```

### Root Causes & Fixes:

**1. Browser Cache**
```bash
# Hard refresh (Ctrl+Shift+R on Windows)
# or clear browser cache
```

**2. JavaScript Not Updated**
```bash
# Check Chrome DevTools Network tab:
# Should see: POST /orders/place-order/ → JSON response (not form submission)

# If form submission shown:
# - Clear browser cache
# - Hard refresh
# - Check HTML for proper form attributes
```

**3. Content-Type Header Missing**
```python
# In orders/views.py, verify this line exists:
response = JsonResponse({...})
response['Content-Type'] = 'application/json'
return response
```

**4. X-Requested-With Header Missing**
```javascript
// In checkout.html, verify:
headers: {
    'X-Requested-With': 'XMLHttpRequest'  // ← Must have this
}
```

---

## Issue: Order Placed Without Payment?

### Symptoms:
- Order confirmed, cart empty, but payment not processed
- User can see order in "My Orders" without paying
- Razor pay modal never opened

### Verification Steps:

**Step 1: Check order payment_status**
```bash
python manage.py shell
>>> from orders.models import Order
>>> order = Order.objects.latest('created_at')
>>> order.payment_status
'PENDING' or 'PAID'?
>>> order.status
'PENDING' or 'PROCESSING'?
```

Expected:
- If payment successful: `payment_status='PAID', status='PROCESSING'`
- If payment pending: `payment_status='PENDING', status='PENDING'`

**Step 2: Check cart status**
```bash
>>> from cart.models import Cart
>>> cart = Cart.objects.get(customer=order.customer)
>>> cart.items.count()
Should be 0 if payment completed
```

**Step 3: Check RazorpayPayment record**
```bash
>>> from orders.models import RazorpayPayment
>>> rp = RazorpayPayment.objects.filter(order=order).latest('created_at')
>>> rp.payment_status
'PENDING', 'CAPTURED', or 'FAILED'?
>>> rp.signature_verified
True or False?
```

### If Order is PAID but payment was never made:

**Check browser console for errors:**
1. Open DevTools (F12)
2. Go to Console tab
3. Look for JavaScript errors during checkout
4. Look for fetch errors (red text)

**Check server logs:**
```bash
# Look for payment verification attempts
grep "Signature verification" shopping_store.log
```

Expected log entries:
```
INFO: Razorpay order created for Order #ORD-20260402-C7ADEC58
INFO: Payment verified and captured for order ORD-20260402-C7ADEC58
```

### Root Causes:

| Cause | Symptoms | Fix |
|-------|----------|-----|
| Old JS cached | Raw JSON showing | Ctrl+Shift+R hard refresh |
| Cart cleared before verification | Order paid but shouldn't be | Restart server, check checkout.html |
| Admin manually processed | No payment flow happened | Check admin logs |
| Old Python bytecode | Changes not taking effect | `find . -type d -name __pycache__ -exec rm -r {} +` |

---

## Issue: "Unexpected Token" Error?

### Symptoms:
```
Console Error:
SyntaxError: Unexpected token '<', '<!DOCTYPE html>...'
```

### This means:
- Backend returned HTML instead of JSON
- Frontend tried to parse HTML as JSON

### Root Cause:
Old code version still running. The fixes should prevent this.

### Verify Fix Applied:

**Check file has changes:**
```bash
grep -n "X-Requested-With" templates/orders/checkout.html
# Should find lines in createAndProcessRazorpayOrder()

grep -n "Content-Type" orders/views.py
# Should find response['Content-Type'] = 'application/json'
```

**If not found:**
```bash
# Restart Django server
# Clear browser cache
# Check you edited the correct files
```

---

## Issue: Razorpay Modal Never Opens?

### Symptoms:
- Click "Place Order"
- Button shows "Processing..."
- Nothing happens
- No error in console

### Debug Steps:

**Step 1: Check browser console (F12)**
```
Look for messages like:
✓ Order created: ORD-20260402-C7ADEC58, ID: 17
✓ Razorpay order created: order_ABC123XYZ
✓ Opening Razorpay modal...
```

If not showing, check for errors below.

**Step 2: Check Network tab (F12 → Network)**
```
POST /orders/place-order/
→ Response: {"success": true, "order_id": 17, ...}

POST /orders/api/create-razorpay-order/
→ Response: {"success": true, "razorpay_order_id": "order_ABC123...", ...}
```

If any show error (red), click to see details.

**Step 3: Check server logs**
```bash
tail -50 shopping_store.log | grep -i "error\|razorpay"
```

### Common Issues:

| Error | Fix |
|-------|-----|
| "Order not found" | Check order_id sent to API matches DB |
| "Razorpay service error" | Check RAZORPAY_KEY_ID & KEY_SECRET in settings |
| "Payment already initiated" | Order already has a RazorpayPayment record, can't create second |
| "Invalid payment method" | Order.payment_method must be 'RAZORPAY' |

---

## Issue: Signature Verification Failing?

### Symptoms:
- Payment shows success in Razorpay
- Frontend verification fails
- Error: "Payment verification failed"
- Order stays PENDING

### Why This Happens:
- Secret key mismatch
- Tampered signature
- Outdated signature format

### Debug Steps:

**Step 1: Check secret key**
```bash
# In Django shell
from django.conf import settings
print(settings.RAZORPAY_KEY_SECRET)
# Should match actual secret key from Razorpay dashboard
```

**Step 2: Check logs for verification attempt**
```bash
grep "Signature verification" shopping_store.log
# Look for SUCCESS or FAILED entries
```

**Step 3: Verify backend implementation**
```python
# In razorpay_service.py, check:
from razorpay.utilities.signature_verification import SignatureException

def verify_payment_signature(self, order_id, payment_id, signature):
    hash_key = f"{order_id}|{payment_id}"  # This must match Razorpay format
    # HMAC SHA256 verification happens here
```

### Production Checklist:

- [ ] Using live RAZORPAY_KEY_ID (starts with `rzp_live_`)
- [ ] Using live RAZORPAY_KEY_SECRET (32+ characters)
- [ ] HTTPS enabled (Razorpay requires HTTPS for payment)
- [ ] SSL certificate valid
- [ ] No proxy/CDN issues with request forwarding

---

## Performance Issues?

### Slow Payment Processing?

**Check these:**

1. **Database Queries**
```bash
# In Django settings.py for debugging:
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
        },
    }
}
# Then check logs for slow queries
```

2. **Razorpay API Response Time**
```javascript
// Add timing to checkout.html
const startTime = Date.now();
const razorpayResponse = await fetch(URL);
console.log(`Razorpay API: ${Date.now() - startTime}ms`);
```

3. **Database Indexes**
```bash
python manage.py shell
>>> from django.db import connection
>>> # Check payment queries use indexes
```

---

## Payment Not Appearing in Razorpay Dashboard?

### Check:

1. **Using test vs live credentials**
   - Test credentials: Dashboard shows test payments separately
   - Live credentials: Dashboard shows real customers

2. **Razorpay order was actually created**
   ```bash
   python manage.py shell
   >>> from orders.models import RazorpayPayment
   >>> rp = RazorpayPayment.objects.latest('created_at')
   >>> print(rp.razorpay_order_id)
   # Check if this ID exists in Razorpay dashboard
   ```

3. **Payment webhook**
   - Razorpay may send webhook after payment
   - Check webhook logs in Razorpay dashboard settings

---

## Logging & Monitoring

### Enable detailed logging:

**In shopping_store/settings.py:**
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'orders_payment.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'orders.views': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'orders.payment_views': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'orders.razorpay_service': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

### Key Events to Look For:

```bash
# 1. Order creation
grep "Order placed successfully" orders_payment.log

# 2. Razorpay order creation
grep "Razorpay order created" orders_payment.log

# 3. Payment verification
grep "Payment verified" orders_payment.log

# 4. Signature verification
grep "Signature verification" orders_payment.log

# 5. Cart clearing
grep "Cart cleared" orders_payment.log

# 6. Invoice generation
grep "Invoice generated" orders_payment.log

# 7. Errors
grep "ERROR\|Exception" orders_payment.log
```

---

## Quick Reference: State Transitions

### Successful Payment Flow:

```
Order Creation:
  status: PENDING → PENDING
  payment_status: PENDING → PENDING
  cart: [items] → [items]

Razorpay Order Created:
  RazorpayPayment.payment_status: PENDING → PENDING
  
Payment Completed:
  (Razorpay modal shows success)

Signature Verification (Backend):
  RazorpayPayment.signature_verified: False → True
  RazorpayPayment.payment_status: PENDING → CAPTURED
  Order.status: PENDING → PROCESSING
  Order.payment_status: PENDING → PAID
  cart: [items] → []
```

### Failed Payment Flow:

```
Order Creation:
  status: PENDING → PENDING
  payment_status: PENDING → PENDING
  cart: [items] → [items]

Razorpay Order Created:
  RazorpayPayment.payment_status: PENDING → PENDING

Payment Failed or User Closed Modal:
  (Razorpay returns error/dismissed callback)

Order Status:
  status: PENDING → PENDING (unchanged)
  payment_status: PENDING → PENDING (unchanged)
  cart: [items] → [items] (unchanged - can retry)
```

---

## Testing Payment Locally

### Razorpay Test Cards:

```
Card Number: 4111111111111111
Expiry: 12/25
CVV: 123
OTP: 000000
```

### Test Credentials:
```
RAZORPAY_KEY_ID: rzp_test_xxxxx (from Razorpay test dashboard)
RAZORPAY_KEY_SECRET: xxxxx (from Razorpay test dashboard)
```

### Expected Flow:
1. Click "Place Order" → Order created in DB
2. Razorpay modal opens
3. Enter test card details
4. OTP page shows (enter 000000)
5. Modal closes → Page shows "Verifying Payment..."
6. Orders shows in DB with status=PROCESSING, payment_status=PAID
7. Redirects to Order Detail

---

## Contact Razorpay Support:

If payment issues persist:
1. Check Razorpay status page: https://status.razorpay.com/
2. Verify API keys are correct (from Razorpay dashboard → Settings)
3. Check webhook logs in Razorpay dashboard
4. Contact Razorpay support with Order ID and payment ID

