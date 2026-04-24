"""
Django REST API views for voice queries

Features:
- Handles audio file upload and processing
- Integrates STT, intent classification, and service layer
- Returns structured JSON responses
- Error handling and validation
- Performance optimization with lazy loading
"""

import logging
import time
import uuid
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import InMemoryUploadedFile

from .models import VoiceQuery, VoiceQueryLog
from .stt import transcribe_audio
from .intent import classify_intent
from .services import handle_voice_query
from .tts import text_to_speech

logger = logging.getLogger(__name__)

# Supported audio formats
SUPPORTED_FORMATS = ['mp3', 'wav', 'ogg', 'm4a', 'flac']
MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25MB


@csrf_exempt  # Only for CORS - implement proper token auth in production
@require_http_methods(["POST"])
def voice_query_view(request):
    """
    Handle voice query requests
    
    POST /api/voice-query/
    
    Request:
    - audio: Audio file (multipart/form-data)
    - language (optional): Language code (default: 'en')
    - include_audio_response (optional): Include TTS response (default: false)
    
    Response:
    {
        "success": bool,
        "detected_text": "user spoken text",
        "intent": "ORDER_TRACKING",
        "confidence": 0.95,
        "response": "Your order status...",
        "data": {...},
        "response_audio_url": "/media/..." (optional),
        "session_id": "uuid",
        "processing_time_ms": 1234,
        "error": "error message" (if failed)
    }
    """
    start_time = time.time()
    session_id = str(uuid.uuid4())
    
    try:
        # Validate request
        if 'audio' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No audio file provided',
                'session_id': session_id
            }, status=400)
        
        audio_file = request.FILES['audio']
        
        # Validate file size
        if audio_file.size > MAX_AUDIO_SIZE:
            return JsonResponse({
                'success': False,
                'error': f'Audio file too large. Maximum size: {MAX_AUDIO_SIZE / 1024 / 1024}MB',
                'session_id': session_id
            }, status=400)
        
        # Validate file format
        file_ext = audio_file.name.split('.')[-1].lower()
        if file_ext not in SUPPORTED_FORMATS:
            return JsonResponse({
                'success': False,
                'error': f'Unsupported audio format. Supported: {", ".join(SUPPORTED_FORMATS)}',
                'session_id': session_id
            }, status=400)
        
        # Get parameters
        language = request.POST.get('language', 'en')
        include_audio_response = request.POST.get('include_audio_response', 'false').lower() == 'true'
        user = request.user if request.user.is_authenticated else None
        
        # Step 1: Speech-to-Text
        logger.info(f"[{session_id}] Starting transcription...")
        stt_result = transcribe_audio(audio_file, language=language)
        
        if not stt_result['success']:
            logger.error(f"[{session_id}] STT failed: {stt_result.get('error')}")
            return JsonResponse({
                'success': False,
                'error': f"Failed to transcribe audio: {stt_result.get('error')}",
                'session_id': session_id
            }, status=400)
        
        detected_text = stt_result['text']
        detected_language = stt_result['language']
        stt_confidence = stt_result['confidence']
        
        logger.info(f"[{session_id}] Transcription successful: '{detected_text}'")
        
        # Step 2: Intent Classification
        logger.info(f"[{session_id}] Classifying intent...")
        intent_result = classify_intent(detected_text)
        
        intent = intent_result['intent']
        intent_confidence = intent_result['confidence']
        candidates = intent_result['candidates']
        
        logger.info(f"[{session_id}] Intent: {intent} (confidence: {intent_confidence:.2f})")
        
        # Step 3: Service Handler
        logger.info(f"[{session_id}] Processing with service handler...")
        service_result = handle_voice_query(intent, detected_text, user)
        
        response_message = service_result.get('response', '')
        service_data = service_result.get('data', {})
        
        # Step 4: Text-to-Speech (optional)
        response_audio_url = None
        if include_audio_response:
            logger.info(f"[{session_id}] Generating audio response...")
            tts_result = text_to_speech(response_message, language=detected_language)
            
            if tts_result['success'] and tts_result.get('audio_data'):
                # Save audio file
                audio_filename = f"response_{session_id}.mp3"
                from django.core.files.base import ContentFile
                audio_content = ContentFile(tts_result['audio_data'])
                response_audio_url = f"/media/voice_responses/{audio_filename}"
        
        # Save to database
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        voice_query = VoiceQuery.objects.create(
            user=user,
            session_id=session_id,
            audio_file=audio_file,
            audio_duration=0,  # Could extract from audio metadata
            transcribed_text=detected_text,
            detected_language=detected_language,
            intent=intent,
            confidence_score=intent_confidence,
            response_message=response_message,
            processing_time_ms=processing_time_ms
        )
        voice_query.calculate_confidence_level()
        voice_query.save()
        
        # Create log entry
        VoiceQueryLog.objects.create(
            voice_query=voice_query,
            stt_model='whisper',
            stt_model_size='base',
            intent_classifier='rule_based',
            intent_candidates=candidates,
            raw_response=service_result
        )
        
        logger.info(f"[{session_id}] Query saved to database")
        
        # Return response
        response_data = {
            'success': True,
            'session_id': session_id,
            'detected_text': detected_text,
            'detected_language': detected_language,
            'intent': intent,
            'confidence': float(intent_confidence),
            'response': response_message,
            'data': service_data,
            'processing_time_ms': processing_time_ms
        }
        
        if response_audio_url:
            response_data['response_audio_url'] = response_audio_url
        
        logger.info(f"[{session_id}] Request completed successfully")
        
        return JsonResponse(response_data)
    
    except Exception as e:
        logger.error(f"[{session_id}] Unexpected error: {str(e)}", exc_info=True)
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return JsonResponse({
            'success': False,
            'error': f"Internal server error: {str(e)}",
            'session_id': session_id,
            'processing_time_ms': processing_time_ms
        }, status=500)


