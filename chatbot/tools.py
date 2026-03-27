"""
Tools Module
------------
LangChain tools for the shopping assistant chatbot.
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal

from django.db.models import Q, Avg
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


def parse_price_from_query(query: str) -> Dict[str, Optional[Decimal]]:
    """Extract price constraints from natural language query"""
    query_lower = query.lower()
    result = {'min_price': None, 'max_price': None}
    
    # Patterns for price extraction
    patterns = [
        # "under 1500", "below 1500", "less than 1500"
        (r'(?:under|below|less than|upto|up to|max|maximum)\s*(?:rs\.?|₹|inr)?\s*(\d+(?:,\d+)?)', 'max'),
        # "above 1000", "over 1000", "more than 1000"
        (r'(?:above|over|more than|min|minimum|atleast|at least)\s*(?:rs\.?|₹|inr)?\s*(\d+(?:,\d+)?)', 'min'),
        # "₹1500", "Rs 1500", "1500 rupees"
        (r'(?:rs\.?|₹|inr)\s*(\d+(?:,\d+)?)', 'max'),
        (r'(\d+(?:,\d+)?)\s*(?:rupees|rs\.?|₹)', 'max'),
        # "between 1000 and 2000", "1000-2000"
        (r'(?:between\s+)?(\d+(?:,\d+)?)\s*(?:to|-|and)\s*(\d+(?:,\d+)?)', 'range'),
    ]
    
    for pattern, price_type in patterns:
        match = re.search(pattern, query_lower)
        if match:
            if price_type == 'range':
                result['min_price'] = Decimal(match.group(1).replace(',', ''))
                result['max_price'] = Decimal(match.group(2).replace(',', ''))
            elif price_type == 'max':
                result['max_price'] = Decimal(match.group(1).replace(',', ''))
            elif price_type == 'min':
                result['min_price'] = Decimal(match.group(1).replace(',', ''))
            break
    
    return result


def extract_filters_from_query(query: str) -> Dict[str, Any]:
    """Extract all filters from a natural language query"""
    query_lower = query.lower()
    filters = {}
    
    # Gender detection
    gender_mapping = {
        'men': 'M', "men's": 'M', 'male': 'M', 'gents': 'M', 'boys': 'M',
        'women': 'F', "women's": 'F', 'female': 'F', 'ladies': 'F', 'girls': 'F',
        'kids': 'K', 'children': 'K', "kid's": 'K',
        'unisex': 'U'
    }
    for keyword, gender_code in gender_mapping.items():
        if keyword in query_lower:
            filters['gender'] = gender_code
            break
    
    # Color detection
    colors = ['black', 'white', 'red', 'blue', 'green', 'yellow', 'pink', 'purple', 
              'orange', 'brown', 'grey', 'gray', 'navy', 'maroon', 'beige', 'cream']
    for color in colors:
        if color in query_lower:
            filters['color'] = color
            break
    
    # Material detection
    materials = ['cotton', 'silk', 'polyester', 'linen', 'wool', 'denim', 'leather', 
                 'chiffon', 'rayon', 'nylon', 'velvet', 'satin']
    for material in materials:
        if material in query_lower:
            filters['material'] = material
            break
    
    # Price extraction
    price_filters = parse_price_from_query(query)
    if price_filters['min_price']:
        filters['min_price'] = price_filters['min_price']
    if price_filters['max_price']:
        filters['max_price'] = price_filters['max_price']
    
    # Size detection
    size_patterns = [
        r'\b(xs|s|m|l|xl|xxl|xxxl|2xl|3xl)\b',
        r'\bsize\s+([\w]+)\b'
    ]
    for pattern in size_patterns:
        match = re.search(pattern, query_lower)
        if match:
            filters['size'] = match.group(1).upper()
            break
    
    # Category/product type keywords (will be used for search)
    filters['search_terms'] = query_lower
    
    return filters


def search_products(
    query: str = None,
    filters: Dict = None,
    limit: int = 10,
    use_semantic: bool = True
) -> List[Dict]:
    """
    Search products using both database filters and semantic search.
    Returns a list of product dictionaries.
    """
    from catalog.models import Product, ProductVariant
    from .embeddings import get_product_store
    
    if filters is None:
        filters = {}
    
    # Start with active products
    queryset = Product.objects.filter(is_active=True).select_related('category', 'brand')
    
    # Apply filters
    if filters.get('gender'):
        queryset = queryset.filter(gender=filters['gender'])
    
    if filters.get('min_price'):
        queryset = queryset.filter(price__gte=filters['min_price'])
    
    if filters.get('max_price'):
        queryset = queryset.filter(price__lte=filters['max_price'])
    
    if filters.get('material'):
        queryset = queryset.filter(material__icontains=filters['material'])
    
    if filters.get('category'):
        queryset = queryset.filter(
            Q(category__name__icontains=filters['category']) |
            Q(category__slug__icontains=filters['category'])
        )
    
    if filters.get('brand'):
        queryset = queryset.filter(
            Q(brand__name__icontains=filters['brand']) |
            Q(brand__slug__icontains=filters['brand'])
        )
    
    # Color filter requires checking variants
    if filters.get('color'):
        color = filters['color']
        product_ids_with_color = ProductVariant.objects.filter(
            color__name__icontains=color
        ).values_list('product_id', flat=True)
        queryset = queryset.filter(id__in=product_ids_with_color)
    
    # Size filter
    if filters.get('size'):
        size = filters['size']
        product_ids_with_size = ProductVariant.objects.filter(
            size__code__iexact=size
        ).values_list('product_id', flat=True)
        queryset = queryset.filter(id__in=product_ids_with_size)
    
    # Text search on name/description
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query) |
            Q(brand__name__icontains=query)
        )
    
    # If using semantic search and we have a query
    product_ids = None
    if use_semantic and query:
        try:
            store = get_product_store()
            semantic_results = store.search_by_text(query, k=limit * 2)
            if semantic_results:
                # Get product IDs from semantic search
                semantic_ids = [pid for pid, score in semantic_results]
                # Combine with database filter results
                db_ids = list(queryset.values_list('id', flat=True)[:limit * 2])
                # Prioritize products that appear in both
                combined_ids = []
                for pid in semantic_ids:
                    if pid in db_ids:
                        combined_ids.append(pid)
                # Then add remaining semantic results
                for pid in semantic_ids:
                    if pid not in combined_ids:
                        combined_ids.append(pid)
                # Then add remaining db results
                for pid in db_ids:
                    if pid not in combined_ids:
                        combined_ids.append(pid)
                product_ids = combined_ids[:limit]
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
    
    # Get final results
    if product_ids:
        # Preserve order from semantic search
        preserved = {pid: i for i, pid in enumerate(product_ids)}
        products = list(queryset.filter(id__in=product_ids))
        products.sort(key=lambda p: preserved.get(p.id, 999))
    else:
        products = list(queryset[:limit])
    
    # Format results
    return [format_product(p) for p in products]


def format_product(product) -> Dict:
    """Format a product for chatbot response"""
    # Get primary image
    image_url = None
    try:
        primary_image = product.images.filter(is_primary=True).first()
        if not primary_image:
            primary_image = product.images.first()
        if primary_image and primary_image.image:
            image_url = primary_image.image.url
    except:
        pass
    
    # Get available sizes
    sizes = []
    try:
        sizes = list(product.variants.filter(
            stock_quantity__gt=0
        ).values_list('size__code', flat=True).distinct())
    except:
        pass
    
    # Get available colors
    colors = []
    try:
        colors = list(product.variants.values_list('color__name', flat=True).distinct())
    except:
        pass
    
    # Get average rating
    rating = None
    try:
        rating_data = product.reviews.filter(is_approved=True).aggregate(avg=Avg('rating'))
        rating = rating_data['avg']
    except:
        pass
    
    return {
        'id': product.id,
        'name': product.name,
        'slug': product.slug,
        'price': float(product.price),
        'compare_price': float(product.compare_price) if product.compare_price else None,
        'description': product.short_description or product.description[:200] if product.description else '',
        'category': product.category.name if product.category else '',
        'brand': product.brand.name if product.brand else '',
        'image_url': image_url,
        'available_sizes': sizes,
        'colors': colors,
        'rating': round(rating, 1) if rating else None,
        'in_stock': product.stock_quantity > 0,
        'discount_percentage': product.discount_percentage
    }


def get_semantic_recommendations(product_id: int = None, query: str = None, limit: int = 5) -> List[Dict]:
    """Get product recommendations using semantic similarity"""
    from catalog.models import Product
    from .embeddings import get_product_store
    
    try:
        store = get_product_store()
        
        if product_id:
            # Get product text and find similar
            product = Product.objects.get(id=product_id)
            from .embeddings import create_product_embedding_text
            text = create_product_embedding_text(product)
            results = store.search_by_text(text, k=limit + 1)  # +1 to exclude self
            product_ids = [pid for pid, _ in results if pid != product_id][:limit]
        elif query:
            results = store.search_by_text(query, k=limit)
            product_ids = [pid for pid, _ in results]
        else:
            return []
        
        products = Product.objects.filter(id__in=product_ids, is_active=True)
        # Preserve order
        preserved = {pid: i for i, pid in enumerate(product_ids)}
        products = list(products)
        products.sort(key=lambda p: preserved.get(p.id, 999))
        
        return [format_product(p) for p in products]
    except Exception as e:
        logger.error(f"Semantic recommendation error: {e}")
        return []


def get_cart_items(user: User) -> Dict:
    """Get cart items for a user"""
    from cart.models import Cart, CartItem
    
    try:
        cart = Cart.objects.get(customer=user)
        items = []
        for item in cart.items.select_related('product', 'variant'):
            item_data = {
                'id': item.id,
                'product_id': item.product.id,
                'product_name': item.product.name,
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'line_total': float(item.line_total),
            }
            if item.variant:
                item_data['variant'] = f"{item.variant.size.code if item.variant.size else ''} - {item.variant.color.name if item.variant.color else ''}"
            items.append(item_data)
        
        return {
            'items': items,
            'total_items': cart.total_items,
            'subtotal': float(cart.subtotal)
        }
    except Cart.DoesNotExist:
        return {'items': [], 'total_items': 0, 'subtotal': 0}


def add_to_cart(user: User, product_id: int, variant_id: int = None, quantity: int = 1) -> Dict:
    """Add a product to user's cart"""
    from catalog.models import Product, ProductVariant
    from cart.models import Cart, CartItem
    
    try:
        product = Product.objects.get(id=product_id, is_active=True)
        cart, _ = Cart.objects.get_or_create(customer=user)
        
        variant = None
        if variant_id:
            variant = ProductVariant.objects.get(id=variant_id, product=product)
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=variant,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        return {
            'success': True,
            'message': f'Added {product.name} to cart',
            'cart_total': cart.total_items
        }
    except Product.DoesNotExist:
        return {'success': False, 'message': 'Product not found'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def remove_from_cart(user: User, item_id: int = None, product_id: int = None) -> Dict:
    """Remove an item from cart"""
    from cart.models import Cart, CartItem
    
    try:
        cart = Cart.objects.get(customer=user)
        
        if item_id:
            item = CartItem.objects.get(id=item_id, cart=cart)
        elif product_id:
            item = CartItem.objects.get(product_id=product_id, cart=cart)
        else:
            return {'success': False, 'message': 'Please specify item to remove'}
        
        product_name = item.product.name
        item.delete()
        
        return {
            'success': True,
            'message': f'Removed {product_name} from cart'
        }
    except CartItem.DoesNotExist:
        return {'success': False, 'message': 'Item not found in cart'}
    except Cart.DoesNotExist:
        return {'success': False, 'message': 'Cart not found'}


def get_user_orders(user: User, limit: int = 5) -> List[Dict]:
    """Get user's recent orders"""
    from orders.models import Order
    
    orders = Order.objects.filter(customer=user).order_by('-created_at')[:limit]
    
    result = []
    for order in orders:
        result.append({
            'order_number': order.order_number,
            'status': order.status,
            'status_display': order.get_status_display(),
            'total_amount': float(order.total_amount),
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
            'tracking_number': order.tracking_number or None,
            'carrier': order.carrier or None,
            'items_count': order.items.count()
        })
    
    return result


def track_order(user: User, order_number: str = None) -> Dict:
    """Track an order"""
    from orders.models import Order
    
    try:
        if order_number:
            order = Order.objects.get(order_number=order_number, customer=user)
        else:
            # Get most recent order
            order = Order.objects.filter(customer=user).order_by('-created_at').first()
            if not order:
                return {'success': False, 'message': 'No orders found'}
        
        items = [
            {
                'name': item.product_name,
                'quantity': item.quantity,
                'price': float(item.unit_price)
            }
            for item in order.items.all()
        ]
        
        return {
            'success': True,
            'order_number': order.order_number,
            'status': order.status,
            'status_display': order.get_status_display(),
            'total_amount': float(order.total_amount),
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
            'tracking_number': order.tracking_number,
            'carrier': order.carrier,
            'shipped_at': order.shipped_at.strftime('%Y-%m-%d %H:%M') if order.shipped_at else None,
            'delivered_at': order.delivered_at.strftime('%Y-%m-%d %H:%M') if order.delivered_at else None,
            'items': items
        }
    except Order.DoesNotExist:
        return {'success': False, 'message': 'Order not found'}


def get_personalized_recommendations(user: User, limit: int = 5) -> List[Dict]:
    """Get personalized product recommendations based on user history"""
    from catalog.models import Product
    from orders.models import OrderItem
    from cart.models import WishlistItem
    
    # Get categories from past orders
    ordered_categories = OrderItem.objects.filter(
        order__customer=user
    ).values_list('product__category_id', flat=True).distinct()
    
    # Get categories from wishlist
    wishlist_categories = WishlistItem.objects.filter(
        wishlist__customer=user
    ).values_list('product__category_id', flat=True).distinct()
    
    # Combine categories
    categories = set(ordered_categories) | set(wishlist_categories)
    
    # Get ordered product IDs to exclude
    ordered_products = OrderItem.objects.filter(
        order__customer=user
    ).values_list('product_id', flat=True)
    
    # Find similar products
    if categories:
        products = Product.objects.filter(
            category_id__in=categories,
            is_active=True
        ).exclude(id__in=ordered_products).order_by('-is_featured', '-created_at')[:limit]
    else:
        # Fallback to featured/trending products
        products = Product.objects.filter(
            is_active=True,
            is_featured=True
        )[:limit]
    
    return [format_product(p) for p in products]


def get_trending_products(limit: int = 5) -> List[Dict]:
    """Get trending/popular products"""
    from catalog.models import Product
    from orders.models import OrderItem
    from django.db.models import Count
    from datetime import timedelta
    from django.utils import timezone
    
    # Get products ordered most in last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    trending_ids = OrderItem.objects.filter(
        order__created_at__gte=thirty_days_ago
    ).values('product_id').annotate(
        order_count=Count('id')
    ).order_by('-order_count').values_list('product_id', flat=True)[:limit]
    
    products = Product.objects.filter(id__in=trending_ids, is_active=True)
    
    # If not enough trending, add featured products
    if products.count() < limit:
        featured = Product.objects.filter(
            is_active=True,
            is_featured=True
        ).exclude(id__in=trending_ids)[:limit - products.count()]
        products = list(products) + list(featured)
    
    return [format_product(p) for p in products]


