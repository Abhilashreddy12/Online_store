from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)
from .models import Order, OrderItem, Coupon, OrderStatusHistory
from cart.models import Cart
from customers.models import Address


@login_required
def checkout(request):
    """Checkout page"""
    cart = get_object_or_404(Cart, customer=request.user)
    
    if not cart.items.exists():
        messages.warning(request, 'Your cart is empty!')
        return redirect('cart:cart_detail')
    
    shipping_addresses = Address.objects.filter(
        customer=request.user,
        address_type='SHIPPING',
        is_active=True
    )
   
    
    context = {
        'cart': cart,
        'shipping_addresses': shipping_addresses,
    }
    return render(request, 'orders/checkout.html', context)


@login_required
def place_order(request):
    """
    Process order placement.
    
    Supports both COD and RAZORPAY payment methods:
    - COD: Creates order and redirects to order detail
    - RAZORPAY: Creates order and returns JSON with order ID (frontend will create Razorpay order)
    """
    if request.method != 'POST':
        return redirect('orders:checkout')
    
    # Get payment method early to determine response type
    payment_method = request.POST.get('payment_method', 'COD')
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    try:
        cart = get_object_or_404(Cart, customer=request.user)
        
        if not cart.items.exists():
            error_msg = 'Your cart is empty!'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('cart:cart_detail')
        
        # Get addresses
        shipping_address_id = request.POST.get('shipping_address')
        
        if not shipping_address_id:
            error_msg = 'Please select a shipping address'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('orders:checkout')
        
        shipping_address = get_object_or_404(Address, id=shipping_address_id, customer=request.user)
        
        # Create order
        order = Order.objects.create(
            customer=request.user,
            shipping_address=shipping_address,
            payment_method=payment_method,
            subtotal=cart.subtotal,
            shipping_cost=Decimal('10.00'),  # Fixed shipping cost
            tax_amount=cart.subtotal * Decimal('0.10'),  # 10% tax
        )
        
        # Apply coupon if provided
        coupon_code = request.POST.get('coupon_code')
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, is_active=True)
                is_valid, message = coupon.is_valid()
                if is_valid:
                    if coupon.discount_type == 'PERCENTAGE':
                        discount = order.subtotal * (coupon.discount_value / 100)
                        if coupon.maximum_discount:
                            discount = min(discount, coupon.maximum_discount)
                    else:
                        discount = coupon.discount_value
                    order.discount_amount = discount
                    coupon.times_used += 1
                    coupon.save()
            except Coupon.DoesNotExist:
                pass
        
        # Calculate total
        order.total_amount = order.subtotal + order.tax_amount + order.shipping_cost - order.discount_amount
        order.status = 'PENDING'
        
        # Set payment status based on payment method
        if payment_method == 'RAZORPAY':
            order.payment_status = 'PENDING'  # Will be updated after payment verification
        elif payment_method == 'COD':
            order.payment_status = 'PENDING'  # COD is typically marked as paid on delivery
        
        order.save()
        
        # Create order items from cart
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                variant=cart_item.variant,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price,
            )
        
        # Create initial status history
        OrderStatusHistory.objects.create(
            order=order,
            status='PENDING',
            notes='Order placed successfully',
            created_by=request.user
        )
        
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
    
    except Exception as e:
        # Log error
        logger.error(f"Error placing order: {str(e)}")
        
        # Return appropriate response based on request type
        error_msg = f'Error placing order: {str(e)}'
        if is_ajax:
            return JsonResponse({'success': False, 'error': error_msg}, status=500)
        messages.error(request, error_msg)
        return redirect('orders:checkout')


@login_required
def order_list(request):
    """List user's orders"""
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    return render(request, 'orders/order_list.html', {'orders': orders})


@login_required
def order_detail(request, order_number):
    """Order detail page"""
    order = get_object_or_404(Order, order_number=order_number, customer=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})


@login_required
def cancel_order(request, order_number):
    """Cancel an order"""
    order = get_object_or_404(Order, order_number=order_number, customer=request.user)
    
    if order.status in ['PENDING', 'PROCESSING']:
        order.status = 'CANCELLED'
        order.save()
        
        OrderStatusHistory.objects.create(
            order=order,
            status='CANCELLED',
            notes='Order cancelled by customer',
            created_by=request.user
        )
        
        messages.success(request, f'Order {order.order_number} has been cancelled.')
    else:
        messages.error(request, 'This order cannot be cancelled.')
    
    return redirect('orders:order_detail', order_number=order.order_number)

