# Voice Bot - System Architecture & Data Flow

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐  │
│  │  Web Browser     │    │  Mobile App      │    │  API Client  │  │
│  │  (JavaScript)    │    │  (React Native)  │    │  (Python)    │  │
│  └────────┬─────────┘    └────────┬─────────┘    └──────┬───────┘  │
│           │ Audio Recording        │ Audio Stream       │ Audio File│
│           └────────────┬───────────┴──────────────────────┘          │
└────────────────────────┼──────────────────────────────────────────────┘
                         │ POST /api/voice-query/
                         │ (multipart/form-data)
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DJANGO REQUEST HANDLER                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  views.py - voice_query_view()                              │   │
│  │  ├─ Parse request (audio file, language)                   │   │
│  │  ├─ Validate audio file (size, format)                     │   │
│  │  ├─ Create session_id (UUID)                               │   │
│  │  └─ Record start_time for metrics                          │   │
│  └─────────────┬───────────────────────────────────────────────┘   │
└────────────────┼──────────────────────────────────────────────────────┘
                 │
        ┌────────┴────────┬────────────┬─────────────┐
        │                 │            │             │
        ▼                 ▼            ▼             ▼
    ┌──────────┐     ┌─────────┐  ┌────────┐  ┌──────────┐
    │  STT     │     │ Intent  │  │ TTS    │  │ Database │
    │ Layer    │     │ Layer   │  │ Layer  │  │ Layer    │
    └──────────┘     └─────────┘  └────────┘  └──────────┘
        │                 │            │             │
        ▼                 ▼            ▼             ▼
    ┌──────────┐     ┌─────────┐  ┌────────┐  ┌──────────┐
    │stt.py    │     │intent.py│  │tts.py  │  │models.py │
    │          │     │         │  │        │  │          │
    │Whisper   │     │Rule-    │  │gTTS    │  │Voice     │
    │Model     │     │based    │  │Engine  │  │Query     │
    │(Singleton)     │Classifier   │(opt)  │  │VoiceQuery│
    └────┬─────┘     └────┬────┘  └───┬────┘  │Log       │
         │                │           │       │          │
         │ Text           │ Intent    │ Audio │ Save     │
         │ Confidence     │ Confidence│ URL   │ Audit    │
         └────┬───────────┴───────────┴───────┴─────────┐
              │                                         │
              ▼                                         ▼
         ┌────────────┐                         ┌──────────────┐
         │services.py │                         │ Database     │
         │            │                         │              │
         │VoiceSvc    │────────────────────────▶│ VoiceQuery   │
         │Handler     │                         │ VoiceQueryLog│
         │            │◀────────────────────────│              │
         │├─ Get user │      User Data          └──────────────┘
         │├─ Query DB │
         │└─ Generate │
         │  Response  │
         └────┬───────┘
              │
        ┌─────┼─────┬────────┬──────────┐
        │     │     │        │          │
        ▼     ▼     ▼        ▼          ▼
    ┌──────────────────────────────────────────┐
    │   Integration with Django Apps           │
    │                                          │
    │  ├─ Orders App ─────────────────────┐   │
    │  │  Order.objects.filter()           │   │
    │  │  Order status, tracking          │   │
    │  │                                   │   │
    │  ├─ Catalog App ────────────────────┐   │
    │  │  Product.objects.filter()         │   │
    │  │  Search, categories               │   │
    │  │                                   │   │
    │  ├─ Customers App ───────────────────┐   │
    │  │  User association, privacy        │   │
    │  │                                   │   │
    │  └───────────────────────────────────┘   │
    └──────────┬───────────────────────────────┘
               │
               ▼
        ┌──────────────────┐
        │ Response Data    │
        │                  │
        │ {'response': .., │
        │  'data': ..,     │
        │  'intent': ..,   │
        │  'confidence': .}│
        └──────┬───────────┘
               │
               ▼ JSON Serialization
        ┌──────────────────────┐
        │ HTTP Response (200)  │
        └──────┬───────────────┘
               │
               ▼
    ┌──────────────────────────────────┐
    │ Return to Client                 │
    │                                  │
    │ {                                │
    │   "success": true,               │
    │   "detected_text": "...",        │
    │   "intent": "ORDER_TRACKING",    │
    │   "confidence": 0.95,            │
    │   "response": "...",             │
    │   "data": {...},                 │
    │   "processing_time_ms": 2341     │
    │ }                                │
    └──────────────────────────────────┘