@require_http_methods(["GET"])
def query_history_view(request):
    """
    Get voice query history for authenticated user
    
    GET /api/voice-query/history/
    
    Query parameters:
    - limit: Number of records to return (default: 20)
    - offset: Offset for pagination (default: 0)
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)
    
    try:
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        
        # Ensure reasonable limits
        limit = min(limit, 100)
        
        # Get queries
        queries = VoiceQuery.objects.filter(user=request.user).order_by('-created_at')
        total_count = queries.count()
        
        queries = queries[offset:offset + limit]
        
        # Format results
        results = [
            {
                'id': q.id,
                'session_id': q.session_id,
                'transcribed_text': q.transcribed_text,
                'intent': q.intent,
                'confidence': float(q.confidence_score),
                'response': q.response_message,
                'created_at': q.created_at.isoformat(),
                'processing_time_ms': q.processing_time_ms
            }
            for q in queries
        ]
        
        return JsonResponse({
            'success': True,
            'results': results,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'total_count': total_count
            }
        })
    
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid pagination parameters'
        }, status=400)
    except Exception as e:
        logger.error(f"Query history error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to retrieve query history'
        }, status=500)


@require_http_methods(["GET"])
def query_stats_view(request):
    """
    Get voice query statistics for authenticated user
    
    GET /api/voice-query/stats/
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)
    
    try:
        from django.db.models import Count, Avg
        from datetime import timedelta
        from django.utils import timezone
        
        # Last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        queries = VoiceQuery.objects.filter(
            user=request.user,
            created_at__gte=thirty_days_ago
        )
        
        # Calculate stats
        total_queries = queries.count()
        avg_confidence = queries.aggregate(Avg('confidence_score'))['confidence_score__avg'] or 0
        
        # Intent distribution
        intent_distribution = queries.values('intent').annotate(count=Count('id')).order_by('-count')
        
        # Average processing time
        avg_processing_time = queries.aggregate(Avg('processing_time_ms'))['processing_time_ms__avg'] or 0
        
        return JsonResponse({
            'success': True,
            'stats': {
                'total_queries_30d': total_queries,
                'avg_confidence': float(avg_confidence),
                'avg_processing_time_ms': float(avg_processing_time),
                'intent_distribution': list(intent_distribution),
            }
        })
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error fetching statistics'
        }, status=500)


def voice_bot_streaming_interface(request):
    """
    Render the real-time voice bot streaming interface
    
    GET /voice-bot-streaming/
    
    Returns HTML page with WebSocket client for real-time streaming
    """
    from django.shortcuts import render
    return render(request, 'voice_bot_streaming.html')
