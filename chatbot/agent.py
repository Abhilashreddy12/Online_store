"""
Agent Module
------------
LangChain agent that orchestrates the shopping assistant chatbot.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any

from django.conf import settings
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

# Configuration - read from Django settings first, then env
def _get_openai_key():
    try:
        key = getattr(settings, 'OPENAI_API_KEY', '') or os.environ.get('OPENAI_API_KEY', '')
        return key.strip() if key else ''
    except Exception:
        return os.environ.get('OPENAI_API_KEY', '')

OPENAI_API_KEY = _get_openai_key()
LLM_MODEL = os.environ.get('LLM_MODEL', 'gpt-3.5-turbo')
USE_SIMPLE_AGENT = os.environ.get('USE_SIMPLE_AGENT', 'false').lower() == 'true'


SYSTEM_PROMPT = """You are a friendly and helpful AI shopping assistant for Fashion Store, an online clothing store.

Your capabilities:
1. Search for products based on user queries (supports filters like gender, color, size, price, material)
2. Provide product recommendations
3. Help with cart operations (view cart, add/remove items)
4. Track orders and show order history
5. Answer questions about store policies (shipping, returns, payments, etc.)
6. Recommend clothing sizes based on body measurements

Guidelines:
- Be friendly, professional, and concise
- When showing products, highlight key features like price discounts, materials, sizes
- If user asks about "this" or "the first one", refer to the last shown products
- For price queries, extract the price range (e.g., "under 1500" means max price ₹1500)
- Always confirm actions like adding to cart
- If you can't help with something, politely explain and suggest alternatives

Current context:
{context}

