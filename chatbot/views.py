"""
Views Module
------------
API endpoints for the chatbot.
"""

import json
import logging
import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)


def get_or_create_session_id(request):
    """Get or create a session ID for the chat"""
    session_id = request.session.get('chatbot_session_id')
    if not session_id:
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        request.session['chatbot_session_id'] = session_id
    return session_id


@csrf_exempt
@require_http_methods(["POST"])
def chat_api(request):
    """
    Main chat API endpoint.
    
    POST /chatbot/api/chat/
    
    Request body:
    {
        "message": "Find black shirts under 1500",
        "session_id": "optional-session-id"
    }
    
    Response:
    {
        "type": "product_list" | "text" | "cart" | "order" | "faq" | "error",
        "message": "Response message",
        "data": { ... optional data ... }
    }
    """
    try:
        # Parse request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'type': 'error',
                'message': 'Invalid JSON in request body'
            }, status=400)
        
        message = data.get('message', '').strip()
        if not message:
            return JsonResponse({
                'type': 'error',
                'message': 'Message is required'
            }, status=400)
        
        # Get session ID
        session_id = data.get('session_id') or get_or_create_session_id(request)
        
        # Get user if authenticated
        user = request.user if request.user.is_authenticated else None
        
        # Process message
        from .agent import process_message
        response = process_message(message, user, session_id)
        
        # Add session_id to response
        response['session_id'] = session_id
        
        return JsonResponse(response)
        
    except Exception as e:
        logger.error(f"Chat API error: {e}")
        return JsonResponse({
            'type': 'error',
            'message': 'An error occurred processing your request'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def clear_chat_history(request):
    """Clear chat history for current session"""
    session_id = get_or_create_session_id(request)
    
    from .memory import get_memory
    memory = get_memory()
    memory.clear_session(session_id)
    
    return JsonResponse({
        'success': True,
        'message': 'Chat history cleared'
    })


@require_http_methods(["GET"])
def chat_history(request):
    """Get chat history for current session"""
    session_id = get_or_create_session_id(request)
    
    from .memory import get_memory
    memory = get_memory()
    history = memory.get_history(session_id)
    
    return JsonResponse({
        'session_id': session_id,
        'history': history
    })


@csrf_exempt
@require_http_methods(["POST"])
def rebuild_embeddings(request):
    """
    Admin endpoint to rebuild product embeddings.
    Requires admin authentication.
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'message': 'Admin authentication required'
        }, status=403)
    
    try:
        from catalog.models import Product
        from .embeddings import get_product_store
        
        store = get_product_store()
        products = Product.objects.filter(is_active=True)
        store.rebuild_index(products)
        
        return JsonResponse({
            'success': True,
            'message': f'Rebuilt embeddings for {products.count()} products'
        })
        
    except Exception as e:
        logger.error(f"Failed to rebuild embeddings: {e}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def rebuild_faq_index(request):
    """
    Admin endpoint to rebuild FAQ index.
    Requires admin authentication.
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'message': 'Admin authentication required'
        }, status=403)
    
    try:
        from .rag_pipeline import rebuild_faq_index
        rebuild_faq_index()
        
        return JsonResponse({
            'success': True,
            'message': 'FAQ index rebuilt successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to rebuild FAQ index: {e}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@require_http_methods(["GET"])
def chatbot_status(request):
    """Check chatbot status and configuration"""
    import os
    
    status = {
        'operational': True,
        'features': {
            'product_search': True,
            'semantic_search': False,
            'cart_operations': True,
            'order_tracking': True,
            'faq': True,
            'langchain_agent': False
        }
    }
    
    # Check if embeddings are available
    try:
        from .embeddings import get_product_store
        store = get_product_store()
        if store.index and store.index.ntotal > 0:
            status['features']['semantic_search'] = True
            status['embeddings_count'] = store.index.ntotal
    except:
        pass
    
    # Check if LangChain/OpenAI is configured
    if os.environ.get('OPENAI_API_KEY'):
        status['features']['langchain_agent'] = True
    
    return JsonResponse(status)