```

## 🔄 Intent Classification Flow

```
┌─────────────────────────────┐
│ Transcribed Text            │
│ "where is my order"         │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ intent.classify(text)               │
└────────────┬────────────────────────┘
             │
             ▼
    ┌────────────────────┐
    │ Score Calculation  │
    │                    │
    │ For each intent:   │
    │ ├─ Check phrases   │
    │ ├─ Check keywords  │
    │ └─ Apply weight    │
    │                    │
    │ Results:           │
    │ ORDER_TRACKING  → 0.92
    │ PRODUCT_SEARCH  → 0.15
    │ PAYMENT_ISSUE   → 0.08
    │ GENERAL_QUERY   → 0.05
    │ ...             → ...
    └────────┬───────────┘
             │
             ▼
    ┌─────────────────────┐
    │ Sort & Select       │
    │                     │
    │ Top Intent:         │
    │ ORDER_TRACKING      │
    │ (confidence: 0.92)  │
    │                     │
    │ Top 3 Candidates:   │
    │ [ORDER_TRACKING:0.92│
    │  PRODUCT_SEARCH:0.15│
    │  PAYMENT_ISSUE:0.08]│
    └──────────┬──────────┘
               │
               ▼
    ┌────────────────────────┐
    │ Return Result          │
    │ (intent, confidence,   │
    │  candidates)           │
    └────────────────────────┘
```

## 💾 Data Flow - Order Tracking

```
┌──────────────────────┐
│ User Query           │
│ "where's my order"   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────┐
│ STT Process              │
│ Whisper transcription    │
│ Output: "where is my... "│
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ Intent Classification    │
│ intent = ORDER_TRACKING  │
│ confidence = 0.95        │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Service Handler                      │
│ services.handle_order_tracking()     │
└──────────┬──────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Database Query                       │
│                                      │
│ Order.objects.filter(                │
│     customer=user                    │
│ ).order_by('-created_at')[:5]        │
└──────────┬──────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Order Data Retrieved                 │
│                                      │
│ Order {                              │
│   order_number: "ORD-20260422-...",  │
│   status: "SHIPPED",                 │
│   tracking_number: "TRK123456",      │
│   delivered_at: null,                │
│   total_amount: 5999.00,             │
│   ...                                │
│ }                                    │
└──────────┬──────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Response Generation                  │
│                                      │
│ "Your order ORD-... has been       │
│  shipped. Tracking: TRK123456"       │
└──────────┬──────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ TTS Processing (Optional)            │
│ text_to_speech(response_text)        │
│ Output: audio_bytes                  │
└──────────┬──────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Database Save                        │
│                                      │
│ VoiceQuery.create(                   │
│   user=user,                         │
│   transcribed_text="...",            │
│   intent="ORDER_TRACKING",           │
│   confidence_score=0.95,             │
│   response_message="...",            │
│   processing_time_ms=2341            │
│ )                                    │
└──────────┬──────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Return JSON Response                 │
│                                      │
│ {                                    │
│   "success": true,                   │
│   "detected_text": "where is...",    │
│   "intent": "ORDER_TRACKING",        │
│   "confidence": 0.95,                │
│   "response": "Your order...",       │
│   "data": {                          │
│     "orders": [{...}]                │
│   },                                 │
│   "processing_time_ms": 2341         │
│ }                                    │
└──────────────────────────────────────┘
```

## 🔐 Security & Error Handling Flow

```
┌─────────────────────────┐
│ Incoming Request        │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Validation Layer                │
│                                 │
│ ├─ Audio file exists?           │
│ │  NO → 400 Error               │
│ │                               │
│ ├─ File size < 25MB?            │
│ │  NO → 400 Error               │
│ │                               │
│ ├─ File format valid?           │
│ │  NO → 400 Error               │
│ │                               │
│ └─ OK → Continue                │
└────────────┬────────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ STT Processing                 │
│                                │
│ Try:                           │
│   transcribe()                 │
│ Except:                        │
│   log_error()                  │
│   return error_response()      │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ Intent Classification          │
│                                │
│ Try:                           │
│   classify_intent()            │
│ Except:                        │
│   default to UNKNOWN           │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ Service Handler                │
│                                │
│ Try:                           │
│   handle_query()               │
│ Except:                        │
│   fallback_response()          │
│   log_error()                  │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ Database Save                  │
│                                │
│ Try:                           │
│   VoiceQuery.create()          │
│ Except:                        │
│   log_error()                  │
│   return generic error         │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ Return Response                │
│                                │
│ IF success:                    │
│   HTTP 200 + JSON data         │
│ IF error:                      │
│   HTTP 400/500 + error message │
└────────────────────────────────┘
```

## 📊 Database Schema

```
┌─────────────────────────────────┐
│ VoiceQuery                      │
├─────────────────────────────────┤
│ id (PK)                         │
│ user_id (FK) → User             │
│ session_id (VARCHAR 100)        │
│ audio_file (FileField)          │
│ audio_duration (FLOAT)          │
│ transcribed_text (TEXT)         │
│ detected_language (VARCHAR 10)  │
│ intent (VARCHAR 50)             │ ◄── INDEX
│ confidence_score (FLOAT)        │
│ confidence_level (VARCHAR 10)   │
│ response_message (TEXT)         │
│ response_audio (FileField)      │
│ error_message (TEXT)            │
│ processing_time_ms (INT)        │
│ created_at (DATETIME)           │ ◄── INDEX
│ updated_at (DATETIME)           │
│                                 │
│ INDEXES:                        │
│ - (user_id, -created_at)        │
│ - (intent, created_at)          │
│ - (session_id)                  │
└─────────────────────────────────┘
         │
         │ 1:1
         │
         ▼
