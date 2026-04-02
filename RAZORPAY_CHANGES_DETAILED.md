# Code Changes Summary - Razorpay Payment Flow Fixed

## File 1: orders/views.py - place_order() Function

### Change: Don't clear cart for Razorpay, only for COD

**Before:**
```python
# Clear cart (ALL CASES)
cart.items.all().delete()

# Handle response based on payment method
if payment_method == 'RAZORPAY':
    return JsonResponse({
        'success': True,
        'order_id': order.id,
        'order_number': order.order_number
    })
else:
    messages.success(request, f'Order {order.order_number} placed successfully!')
    return redirect('orders:order_detail', order_number=order.order_number)
```

**After:**
```python
# Handle response based on payment method
if payment_method == 'RAZORPAY':
    # For RAZORPAY: DON'T clear cart yet - cart will be cleared after payment verification
    # Return JSON with order ID for frontend to create Razorpay order
    response = JsonResponse({
        'success': True,
        'order_id': order.id,
        'order_number': order.order_number
    })
    # Ensure proper content-type for JSON response
    response['Content-Type'] = 'application/json'
    return response
else:
    # For COD: Immediately clear cart since payment is not required
    cart.items.all().delete()
    # For COD, redirect to order detail
    messages.success(request, f'Order {order.order_number} placed successfully!')
    return redirect('orders:order_detail', order_number=order.order_number)
```

**Why:** 
- Razorpay: Order created but payment pending. Cart preserved until payment verified.
- COD: No payment needed, so cart cleared immediately.

---

## File 2: orders/payment_views.py - Imports

### Change: Add Cart import

**Before:**
```python
from .models import Order, RazorpayPayment, Invoice
from .razorpay_service import RazorpayPaymentService, verify_idempotency
from .invoice_service import InvoiceGenerator
```

**After:**
```python
from .models import Order, RazorpayPayment, Invoice
from .razorpay_service import RazorpayPaymentService, verify_idempotency
from .invoice_service import InvoiceGenerator
from cart.models import Cart  # ADD THIS
```

**Why:** Need Cart model to clear cart after payment verification.

---

## File 3: orders/payment_views.py - verify_razorpay_payment()

### Change: Clear cart ONLY after successful payment verification

**Before:**
```python
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

return JsonResponse({
    'success': True,
    'message': f'Payment successful! Order {order.order_number} confirmed.',
    'redirect_url': reverse('orders:order_detail', kwargs={'order_number': order.order_number})
})
```

**After:**
```python
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

# Clear cart only after successful payment verification ← NEW
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
```

**Why:**
- Only clear cart AFTER signature verification succeeds
- If verification fails, cart is preserved for retry
- User doesn't lose items if payment fails

---

## File 4: templates/orders/checkout.html - Form Submission Handler

### Change: Prevent default form submission and use proper AJAX

**Before:**
```javascript
// Handle form submission with Razorpay integration
document.getElementById('checkout-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const paymentMethod = document.querySelector('input[name="payment_method"]:checked').value;
    
    if (paymentMethod === 'RAZORPAY') {
        // First, create order via normal form submission
        await createAndProcessRazorpayOrder();
    } else {
        // For COD and other methods, submit normally
        this.submit();
    }
});
```

**After:**
```javascript
// Handle form submission with Razorpay integration
document.getElementById('checkout-form').addEventListener('submit', async function(e) {
    e.preventDefault();  // CRITICAL: Stop form from submitting normally
    
    const paymentMethod = document.querySelector('input[name="payment_method"]:checked').value;
    const checkoutBtn = document.getElementById('checkout-btn');
    
    // Disable button during processing
    checkoutBtn.disabled = true;
    
    if (paymentMethod === 'RAZORPAY') {
        // For RAZORPAY: Process via AJAX, open Razorpay modal
        await createAndProcessRazorpayOrder();
    } else {
        // For COD: Submit form normally (this will redirect)
        // Re-enable button since form is submitting
        checkoutBtn.disabled = false;
        this.submit();  // Standard form submission for COD
    }
});
```

**Why:**
- Prevents double submission
- Clearly separates AJAX (Razorpay) from form submission (COD)
- Disables button during processing to prevent race conditions

---

## File 5: templates/orders/checkout.html - createAndProcessRazorpayOrder()

### Complete Rewrite

**Key Changes:**
1. **Proper JSON Response Handling**
   - Check Content-Type before parsing
   - Handle non-JSON responses (HTML errors)

2. **Improved Error Messages**
   - Tell user what went wrong
   - Better logging for debugging

3. **Form Validation**
   - Check shipping address selected
   - Check payment method is Razorpay
   - Before even hitting the server

4. **Better Button State Management**
   - Show "Processing..." during API calls
   - Reset button on errors
   - Prevent double-click submission

