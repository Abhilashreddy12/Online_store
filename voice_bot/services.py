"""
Business Logic Layer - Intent-to-Response mapping

Features:
- Maps intents to actual Django model queries
- Handles order tracking, product search, etc.
- Returns structured responses
- Extensible architecture for new intents
"""

import logging
from typing import Dict, Any
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.db.models import Q

from orders.models import Order, OrderItem
from catalog.models import Product, Category, Brand
from .intent import IntentType

logger = logging.getLogger(__name__)


class VoiceServiceHandler:
    """Main service handler that maps intents to business logic"""
    
    def __init__(self):
        """Initialize service handler"""
        self.handlers = {
            IntentType.ORDER_TRACKING.value: self.handle_order_tracking,
            IntentType.PRODUCT_SEARCH.value: self.handle_product_search,
            IntentType.PAYMENT_ISSUE.value: self.handle_payment_issue,
            IntentType.RETURN_REQUEST.value: self.handle_return_request,
            IntentType.GENERAL_QUERY.value: self.handle_general_query,
            IntentType.UNKNOWN.value: self.handle_unknown_query,
        }
    
    def handle_query(
        self,
        intent: str,
        query_text: str,
        user: User = None
    ) -> Dict[str, Any]:
        """
        Route query to appropriate handler
        
        Args:
            intent: Intent type
            query_text: Original query text
            user: Django User object (optional)
        
        Returns:
            {
                'response': response message,
                'data': relevant data,
                'success': bool
            }
        """
        handler = self.handlers.get(intent, self.handle_unknown_query)
        
        try:
            result = handler(query_text, user)
            return result
        except Exception as e:
            logger.error(f"Error handling {intent}: {str(e)}", exc_info=True)
            return {
                'response': "Sorry, I encountered an error processing your request. Please try again.",
                'data': {},
                'success': False,
                'error': str(e)
            }
    
    # ========== ORDER TRACKING ==========
    
    def handle_order_tracking(self, query_text: str, user: User = None) -> Dict:
        """Handle order tracking queries"""
        if not user:
            return {
                'response': "Please log in to track your orders.",
                'data': {},
                'success': False
            }
        
        try:
            # Get recent orders for user
            recent_orders = Order.objects.filter(
                customer=user
            ).order_by('-created_at')[:5]
            
            if not recent_orders.exists():
                return {
                    'response': "You have no orders yet.",
                    'data': {'orders': []},
                    'success': True
                }
            
            # Format order information
            orders_info = []
            for order in recent_orders:
                status_display = dict(Order.STATUS_CHOICES).get(order.status)
                payment_status = dict(Order.PAYMENT_STATUS_CHOICES).get(order.payment_status)
                
                order_info = {
                    'order_number': order.order_number,
                    'status': order.status,
                    'status_display': status_display,
                    'payment_status': payment_status,
                    'total_amount': float(order.total_amount),
                    'created_at': order.created_at.strftime('%Y-%m-%d'),
                }
                
                # Add delivery info if available
                if order.delivered_at:
                    order_info['delivered_date'] = order.delivered_at.strftime('%Y-%m-%d')
                elif order.shipped_at:
                    order_info['shipped_date'] = order.shipped_at.strftime('%Y-%m-%d')
                
                # Add tracking number if available
                if order.tracking_number:
                    order_info['tracking_number'] = order.tracking_number
                    order_info['carrier'] = order.carrier
                
                orders_info.append(order_info)
            
            # Build response message
            latest_order = recent_orders[0]
            response = self._format_order_tracking_response(latest_order)
            
            return {
                'response': response,
                'data': {'orders': orders_info},
                'success': True
            }
        
        except Exception as e:
            logger.error(f"Order tracking error: {str(e)}")
            return {
                'response': "I couldn't retrieve your order information. Please try again.",
                'data': {},
                'success': False
            }
    
    def _format_order_tracking_response(self, order: Order) -> str:
        """Format friendly order tracking response"""
        status_msg = {
            'PENDING': 'is being processed',
            'PROCESSING': 'is being prepared for shipment',
            'SHIPPED': f'has been shipped',
            'DELIVERED': 'has been delivered',
            'CANCELLED': 'has been cancelled',
            'REFUNDED': 'has been refunded',
        }
        
        status_text = status_msg.get(order.status, 'is being processed')
        response = f"Your order {order.order_number} {status_text}."
        
        if order.status == 'SHIPPED' and order.tracking_number:
            response += f" Tracking number: {order.tracking_number}."
        elif order.status == 'DELIVERED' and order.delivered_at:
            response += f" It was delivered on {order.delivered_at.strftime('%B %d, %Y')}."
        
        return response
    
    # ========== PRODUCT SEARCH ==========
    
    def handle_product_search(self, query_text: str, user: User = None) -> Dict:
        """Handle product search queries"""
        try:
            # Extract search keywords
            keywords = self._extract_keywords(query_text)
            
            if not keywords:
                return {
                    'response': "Please specify what product you're looking for.",
                    'data': {'products': []},
                    'success': True
                }
            
            # Search products
            products = Product.objects.filter(
                Q(name__icontains=keywords) |
                Q(description__icontains=keywords) |
                Q(category__name__icontains=keywords) |
                Q(brand__name__icontains=keywords),
                is_active=True
            )[:10]
            
            if not products.exists():
                return {
                    'response': f"Sorry, I couldn't find any products matching '{keywords}'.",
                    'data': {'products': []},
                    'success': True
                }
            
            # Format product information
            products_info = []
            for product in products[:3]:  # Show top 3
                products_info.append({
                    'name': product.name,
                    'price': float(product.price),
                    'category': product.category.name,
                    'brand': product.brand.name if product.brand else 'Unknown',
                    'in_stock': product.stock_quantity > 0,
                    'short_description': product.short_description or product.description[:100],
                })
            
            # Build response
            product_names = ', '.join([p['name'] for p in products_info])
            response = f"I found these products: {product_names}."
            
            return {
                'response': response,
                'data': {'products': products_info, 'total_found': products.count()},
                'success': True
            }
        
        except Exception as e:
            logger.error(f"Product search error: {str(e)}")
            return {
                'response': "I encountered an error searching for products. Please try again.",
                'data': {'products': []},
                'success': False
            }
    
    # ========== PAYMENT ISSUE ==========
    
    def handle_payment_issue(self, query_text: str, user: User = None) -> Dict:
        """Handle payment-related queries"""
        response = (
            "I'm sorry you're experiencing a payment issue. Here are your options:\n"
            "1. Check your internet connection and try again\n"
            "2. Use a different payment method\n"
            "3. Contact our support team at support@madiriclet.com\n"
            "4. Call our customer service for immediate assistance"
        )
        
        return {
            'response': response,
            'data': {
                'support_email': 'support@madiriclet.com',
                'issue_type': 'payment'
            },
            'success': True
        }
    
    # ========== RETURN REQUEST ==========
    
    def handle_return_request(self, query_text: str, user: User = None) -> Dict:
        """Handle return and exchange requests"""
        response = (
            "Our return policy allows returns within 30 days of purchase. "
            "Here's what you need to do:\n"
            "1. Contact our support team with your order number\n"
            "2. Provide reason for return\n"
            "3. We'll provide you with a return label\n"
            "4. Ship the item back to us\n"
            "Your refund will be processed within 5-7 business days."
        )
        
        return {
            'response': response,
            'data': {
                'return_window_days': 30,
                'refund_processing_days': '5-7',
                'support_email': 'support@madiriclet.com'
            },
            'success': True
        }
    
    # ========== GENERAL QUERY ==========
    
    def handle_general_query(self, query_text: str, user: User = None) -> Dict:
        """Handle general/greeting queries"""
        response = (
            "Hello! I'm your AI shopping assistant. I can help you with:\n"
            "- Track your orders\n"
            "- Search for products\n"
            "- Answer payment questions\n"
            "- Explain our return policy\n"
            "How can I assist you today?"
        )
        
        return {
            'response': response,
            'data': {'query_type': 'general'},
            'success': True
        }
    
    # ========== UNKNOWN QUERY ==========
    
    def handle_unknown_query(self, query_text: str, user: User = None) -> Dict:
        """Handle unknown queries"""
        response = (
            "I'm not sure how to help with that. "
            "Try asking about:\n"
            "- Order tracking\n"
            "- Product search\n"
            "- Payment issues\n"
            "- Return requests"
        )
        
        return {
            'response': response,
            'data': {'query_type': 'unknown'},
            'success': True
        }
    
    # ========== UTILITY METHODS ==========
    
    @staticmethod
    def _extract_keywords(text: str, min_length: int = 3) -> str:
        """Extract search keywords from text"""
        # Remove common words
        stop_words = {
            'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'is', 'are', 'was', 'were', 'be', 'have', 'has', 'had', 'do',
            'does', 'did', 'will', 'would', 'could', 'should', 'can', 'may', 'might'
        }
        
        words = [w for w in text.lower().split() if w not in stop_words and len(w) >= min_length]
        return ' '.join(words)


# Global service handler instance
_service_handler = None


def get_service_handler() -> VoiceServiceHandler:
    """Get or create the service handler"""
    global _service_handler
    if _service_handler is None:
        _service_handler = VoiceServiceHandler()
    return _service_handler


def handle_voice_query(
    intent: str,
    query_text: str,
    user: User = None
) -> dict:
    """
    Convenience function to handle voice query
    
    Returns:
        {
            'response': response message,
            'data': relevant data,
            'success': bool
        }
    """
    handler = get_service_handler()
    return handler.handle_query(intent, query_text, user)
