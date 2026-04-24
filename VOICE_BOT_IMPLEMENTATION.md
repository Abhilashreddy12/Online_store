# Voice Bot Architecture & Implementation Guide

## Overview

The **Voice Bot** is a production-ready, modular AI-powered voice assistant integrated into the Madiriclet e-commerce platform. It enables customers to interact with the system using natural language voice queries in any language.

## Architecture

```
┌─────────────────────────────────────────────────┐
│         Client (Web/Mobile)                     │
│         - Audio Recording                       │
│         - Audio Upload (multipart/form-data)    │
└─────────────────┬───────────────────────────────┘
                  │ POST /api/voice-query/
                  ▼
┌─────────────────────────────────────────────────┐
│         Django Views (views.py)                 │
│         - Request Validation                    │
│         - Error Handling                        │
│         - Session Management                    │
└─────────────────┬───────────────────────────────┘
                  │
        ┌─────────┼─────────┐
        │         │         │
        ▼         ▼         ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│  STT     │  │ Intent   │  │ Services │
│ (stt.py) │  │ (intent  │  │(services│
│          │  │  .py)    │  │  .py)    │
│ Whisper  │  │ Rule-    │  │ Business │
│ Model    │  │ based    │  │ Logic    │
└──────────┘  │ Keyword  │  └──────────┘
              │ Matching │
              └──────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│     Django Models (models.py)                   │
│     - VoiceQuery                                │
│     - VoiceQueryLog                             │
│     - Audit Trail & Analytics                   │
└─────────────────────────────────────────────────┘
```

## Key Components

### 1. **Speech-to-Text (stt.py)**
- **Engine**: OpenAI Whisper
- **Singleton Pattern**: Model loaded once, reused across requests
- **Multilingual Support**: Automatic translation to English
- **Features**:
  - Automatic language detection
  - Translation task support
  - Confidence scoring
  - Error handling for invalid/empty audio

**Usage:**
```python
from voice_bot.stt import transcribe_audio

result = transcribe_audio(
    audio_file,
    language='en',
    translate_to_english=True
)
# Returns: {'text': '...', 'language': 'en', 'confidence': 0.95, 'success': True}
```

### 2. **Intent Classification (intent.py)**
- **Type**: Rule-based keyword matching (extensible for ML models)
- **Supported Intents**:
  - `ORDER_TRACKING` - Track order status
  - `PRODUCT_SEARCH` - Search for products
  - `PAYMENT_ISSUE` - Payment problems
  - `RETURN_REQUEST` - Return/exchange requests
  - `GENERAL_QUERY` - General inquiries
  - `UNKNOWN` - Unrecognized queries

**Usage:**
```python
from voice_bot.intent import classify_intent

result = classify_intent("where is my order")
# Returns:
# {
#     'intent': 'ORDER_TRACKING',
#     'confidence': 0.92,
#     'candidates': [...],
#     'description': 'Track your order status'
# }
```

### 3. **Business Logic Layer (services.py)**
- **VoiceServiceHandler**: Routes intents to appropriate handlers
- **Integration Points**:
  - Orders App: Order tracking, status updates
  - Catalog App: Product search, availability
  - Dynamic response generation

**Supported Handlers:**
- `handle_order_tracking()` - Queries order status
- `handle_product_search()` - Searches products
- `handle_payment_issue()` - Returns help info
- `handle_return_request()` - Returns policy info
- `handle_general_query()` - Greeting/help responses

**Usage:**
```python
from voice_bot.services import handle_voice_query

result = handle_voice_query(
    intent='ORDER_TRACKING',
    query_text='where is my order',
    user=request.user
)
# Returns: {'response': '...', 'data': {...}, 'success': True}
```

### 4. **Text-to-Speech (tts.py)**
- **Engine**: gTTS (Google Text-to-Speech)
- **Optional Feature**: Converts response to audio
- **Extensible**: Support for Google Cloud, AWS Polly
- **Supported Languages**: All gTTS supported languages