┌─────────────────────────────────┐
│ VoiceQueryLog                   │
├─────────────────────────────────┤
│ id (PK)                         │
│ voice_query_id (FK) ◄──────┐    │
│ stt_model (VARCHAR 50)      │    │
│ stt_model_size (VARCHAR 20) │    │
│ intent_classifier (VARCHAR) │    │
│ intent_candidates (JSON)    │    │
│ raw_response (JSON)         │    │
│ created_at (DATETIME)       │    │
└─────────────────────────────────┘
```

## 🚀 Deployment Architecture

```
┌──────────────────────────────────────────────┐
│         PRODUCTION ENVIRONMENT               │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │ Load Balancer / CDN                  │   │
│  │ (Optional: Cloudflare, AWS)          │   │
│  └──────────────┬───────────────────────┘   │
│                 │                            │
│  ┌──────────────▼────────────────────────┐  │
│  │ Django Application Servers            │  │
│  │ (Gunicorn + Nginx)                    │  │
│  │                                       │  │
│  │ ├─ Instance 1                        │  │
│  │ ├─ Instance 2                        │  │
│  │ └─ Instance 3 (Horizontal scaling)   │  │
│  └──────────────┬────────────────────────┘  │
│                 │                            │
│  ┌──────────────▼────────────────────────┐  │
│  │ Shared Resources                      │  │
│  │                                       │  │
│  │ ├─ PostgreSQL Database                │  │
│  │ │  (Replica for read scaling)         │  │
│  │ │                                     │  │
│  │ ├─ Redis Cache                        │  │
│  │ │  (Session, query caching)          │  │
│  │ │                                     │  │
│  │ ├─ Cloudinary/S3                      │  │
│  │ │  (Audio file storage)               │  │
│  │ │                                     │  │
│  │ └─ Whisper Model                      │  │
│  │    (Shared, maybe GPU)                │  │
│  └───────────────────────────────────────┘  │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │ Monitoring & Logging                 │   │
│  │                                       │  │
│  │ ├─ Prometheus (Metrics)               │  │
│  │ ├─ ELK Stack (Logs)                   │  │
│  │ ├─ Sentry (Error tracking)            │  │
│  │ └─ New Relic (APM)                    │  │
│  └───────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

## 📈 Scalability Considerations

```
┌─────────────────────────────────────────┐
│ CURRENT (Single Instance)               │
│                                         │
│ Capacity:                               │
│ - ~100 concurrent users                │
│ - ~50 requests/minute                  │
│ - Whisper model: ~500MB RAM            │
│ - Database: Single instance            │
└─────────────────────────────────────────┘
                  ▼
           Scale Up Plan
                  ▼
┌─────────────────────────────────────────┐
│ FUTURE (Multi-Instance)                 │
│                                         │
│ Improvements:                           │
│ ├─ Load balancer                        │
│ ├─ Multiple Django instances            │
│ ├─ Database replication                 │
│ ├─ Redis caching                        │
│ ├─ Celery for async STT                 │
│ ├─ GPU for Whisper                      │
│ └─ CDN for audio files                  │
│                                         │
│ Capacity:                               │
│ - ~1000+ concurrent users               │
│ - ~500 requests/minute                  │
│ - Distributed Whisper models            │
│ - Replicated database                   │
└─────────────────────────────────────────┘
```

---

This architecture ensures:
- ✅ **Modularity**: Each component independent
- ✅ **Scalability**: Ready for horizontal scaling
- ✅ **Reliability**: Error handling at every layer
- ✅ **Maintainability**: Clear separation of concerns
- ✅ **Performance**: Optimized queries and caching
- ✅ **Security**: Input validation and error handling