Conversation history:
{history}
"""


class SimpleAgent:
    """
    Simple rule-based agent for when LangChain/LLM is not available.
    Routes queries to appropriate tools without using an LLM.
    """
    
    def __init__(self, user: Optional[User] = None, session_id: str = None):
        self.user = user
        self.session_id = session_id or 'anonymous'
    
    def _detect_intent(self, message: str) -> str:
        """Detect user intent from message"""
        message_lower = message.lower()
        
        # Cart operations
        if any(word in message_lower for word in ['add to cart', 'add this', 'buy this', 'i want this']):
            return 'add_to_cart'
        if any(word in message_lower for word in ['show cart', 'my cart', 'view cart', 'cart items', "what's in my cart"]):
            return 'show_cart'
        if any(word in message_lower for word in ['remove from cart', 'delete from cart']):
            return 'remove_from_cart'
        
        # Order tracking
        if any(word in message_lower for word in ['track order', 'where is my order', 'order status', 'track my order']):
            return 'track_order'
        if any(word in message_lower for word in ['my orders', 'order history', 'past orders', 'previous orders']):
            return 'order_history'
        
        # Size recommendation
        if any(word in message_lower for word in ['what size', 'recommend size', 'size for me', 'which size']):
            if any(word in message_lower for word in ['cm', 'kg', 'height', 'weight']):
                return 'size_recommendation'
        
        # FAQ
        from .rag_pipeline import is_faq_query
        if is_faq_query(message):
            return 'faq'
        
        # Recommendations
        if any(word in message_lower for word in ['recommend', 'suggestion', 'similar', 'like this', 'for me']):
            return 'recommendations'
        
        # Default to product search
        return 'product_search'
    
    def _extract_size_params(self, message: str) -> Dict:
        """Extract size parameters from message"""
        import re
        
        params = {}
        
        # Height patterns
        height_match = re.search(r'(\d+)\s*(?:cm|centimeter)', message.lower())
        if height_match:
            params['height_cm'] = int(height_match.group(1))
        
        # Weight patterns
        weight_match = re.search(r'(\d+)\s*(?:kg|kilogram)', message.lower())
        if weight_match:
            params['weight_kg'] = int(weight_match.group(1))
        
        # Body type
        if 'slim' in message.lower():
            params['body_type'] = 'slim'
        elif 'athletic' in message.lower():
            params['body_type'] = 'athletic'
        else:
            params['body_type'] = 'regular'
        
        return params
    
    def run(self, message: str) -> Dict:
        """Process a message and return response"""
        from .tools import (
            search_products, extract_filters_from_query, get_semantic_recommendations,
            get_cart_items, add_to_cart, remove_from_cart, track_order, get_user_orders,
            suggest_size, get_personalized_recommendations
        )
        from .rag_pipeline import get_faq_response
        from .memory import get_memory
        
        intent = self._detect_intent(message)
        memory = get_memory()
        
        response = {
            'type': 'text',
            'message': '',
            'data': None
        }
        
        try:
            if intent == 'product_search':
                filters = extract_filters_from_query(message)
                products = search_products(query=message, filters=filters, limit=6)
                
                if products:
                    memory.set_last_products(self.session_id, [p['id'] for p in products])
                    memory.set_last_filters(self.session_id, filters)
                    
                    response['type'] = 'product_list'
                    response['message'] = f"I found {len(products)} products matching your search:"
                    response['data'] = {'products': products}
                else:
                    response['message'] = "I couldn't find any products matching your criteria. Try adjusting your filters or search terms."
            
            elif intent == 'recommendations':
                last_products = memory.get_last_products(self.session_id)
                
                if last_products:
                    products = get_semantic_recommendations(product_id=last_products[0], limit=5)
                elif self.user and self.user.is_authenticated:
                    products = get_personalized_recommendations(self.user, limit=5)
                else:
                    products = get_semantic_recommendations(query=message, limit=5)
                
                if products:
                    memory.set_last_products(self.session_id, [p['id'] for p in products])
                    response['type'] = 'product_list'
                    response['message'] = "Here are some recommendations for you:"
                    response['data'] = {'products': products}
                else:
                    response['message'] = "I couldn't find any recommendations at the moment."
            
            elif intent == 'show_cart':
                if not self.user or not self.user.is_authenticated:
                    response['message'] = "Please log in to view your cart."
                else:
                    cart = get_cart_items(self.user)
                    response['type'] = 'cart'
                    if cart['items']:
                        response['message'] = f"You have {cart['total_items']} item(s) in your cart:"
                    else:
                        response['message'] = "Your cart is empty."
                    response['data'] = {'cart': cart}
            
            elif intent == 'add_to_cart':
                if not self.user or not self.user.is_authenticated:
                    response['message'] = "Please log in to add items to your cart."
                else:
                    last_products = memory.get_last_products(self.session_id)
                    if last_products:
                        result = add_to_cart(self.user, last_products[0])
                        response['type'] = 'cart_action'
                        response['message'] = result['message']
                        response['data'] = result
                    else:
                        response['message'] = "Please search for a product first, then I can add it to your cart."
            
            elif intent == 'remove_from_cart':
                if not self.user or not self.user.is_authenticated:
                    response['message'] = "Please log in to manage your cart."
                else:
                    response['message'] = "To remove an item, please go to your cart page or specify which item to remove."
            
            elif intent == 'track_order':
                if not self.user or not self.user.is_authenticated:
                    response['message'] = "Please log in to track your orders."
                else:
                    # Try to extract order number from message
                    import re
                    order_match = re.search(r'ORD[-\s]?[\w-]+', message.upper())
                    order_number = order_match.group(0) if order_match else None
                    
                    result = track_order(self.user, order_number)
                    response['type'] = 'order'
                    if result['success']:
                        response['message'] = f"Order {result['order_number']} Status: {result['status_display']}"
                        response['data'] = result
                    else:
                        response['message'] = result['message']
            
            elif intent == 'order_history':
                if not self.user or not self.user.is_authenticated:
                    response['message'] = "Please log in to view your orders."
                else:
                    orders = get_user_orders(self.user, limit=5)
                    response['type'] = 'order_list'
                    if orders:
                        response['message'] = "Here are your recent orders:"
                        response['data'] = {'orders': orders}
                    else:
                        response['message'] = "You don't have any orders yet."
            
            elif intent == 'size_recommendation':
                params = self._extract_size_params(message)
                if 'height_cm' in params and 'weight_kg' in params:
                    result = suggest_size(**params)
                    response['type'] = 'size_recommendation'
                    response['message'] = result['tip']
                    response['data'] = result
                else:
                    response['message'] = "To recommend a size, please provide your height (in cm) and weight (in kg). For example: 'What size for 175 cm, 70 kg?'"
            
            elif intent == 'faq':
                faq_response = get_faq_response(message)
                response['type'] = 'faq'
                response['message'] = faq_response or "I don't have specific information about that. Please contact our customer support for assistance."
            
            else:
                response['message'] = "I'm not sure how to help with that. You can ask me to search for products, check your cart, track orders, or answer questions about our store policies."
        
        except Exception as e:
            logger.error(f"Agent error: {e}")
            response['message'] = "I encountered an error processing your request. Please try again."
        
        return response


class LangChainAgent:
    """
    LangChain-based agent using langgraph (compatible with langchain 1.x).
    Requires OpenAI API key.
    """

    def __init__(self, user: Optional[User] = None, session_id: str = None):
        self.user = user
        self.session_id = session_id or 'anonymous'
        self._llm = None
        self._tools = []
        self._setup_agent()

    def _setup_agent(self):
        """Initialize the LLM and tools"""
        try:
            from langchain_openai import ChatOpenAI
            from .tools import create_langchain_tools
            from .rag_pipeline import create_faq_tool

            api_key = _get_openai_key()
            if not api_key:
                logger.warning("OpenAI API key not set, LangChain agent unavailable")
                return

            self._llm = ChatOpenAI(
                model=LLM_MODEL,
                temperature=0.7,
                api_key=api_key
            )

            self._tools = create_langchain_tools(self.user, self.session_id)
            faq_tool = create_faq_tool()
            if faq_tool:
                self._tools.append(faq_tool)

            logger.info("LangChain agent initialized successfully")

        except ImportError as e:
            logger.warning(f"LangChain dependencies not available: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize LangChain agent: {e}")

    def run(self, message: str) -> Dict:
        """Process a message using langgraph react agent"""
        if self._llm is None:
            return SimpleAgent(self.user, self.session_id).run(message)

        try:
            from langgraph.prebuilt import create_react_agent
            from langchain_core.messages import HumanMessage, SystemMessage
            from .memory import get_memory

            # Build conversation history as messages
            memory = get_memory()
            history_entries = memory.get_history(self.session_id) if hasattr(memory, 'get_history') else []

            system_content = SYSTEM_PROMPT.format(context="", history="")
            messages = [SystemMessage(content=system_content)]

            # Add past turns (up to last 6)
            for entry in history_entries[-6:]:
                messages.append(HumanMessage(content=entry.get('user', '')))
                if entry.get('assistant'):
                    from langchain_core.messages import AIMessage
                    messages.append(AIMessage(content=entry['assistant']))

            messages.append(HumanMessage(content=message))

            agent = create_react_agent(self._llm, self._tools)
            result = agent.invoke({"messages": messages})

            # Extract the last AI message
            output = ''
            for msg in reversed(result.get('messages', [])):
                if hasattr(msg, 'content') and msg.__class__.__name__ == 'AIMessage':
                    output = msg.content
                    break

            if not output:
                output = result.get('output', '')

            # Try to parse structured JSON response
            try:
                if output.strip().startswith('{'):
                    return json.loads(output)
            except Exception:
                pass

            return {'type': 'text', 'message': output, 'data': None}

        except Exception as e:
            logger.error(f"LangChain agent error: {e}")
            return SimpleAgent(self.user, self.session_id).run(message)


def get_agent(user: Optional[User] = None, session_id: str = None):
    """
    Get the appropriate agent based on configuration.
    """
    api_key = _get_openai_key()
    if USE_SIMPLE_AGENT or not api_key:
        return SimpleAgent(user, session_id)
    
    return LangChainAgent(user, session_id)


def process_message(
    message: str,
    user: Optional[User] = None,
    session_id: str = None
) -> Dict:
    """
    Main entry point for processing chat messages.
    
    Args:
        message: User's message
        user: Django User object (optional)
        session_id: Session identifier for conversation tracking
    
    Returns:
        Dict with response type, message, and optional data
    """
    from .memory import get_memory
    from .models import ChatLog
    
    if not session_id:
        session_id = f"anon_{id(message)}"
    
    # Get memory and add user message
    memory = get_memory()
    memory.add_message(session_id, 'user', message)
    
    # Get agent and process message
    agent = get_agent(user, session_id)
    response = agent.run(message)
    
    # Add assistant response to memory
    memory.add_message(session_id, 'assistant', response.get('message', ''), response.get('data'))
    
    # Log conversation
    try:
        ChatLog.objects.create(
            user=user if user and user.is_authenticated else None,
            session_id=session_id,
            message=message,
            response=response.get('message', ''),
            response_type=response.get('type', 'text'),
            metadata=response.get('data')
        )
    except Exception as e:
        logger.error(f"Failed to log chat: {e}")
    
    return response