def suggest_size(height_cm: int, weight_kg: int, body_type: str = 'regular') -> Dict:
    """Suggest clothing size based on body measurements"""
    
    # Simple size recommendation logic
    bmi = weight_kg / ((height_cm / 100) ** 2)
    
    size_chart = {
        'slim': {
            (0, 18.5): 'XS',
            (18.5, 22): 'S',
            (22, 25): 'M',
            (25, 28): 'L',
            (28, 32): 'XL',
            (32, 100): 'XXL'
        },
        'regular': {
            (0, 18.5): 'S',
            (18.5, 23): 'M',
            (23, 27): 'L',
            (27, 31): 'XL',
            (31, 100): 'XXL'
        },
        'athletic': {
            (0, 20): 'M',
            (20, 25): 'L',
            (25, 30): 'XL',
            (30, 100): 'XXL'
        }
    }
    
    body_type = body_type.lower() if body_type else 'regular'
    if body_type not in size_chart:
        body_type = 'regular'
    
    chart = size_chart[body_type]
    
    recommended_size = 'M'  # Default
    for (low, high), size in chart.items():
        if low <= bmi < high:
            recommended_size = size
            break
    
    return {
        'recommended_size': recommended_size,
        'height_cm': height_cm,
        'weight_kg': weight_kg,
        'body_type': body_type,
        'bmi': round(bmi, 1),
        'tip': f"Based on your measurements (BMI: {round(bmi, 1)}), we recommend size {recommended_size}. "
               f"For a looser fit, consider going one size up."
    }


