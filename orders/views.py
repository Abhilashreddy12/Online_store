from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
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
    billing_addresses = Address.objects.filter(
        customer=request.user,
        address_type='BILLING',
        is_active=True
    )
    
    context = {
        'cart': cart,
        'shipping_addresses': shipping_addresses,
        'billing_addresses': billing_addresses,
    }
    return render(request, 'orders/checkout.html', context)


@login_required
def place_order(request):
    """Process order placement"""
    if request.method != 'POST':
        return redirect('orders:checkout')
    
    cart = get_object_or_404(Cart, customer=request.user)
    
    if not cart.items.exists():
        messages.error(request, 'Your cart is empty!')
        return redirect('cart:cart_detail')
    
    # Get addresses
    shipping_address_id = request.POST.get('shipping_address')
    billing_address_id = request.POST.get('billing_address')
    payment_method = request.POST.get('payment_method', 'COD')
    
    if not shipping_address_id or not billing_address_id:
        messages.error(request, 'Please select both shipping and billing addresses!')
        return redirect('orders:checkout')
    
    shipping_address = get_object_or_404(Address, id=shipping_address_id, customer=request.user)
    billing_address = get_object_or_404(Address, id=billing_address_id, customer=request.user)
    
    # Create order
    order = Order.objects.create(
        customer=request.user,
        shipping_address=shipping_address,
        billing_address=billing_address,
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
    
    # Clear cart
    cart.items.all().delete()
    
    messages.success(request, f'Order {order.order_number} placed successfully!')
    return redirect('orders:order_detail', order_number=order.order_number)


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