**New Code:**
```javascript
async function createAndProcessRazorpayOrder() {
    const form = document.getElementById('checkout-form');
    const checkoutBtn = document.getElementById('checkout-btn');
    
    checkoutBtn.textContent = 'Processing...';
    
    try {
        // Validate form before sending
        const shippingAddressValue = document.querySelector('input[name="shipping_address"]:checked');
        if (!shippingAddressValue) {
            throw new Error('Please select a shipping address');
        }
        
        const paymentMethodValue = document.querySelector('input[name="payment_method"]:checked');
        if (!paymentMethodValue || paymentMethodValue.value !== 'RAZORPAY') {
            throw new Error('Please select Razorpay as payment method');
        }
        
        // Step 1: Create order in our backend
        const formData = new FormData(form);
        const createOrderResponse = await fetch('{% url "orders:place_order" %}', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'  // Tell backend this is AJAX
            }
        });
        
        // Check response status
        if (!createOrderResponse.ok) {
            const errorText = await createOrderResponse.text();
            throw new Error(`Server error: ${createOrderResponse.status}`);
        }
        
        // Parse response - MUST be JSON
        const contentType = createOrderResponse.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            throw new Error('Invalid server response (not JSON)');
        }
        
        const orderData = await createOrderResponse.json();
        
        if (!orderData.success) {
            throw new Error(orderData.error || 'Failed to create order');
        }
        
        const orderId = orderData.order_id;
        
        // Step 2: Create Razorpay order
        const razorpayResponse = await fetch('{% url "orders:create_razorpay_order" %}', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: `order_id=${orderId}`
        });
        
        if (!razorpayResponse.ok) {
            throw new Error('Failed to create Razorpay order');
        }
        
        const razorpayData = await razorpayResponse.json();
        
        if (!razorpayData.success) {
            throw new Error(razorpayData.error || 'Failed to initiate payment');
        }
        
        // Step 3: Open Razorpay Checkout modal
        openRazorpayCheckout(razorpayData, orderId);
        
    } catch (error) {
        console.error('Checkout Error:', error);
        
        let userMessage = error.message;
        if (userMessage.includes('Server error')) {
            userMessage = 'Unable to process order. Please try again.';
        }
        
        alert('Checkout Error: ' + userMessage);
        checkoutBtn.disabled = false;
        checkoutBtn.textContent = 'Place Order';
    }
}
```

---

## File 6: templates/orders/checkout.html - openRazorpayCheckout()

### Enhanced with Better Documentation and Error Handling

**New Features:**
1. **Error Callback** - Shows user-friendly error message
2. **Modal Dismissed Callback** - User can close without paying and retry
3. **Security Comments** - Explains why frontend can't tamper with payment
4. **Better Logging** - Console logs for debugging

**Key Code Block:**
```javascript
error: function(error) {
    console.error('Razorpay error:', error);
    const errorMsg = error.description || error.message || 'Payment failed';
    alert(`Payment failed: ${errorMsg}`);
    
    // Reset button so user can try again
    const checkoutBtn = document.getElementById('checkout-btn');
    checkoutBtn.disabled = false;
    checkoutBtn.textContent = 'Place Order';
},

modal: {
    ondismiss: function() {
        console.log('User closed Razorpay modal without completing payment');
        // Reset button
        const checkoutBtn = document.getElementById('checkout-btn');
        checkoutBtn.disabled = false;
        checkoutBtn.textContent = 'Place Order';
    }
}
```

---

## File 7: templates/orders/checkout.html - verifyPayment()

### Complete Rewrite with Better UX

**Key Changes:**
1. **Signature Verification Explanation** - Comments explain why it's secure
2. **Better Success Flow** - Shows confirmation message, then redirects
3. **Better Error Flow** - Shows what went wrong, lets user retry
4. **Button State Management** - Properly disabled during verification

**New Code:**
```javascript
async function verifyPayment(paymentId, orderId, signature, orderDbId) {
    const checkoutBtn = document.getElementById('checkout-btn');
    checkoutBtn.textContent = 'Verifying Payment...';
    checkoutBtn.disabled = true;
    
    try {
        const verifyResponse = await fetch('{% url "orders:verify_razorpay_payment" %}', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({
                razorpay_payment_id: paymentId,
                razorpay_order_id: orderId,
                razorpay_signature: signature,
                order_id: orderDbId
            })
        });
        
        const verifyData = await verifyResponse.json();
        
        if (verifyData.success) {
            console.log('Payment verified successfully');
            alert('Payment successful! Your order has been confirmed. Redirecting...');
            
            // Redirect to order detail page
            setTimeout(() => {
                window.location.href = verifyData.redirect_url;
            }, 1500);
        } else {
            console.error('Payment verification failed:', verifyData.error);
            alert('Payment verification failed: ' + verifyData.error + '\nPlease contact support if you were charged.');
            
            // Reset button to allow retry
            checkoutBtn.disabled = false;
            checkoutBtn.textContent = 'Place Order';
        }
    } catch (error) {
        console.error('Verification error:', error);
        alert('Error verifying payment: ' + error.message);
        
        // Reset button
        checkoutBtn.disabled = false;
        checkoutBtn.textContent = 'Place Order';
    }
}
```

---

## Summary of Behavioral Changes

| Scenario | Before | After |
|----------|--------|-------|
| **User selects Razorpay & clicks Place Order** | Page reloads with JSON | Modal appears (AJAX, no reload) |
| **Order creation** | Order created, cart cleared | Order created, cart preserved |
| **If user closes modal** | Cart already gone | Cart preserved for retry |
| **Payment signature invalid** | Order already placed as PAID | Order stays PENDING, order PAID only if signature valid |
| **Error during payment** | Can't even retry | Can retry without losing cart |
| **Successful payment** | Cart already cleared | Cart cleared AFTER verification |
| **Form double-submission** | No protection | Button disabled during processing |
| **Error messages** | Generic "Error" | Specific error descriptions |

---

## Testing Commands

### Test the checkout flow locally:
```bash
cd a:\online_store\shopping_store

# Start dev server
python manage.py runserver

# Visit in browser:
# http://127.0.0.1:8000/orders/checkout/

# Use Razorpay test credentials:
# Key ID: (from Razorpay dashboard)
# Key Secret: (from Razorpay dashboard)
```

### Check logs for payment events:
```bash
# Monitor Django logs in real-time
tail -f logs/django.log | grep -i "payment\|order"
```

---

## Production Deployment

1. **Update Razorpay credentials in .env**
2. **Run migrations**: `python manage.py migrate`
3. **Collect static files**: `python manage.py collectstatic`
4. **Test on staging first**
5. **Monitor logs for errors**
6. **Verify signature verification is working**

All changes are backward compatible with COD and other payment methods.