# LangChain Tool wrapper functions
def create_langchain_tools(user: Optional[User] = None, session_id: str = None):
    """Create LangChain tools for the agent (compatible with langchain 1.x / langchain_core)"""
    try:
        from langchain_core.tools import tool as lc_tool
    except ImportError:
        logger.warning("langchain_core not installed")
        return []

    from .memory import get_memory

    # Capture module-level references before any local name bindings
    _mod_add_to_cart = add_to_cart
    _mod_remove_from_cart = remove_from_cart
    _mod_track_order = track_order

    @lc_tool
    def product_search(query: str) -> str:
        """Search for products. Use when user wants to find, browse or filter products. Handles price, color, size, gender filters."""
        filters = extract_filters_from_query(query)
        products = search_products(query=query, filters=filters, limit=5)
        if session_id:
            memory = get_memory()
            memory.set_last_products(session_id, [p['id'] for p in products])
            memory.set_last_filters(session_id, filters)
        if not products:
            return "No products found matching your criteria."
        return json.dumps({'type': 'product_list', 'products': products})

    @lc_tool
    def product_recommendations(query: str) -> str:
        """Get product recommendations. Use when user asks for recommendations, similar items, or suggestions."""
        if session_id:
            memory = get_memory()
            last_products = memory.get_last_products(session_id)
            if last_products and any(w in query.lower() for w in ['similar', 'like this', 'these', 'recommend']):
                products = get_semantic_recommendations(product_id=last_products[0], limit=5)
                return json.dumps({'type': 'product_list', 'products': products})
        products = get_semantic_recommendations(query=query, limit=5)
        return json.dumps({'type': 'product_list', 'products': products})

    @lc_tool
    def show_cart(query: str = "") -> str:
        """Show the user's shopping cart contents."""
        if not user or not user.is_authenticated:
            return json.dumps({'type': 'error', 'message': 'Please login to view your cart'})
        cart = get_cart_items(user)
        return json.dumps({'type': 'cart', 'cart': cart})

    @lc_tool
    def add_to_cart_tool(product_id: int, quantity: int = 1) -> str:
        """Add a product to the shopping cart. product_id is required."""
        if not user or not user.is_authenticated:
            return json.dumps({'type': 'error', 'message': 'Please login to add items to cart'})
        pid = product_id
        if not pid and session_id:
            memory = get_memory()
            last = memory.get_last_products(session_id)
            if last:
                pid = last[0]
        if not pid:
            return json.dumps({'type': 'error', 'message': 'Please specify which product to add'})
        result = _mod_add_to_cart(user, pid, quantity=quantity)
        return json.dumps({'type': 'cart_action', **result})

    @lc_tool
    def remove_from_cart_tool(product_id: int) -> str:
        """Remove a product from the shopping cart by product_id."""
        if not user or not user.is_authenticated:
            return json.dumps({'type': 'error', 'message': 'Please login first'})
        result = _mod_remove_from_cart(user, product_id=product_id)
        return json.dumps({'type': 'cart_action', **result})

    @lc_tool
    def track_order_tool(order_number: str = "") -> str:
        """Track an order status. Pass order number or leave empty for the latest order."""
        if not user or not user.is_authenticated:
            return json.dumps({'type': 'error', 'message': 'Please login to track orders'})
        result = _mod_track_order(user, order_number.strip() or None)
        return json.dumps({'type': 'order', **result})

    @lc_tool
    def order_history(query: str = "") -> str:
        """Get user's recent order history."""
        if not user or not user.is_authenticated:
            return json.dumps({'type': 'error', 'message': 'Please login to view orders'})
        orders = get_user_orders(user, limit=5)
        return json.dumps({'type': 'order_list', 'orders': orders})

    @lc_tool
    def personalized_recommendations(query: str = "") -> str:
        """Get personalized product recommendations based on user preferences and history."""
        if user and user.is_authenticated:
            products = get_personalized_recommendations(user, limit=5)
        else:
            products = get_trending_products(limit=5)
        return json.dumps({'type': 'product_list', 'products': products})

    @lc_tool
    def size_recommendation(height_cm: int, weight_kg: int, body_type: str = "regular") -> str:
        """Recommend clothing size based on height (cm), weight (kg), and body type (slim/regular/athletic)."""
        result = suggest_size(height_cm, weight_kg, body_type)
        return json.dumps({'type': 'size_recommendation', **result})

    return [
        product_search,
        product_recommendations,
        show_cart,
        add_to_cart_tool,
        remove_from_cart_tool,
        track_order_tool,
        order_history,
        personalized_recommendations,
        size_recommendation,
    ]