**Usage:**
```python
from voice_bot.tts import text_to_speech

result = text_to_speech(
    "Your order is on the way",
    language='en'
)
# Returns: {'audio_data': b'...', 'format': 'mp3', 'success': True}
```

### 5. **Django Views (views.py)**
- **Main Endpoint**: `POST /api/voice-query/`
- **Supporting Endpoints**:
  - `GET /api/voice-query/history/` - Query history
  - `GET /api/voice-query/stats/` - Analytics

**Request Example:**
```bash
curl -X POST http://localhost:8000/api/voice-query/ \
  -F "audio=@sample.mp3" \
  -F "language=en" \
  -F "include_audio_response=true"
```

**Response Example:**
```json
{
  "success": true,
  "session_id": "uuid-123",
  "detected_text": "where is my order",
  "intent": "ORDER_TRACKING",
  "confidence": 0.95,
  "response": "Your order ORD-20260422-ABC123 is being shipped.",
  "data": {
    "orders": [
      {
        "order_number": "ORD-20260422-ABC123",
        "status": "SHIPPED",
        "total_amount": 5999.00,
        "tracking_number": "TRK123456789"
      }
    ]
  },
  "processing_time_ms": 2341
}
```

## Performance Optimizations

### 1. **Model Singleton Pattern**
- Whisper model loaded once on first use
- Reused across all requests
- Lazy loading to avoid startup overhead

### 2. **Request Caching**
- Session IDs track unique conversations
- Reduce duplicate processing
- Enable conversation context (future feature)

### 3. **Database Indexing**
- Optimized queries for user, intent, timestamp
- Fast retrieval for analytics

### 4. **Asynchronous Processing (Future)**
- Celery for long-running STT tasks
- Background audio processing
- Real-time streaming support

## Database Models

### VoiceQuery
```
- user: ForeignKey(User)
- session_id: CharField
- audio_file: FileField
- transcribed_text: TextField
- detected_language: CharField
- intent: CharField (choices)
- confidence_score: FloatField
- response_message: TextField
- response_audio: FileField (optional)
- error_message: TextField
- processing_time_ms: IntegerField
- created_at, updated_at: DateTimeField
```

### VoiceQueryLog
```
- voice_query: OneToOneField(VoiceQuery)
- stt_model: CharField
- stt_model_size: CharField
- intent_classifier: CharField
- intent_candidates: JSONField (top-3 intents)
- raw_response: JSONField (complete response)
- created_at: DateTimeField
```

## Admin Interface

Access at `/admin/voice_bot/`:
- **VoiceQuery Admin**: View all queries with filtering, search, and colored badges
- **VoiceQueryLog Admin**: Detailed logs for debugging
- **Dashboard**: Intents, confidence levels, processing times

## Error Handling

The system handles:
- **Empty audio files**: Returns validation error
- **Invalid file formats**: Rejects with supported formats list
- **Transcription failures**: Logs error and returns fallback message
- **Unknown intents**: Routes to general query handler
- **Database errors**: Returns generic error with session ID
- **Service failures**: Graceful degradation

## Extension Points

### Future Enhancements

1. **ML-Based Intent Classification**
   - Replace rule-based with RoBERTa/BERT
   - Fine-tune on e-commerce domain
   - Higher accuracy for ambiguous queries

2. **Multilingual Response Generation**
   - Translate responses based on detected language
   - Support for multiple TTS engines

3. **Real-Time Streaming**
   - WebSocket integration
   - Stream audio while processing
   - Real-time transcription updates

4. **Context Awareness**
   - Multi-turn conversations
   - Session memory
   - User preference tracking

5. **Advanced Analytics**
   - Intent trends
   - Response satisfaction
   - Performance metrics

## Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

Required packages:
- `openai-whisper>=20231117`
- `gtts>=2.3.0`
- `librosa>=0.10.0`
- `soundfile>=0.12.1`

