from .models import Cart

def cart_context(request):
    """Add cart information to all templates"""
    cart_count = 0
    cart_total = 0
    
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(customer=request.user)
            cart_count = cart.total_items
            cart_total = cart.subtotal
        except Cart.DoesNotExist:
            pass
    
    return {
        'cart_count': cart_count,
        'cart_total': cart_total,
    }
