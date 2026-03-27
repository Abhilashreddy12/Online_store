"""
RAG Pipeline Module
-------------------
Retrieval Augmented Generation for FAQ and knowledge base queries.
"""

import logging
from typing import List, Dict, Optional

from django.db.models import Q

logger = logging.getLogger(__name__)

# Default FAQ content if database is empty
DEFAULT_FAQ = [
    {
        'category': 'shipping',
        'title': 'Shipping Information',
        'content': '''We offer free shipping on orders above ₹999. Standard delivery takes 3-5 business days. 
        Express delivery is available for ₹99 extra and takes 1-2 business days. 
        We ship to all major cities and towns across India. 
        You will receive a tracking number once your order is shipped.'''
    },
    {
        'category': 'returns',
        'title': 'Return Policy',
        'content': '''We offer a 30-day easy return policy. If you're not satisfied with your purchase, 
        you can return it within 30 days of delivery for a full refund. 
        Items must be unworn, unwashed, and with original tags. 
        To initiate a return, go to your orders page or contact customer support.'''
    },
    {
        'category': 'returns',
        'title': 'Exchange Policy',
        'content': '''We offer free exchanges for size or color within 30 days. 
        Simply initiate an exchange from your orders page. 
        The new item will be shipped once we receive the original.'''
    },
    {
        'category': 'payment',
        'title': 'Payment Methods',
        'content': '''We accept all major payment methods including:
        - Credit/Debit Cards (Visa, Mastercard, Rupay)
        - UPI (Google Pay, PhonePe, Paytm)
        - Net Banking
        - Cash on Delivery (COD) available for orders under ₹10,000
        - EMI options available on orders above ₹3,000
        All transactions are secured with 256-bit SSL encryption.'''
    },
    {
        'category': 'orders',
        'title': 'Order Tracking',
        'content': '''You can track your order in the following ways:
        1. Go to 'My Orders' in your account
        2. Use the tracking number sent via email/SMS
        3. Contact customer support with your order number
        Order status updates: Confirmed → Processing → Shipped → Out for Delivery → Delivered'''
    },
    {
        'category': 'orders',
        'title': 'Order Cancellation',
        'content': '''You can cancel your order before it's shipped. 
        Go to 'My Orders' and click 'Cancel Order'. 
        Refunds are processed within 5-7 business days to your original payment method. 
        COD orders can be cancelled anytime before delivery.'''
    },
    {
        'category': 'account',
        'title': 'Account Help',
        'content': '''To create an account, click 'Register' and provide your email and password. 
        You can reset your password using the 'Forgot Password' link on the login page. 
        Your account gives you access to order history, saved addresses, and wishlist.'''
    },
    {
        'category': 'sizing',
        'title': 'Size Guide',
        'content': '''Our size guide helps you find the perfect fit:
        - XS: Chest 34-36", Waist 28-30"
        - S: Chest 36-38", Waist 30-32"
        - M: Chest 38-40", Waist 32-34"
        - L: Chest 40-42", Waist 34-36"
        - XL: Chest 42-44", Waist 36-38"
        - XXL: Chest 44-46", Waist 38-40"
        For the best fit, measure yourself and compare with our size chart on each product page.'''
    },
    {
        'category': 'support',
        'title': 'Customer Support',
        'content': '''Our customer support team is available:
        - Email: support@fashionstore.com
        - Phone: 1800-XXX-XXXX (10 AM - 8 PM, Mon-Sat)
        - Live Chat: Available on our website
        - WhatsApp: +91-XXXXXXXXXX
        Average response time is under 2 hours.'''
    },
    {
        'category': 'discounts',
        'title': 'Discounts and Offers',
        'content': '''Check out our current offers:
        - 10% off on first order with code WELCOME10
        - Free shipping on orders above ₹999
        - Seasonal sales up to 50% off
        - Refer a friend and get ₹200 credit
        Subscribe to our newsletter for exclusive deals!'''
    }
]


def initialize_faq_documents():
    """Initialize FAQ documents in database if empty"""
    from .models import FAQDocument
    
    if FAQDocument.objects.count() == 0:
        for faq in DEFAULT_FAQ:
            FAQDocument.objects.create(
                title=faq['title'],
                content=faq['content'],
                category=faq['category'],
                is_active=True
            )
        logger.info(f"Initialized {len(DEFAULT_FAQ)} FAQ documents")


def rebuild_faq_index():
    """Rebuild the FAQ vector index"""
    from .models import FAQDocument
    from .embeddings import get_faq_store
    
    initialize_faq_documents()
    
    faq_docs = FAQDocument.objects.filter(is_active=True)
    store = get_faq_store()
    store.rebuild_index(faq_docs)
    
    logger.info(f"Rebuilt FAQ index with {faq_docs.count()} documents")


def search_faq(query: str, k: int = 3) -> List[Dict]:
    """Search FAQ documents using semantic search"""
    from .models import FAQDocument
    from .embeddings import get_faq_store
    
    # Try semantic search first
    try:
        store = get_faq_store()
        faq_ids = store.search(query, k=k)
        
        if faq_ids:
            faqs = FAQDocument.objects.filter(id__in=faq_ids, is_active=True)
            # Preserve order
            preserved = {fid: i for i, fid in enumerate(faq_ids)}
            faqs = list(faqs)
            faqs.sort(key=lambda f: preserved.get(f.id, 999))
            return [{'title': f.title, 'content': f.content, 'category': f.category} for f in faqs]
    except Exception as e:
        logger.warning(f"Semantic FAQ search failed: {e}")
    
    # Fallback to keyword search
    query_words = query.lower().split()
    faqs = FAQDocument.objects.filter(is_active=True)
    
    q_filter = Q()
    for word in query_words:
        q_filter |= Q(title__icontains=word) | Q(content__icontains=word) | Q(category__icontains=word)
    
    faqs = faqs.filter(q_filter)[:k]
    
    return [{'title': f.title, 'content': f.content, 'category': f.category} for f in faqs]


def get_faq_response(query: str) -> Optional[str]:
    """Get a response to an FAQ query"""
    results = search_faq(query, k=2)
    
    if not results:
        return None
    
    # Combine relevant FAQs into response
    response_parts = []
    for faq in results:
        response_parts.append(f"**{faq['title']}**\n{faq['content']}")
    
    return "\n\n".join(response_parts)


def is_faq_query(query: str) -> bool:
    """Detect if a query is likely an FAQ question"""
    faq_keywords = [
        'shipping', 'delivery', 'ship', 'deliver', 'when will',
        'return', 'refund', 'exchange', 'money back',
        'payment', 'pay', 'card', 'upi', 'cod', 'cash on delivery',
        'cancel', 'cancellation',
        'track', 'tracking', 'where is my order', 'order status',
        'size guide', 'size chart', 'what size', 'how to measure',
        'contact', 'support', 'help', 'customer service',
        'discount', 'coupon', 'offer', 'sale', 'promo code',
        'policy', 'terms', 'conditions',
        'how to', 'how do i', 'can i', 'do you'
    ]
    
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in faq_keywords)


def create_faq_tool():
    """Create a LangChain tool for FAQ queries"""
    try:
        from langchain_core.tools import tool as lc_tool
    except ImportError:
        return None

    @lc_tool
    def faq(query: str) -> str:
        """Answer questions about store policies, shipping, returns, payments, sizing, and other common questions. Use for general inquiries not related to specific products or orders."""
        import json
        response = get_faq_response(query)
        if response:
            return json.dumps({'type': 'faq', 'message': response})
        return json.dumps({'type': 'faq', 'message': "I don't have specific information about that. Please contact our customer support for assistance."})

    return faq