### 2. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### 4. Test the Implementation
```bash
python manage.py test voice_bot
```

## Configuration

### Environment Variables
```bash
# Optional - set default model size (tiny, base, small, medium, large)
WHISPER_MODEL_SIZE=base

# Optional - disable TTS
VOICE_BOT_TTS_ENABLED=true

# Optional - max audio file size (bytes)
VOICE_BOT_MAX_AUDIO_SIZE=26214400
```

### Settings.py
The app is auto-configured in `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    ...
    'voice_bot',
]
```

## Security Considerations

### Current Implementation
- CSRF exempt for API endpoint (allows cross-origin requests)
- File size validation
- Audio format validation

### Production Recommendations
1. **Replace CSRF exemption** with token-based auth:
   - API tokens
   - OAuth 2.0
   - JWT

2. **Rate limiting**:
   - Per-user rate limits
   - Per-IP rate limits
   - Use Django Ratelimit or DRF throttling

3. **Audio storage**:
   - Encrypt audio files at rest
   - Use S3/Cloudinary (already configured)
   - Implement retention policies

4. **Logging & Monitoring**:
   - Monitor error rates
   - Track intent distribution
   - Performance monitoring

## Testing

Run tests:
```bash
python manage.py test voice_bot
```

Test coverage includes:
- Intent classification accuracy
- Service handler responses
- Model creation and validation
- Empty/invalid inputs

## API Documentation

### POST /api/voice-query/

**Request:**
- Content-Type: `multipart/form-data`
- Fields:
  - `audio` (required): Audio file (mp3, wav, ogg, m4a, flac)
  - `language` (optional, default='en'): Language code
  - `include_audio_response` (optional, default=false): Include TTS response

**Response:**
- `success`: Boolean
- `session_id`: Unique session identifier
- `detected_text`: Transcribed text
- `intent`: Classified intent
- `confidence`: Confidence score (0-1)
- `response`: Natural language response
- `data`: Intent-specific data (orders, products, etc.)
- `processing_time_ms`: Total processing time

### GET /api/voice-query/history/

**Parameters:**
- `limit` (optional, default=20): Results per page
- `offset` (optional, default=0): Pagination offset

**Response:**
- `success`: Boolean
- `results`: Array of past queries
- `pagination`: Limit, offset, total_count

### GET /api/voice-query/stats/

**Response:**
- `success`: Boolean
- `stats`: Aggregated statistics
  - `total_queries_30d`: Last 30 days
  - `avg_confidence`: Average confidence
  - `avg_processing_time_ms`: Average processing time
  - `intent_distribution`: Intents breakdown

## Monitoring & Metrics

Track in admin dashboard:
- Total queries processed
- Average confidence scores
- Processing times
- Intent distribution
- Error rates
- User engagement

## Support & Documentation

- Admin interface: `/admin/voice_bot/`
- API endpoint: `/api/voice-query/`
- Models documentation: See models.py docstrings
- Tests: See tests.py for examples

## Troubleshooting

**Q: Whisper model not loading?**
A: Ensure `openai-whisper` is installed: `pip install openai-whisper`

**Q: Audio file too large error?**
A: Max size is 25MB. Split larger files or adjust `MAX_AUDIO_SIZE` in views.py

**Q: Wrong intent classification?**
A: Current system is rule-based. Keywords can be tweaked in `intent.py`. ML models can be added later.

**Q: Database error on query save?**
A: Ensure migrations are applied: `python manage.py migrate`

## Future Roadmap

- [ ] ML-based intent classification (RoBERTa)
- [ ] Multi-language response generation
- [ ] Real-time WebSocket streaming
- [ ] Conversation context tracking
- [ ] Advanced analytics dashboard
- [ ] Integration with chatbot app
- [ ] Voice profile customization
- [ ] A/B testing framework
