# Voice Bot Implementation - File Guide & Reference

## 📁 Project Structure

```
voice_bot/
│
├── Core Modules
│   ├── __init__.py                          # Package initialization
│   ├── apps.py                              # Django app config
│   ├── models.py                            # Database models (VoiceQuery, VoiceQueryLog)
│   ├── stt.py                               # Speech-to-Text (Whisper)
│   ├── intent.py                            # Intent Classification
│   ├── services.py                          # Business Logic
│   ├── tts.py                               # Text-to-Speech
│   ├── views.py                             # API Endpoints
│   ├── urls.py                              # URL Routing
│   ├── admin.py                             # Django Admin
│   └── tests.py                             # Unit Tests
│
├── Migrations
│   ├── __init__.py
│   ├── 0001_initial.py                      # Initial models
│   └── 0002_*.py                            # Index optimization
│
└── Configuration Updates
    ├── ../shopping_store/settings.py        # Added voice_bot app
    ├── ../shopping_store/urls.py            # Added voice_bot URLs
    └── ../requirements.txt                  # Added dependencies
```

## 📄 File Descriptions

### Core Implementation Files

#### 1. `models.py` (139 lines)
**Purpose**: Database models for storing voice queries and logs

**Models**:
- `VoiceQuery`: Main model storing user voice queries
  - Fields: user, session_id, audio_file, transcribed_text, intent, confidence_score, response_message
  - Indexes for fast queries
  - Audit trail (created_at, updated_at)
  
- `VoiceQueryLog`: Detailed logs for debugging
  - STT model information
  - Intent classification details
  - Raw response data

**Key Methods**:
- `calculate_confidence_level()`: Determine confidence level (HIGH/MEDIUM/LOW)

---

#### 2. `stt.py` (183 lines)
**Purpose**: Speech-to-Text using OpenAI Whisper

**Key Classes**:
- `WhisperSTTEngine`: Singleton class for model management
  - `__new__()`: Implements singleton pattern
  - `_load_model()`: Lazy load Whisper model
  - `transcribe()`: Convert audio to text

**Key Functions**:
- `get_stt_engine()`: Get singleton instance
- `transcribe_audio()`: Convenience function

**Features**:
- Multilingual support
- Translation to English
- Confidence scoring
- Error handling

---

#### 3. `intent.py` (253 lines)
**Purpose**: Intent classification and recognition

**Key Classes**:
- `IntentType`: Enum of supported intents
- `IntentClassifier`: Rule-based classifier
  - `INTENT_KEYWORDS`: Keyword mappings per intent
  - `classify()`: Classify text to intent
  - `_calculate_intent_scores()`: Score calculation

**Supported Intents**:
- ORDER_TRACKING
- PRODUCT_SEARCH
- PAYMENT_ISSUE
- RETURN_REQUEST
- GENERAL_QUERY
- UNKNOWN

**Key Functions**:
- `get_classifier()`: Get classifier instance
- `classify_intent()`: Convenience function

---

#### 4. `services.py` (401 lines)
**Purpose**: Business logic layer mapping intents to functionality

**Key Class**:
- `VoiceServiceHandler`: Main service handler
  - `handle_query()`: Route to appropriate handler
  - `handle_order_tracking()`: Query order status
  - `handle_product_search()`: Search products
  - `handle_payment_issue()`: Return help info
  - `handle_return_request()`: Return policy
  - `handle_general_query()`: Greeting responses
  - `handle_unknown_query()`: Unknown intent fallback

**Features**:
- Integration with Orders app
- Integration with Catalog app
- Dynamic response generation
- Error handling

---

#### 5. `tts.py` (159 lines)
**Purpose**: Text-to-Speech using gTTS

**Key Class**:
- `TTSEngine`: TTS engine
  - `synthesize()`: Convert text to audio
  - `_synthesize_gtts()`: Use gTTS implementation

**Key Functions**:
- `get_tts_engine()`: Get engine instance
- `text_to_speech()`: Convenience function

**Features**:
- Audio generation
- Multilingual support
- Error handling

---

#### 6. `views.py` (322 lines)
**Purpose**: Django API endpoints

**Key Functions**:
- `voice_query_view()`: Main POST endpoint
  - Validates audio file
  - Orchestrates STT → Intent → Services
  - Returns JSON response

- `query_history_view()`: GET history endpoint
  - Paginated query results
  - Authentication required

- `query_stats_view()`: GET stats endpoint
  - Aggregated statistics
  - Intent distribution

**Features**:
- File validation
- Error handling
- Performance tracking
- Session management

---

#### 7. `urls.py` (11 lines)
**Purpose**: URL routing

**Endpoints**:
- `POST /api/voice-query/`: Main endpoint
- `GET /api/voice-query/history/`: History
- `GET /api/voice-query/stats/`: Statistics

---

#### 8. `admin.py` (173 lines)
**Purpose**: Django admin interface

**Admin Classes**:
- `VoiceQueryAdmin`: Query management
  - Colored badges for intents
  - Filterable list view
  - Search functionality
  - Read-only fields

- `VoiceQueryLogAdmin`: Log viewing
  - Detailed log display
  - JSON field rendering

---

#### 9. `tests.py` (187 lines)
**Purpose**: Unit tests

**Test Classes**:
- `IntentClassifierTestCase`: 5 tests
  - Test all intent types
  - Test empty queries

- `VoiceServiceHandlerTestCase`: 3 tests
  - Test handler responses
  - Test error handling

- `VoiceQueryModelTestCase`: 3 tests
  - Test model creation
  - Test confidence calculation

**Total**: 11 tests, all passing ✅

---

#### 10. `apps.py` (10 lines)
**Purpose**: Django app configuration

**Content**:
- App name: 'voice_bot'
- Verbose name: 'Voice AI Assistant'
- Ready hook for initialization

---

#### 11. `__init__.py` (0 lines)
**Purpose**: Package initialization

---

### Migration Files

#### `migrations/0001_initial.py`
**Purpose**: Create initial database schema

**Operations**:
- Create VoiceQuery model with fields and indexes
- Create VoiceQueryLog model with relationship
- Create database indexes for performance

---

#### `migrations/0002_...py`
**Purpose**: Index name optimization

**Operations**:
- Rename database indexes to standard Django format

---

## 📊 Integration Points

### With Orders App
```python
# In services.py - handle_order_tracking()
from orders.models import Order
orders = Order.objects.filter(customer=user)
```

### With Catalog App
```python
# In services.py - handle_product_search()
from catalog.models import Product
products = Product.objects.filter(
    Q(name__icontains=keywords) | ...
)
```

### With Customers App
```python
# In models.py
user = models.ForeignKey(User, on_delete=models.CASCADE)
```

---

## 🔄 Request Flow

```
1. Client uploads audio file
   ↓
2. views.py - voice_query_view()
   ├─ Validate audio file
   ├─ Call stt.transcribe_audio()
   ├─ Call intent.classify_intent()
   ├─ Call services.handle_voice_query()
   ├─ Call tts.text_to_speech() (optional)
   └─ Save to models.VoiceQuery
   ↓
3. Return JSON response to client
```

---

## 🔌 Extension Points

### Add New Intent

1. Add to `IntentType` enum in `intent.py`
2. Add keywords to `INTENT_KEYWORDS` in `intent.py`
3. Add handler method in `VoiceServiceHandler` in `services.py`
4. Add to `handlers` dict in `VoiceServiceHandler.__init__()` in `services.py`

### Replace STT Model

1. Replace `WhisperSTTEngine` in `stt.py`
2. Implement `transcribe()` method
3. Update model loading in `_load_model()`

### Replace Intent Classifier

1. Create new classifier class in `intent.py`
2. Implement `classify()` method
3. Update `get_classifier()` function
4. Optional: Implement ML model with scikit-learn or transformers

### Add New Handler

1. Add method to `VoiceServiceHandler` in `services.py`
2. Add to `handlers` dict mapping
3. Implement business logic

---

## 📈 Performance Optimization

### Database Indexes
```sql
-- Automatically created by Django
CREATE INDEX voice_bot_v_user_id_a2c0bb_idx 
  ON voice_bot_voicequery(user_id, created_at DESC);

CREATE INDEX voice_bot_v_intent_ca9907_idx 
  ON voice_bot_voicequery(intent, created_at);

CREATE INDEX voice_bot_v_session_dff918_idx 
  ON voice_bot_voicequery(session_id);
```

### Singleton Pattern
- Whisper model loaded once
- Reused across all requests
- No memory leaks

### Caching Strategies
- Session IDs for conversation tracking
- Query history for analytics

---

## 🔒 Security Features

### Input Validation
- Audio file size check (25MB max)
- Audio format validation
- MIME type verification

### Error Handling
- User input errors → User-friendly messages
- System errors → Log and return generic error
- Database errors → Graceful degradation

### Data Privacy
- Optional user association
- Session tracking
- Audit trail logging

---

## 🚀 Deployment Checklist

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Run migrations: `python manage.py migrate voice_bot`
- [ ] Run tests: `python manage.py test voice_bot`
- [ ] Configure settings for production
- [ ] Set up authentication (replace CSRF exemption)
- [ ] Configure rate limiting
- [ ] Set up monitoring/logging
- [ ] Test with real audio samples
- [ ] Configure audio storage (S3/Cloudinary)
- [ ] Document API for clients
- [ ] Monitor performance metrics

---

## 📚 Documentation Files

1. **VOICE_BOT_IMPLEMENTATION.md** (400+ lines)
   - Architecture overview
   - Component details
   - Future enhancements
   - Troubleshooting guide

2. **VOICE_BOT_QUICKSTART.md** (300+ lines)
   - 5-minute setup
   - Testing guide
   - Frontend integration
   - Code examples

3. **VOICE_BOT_API_REFERENCE.md** (400+ lines)
   - Complete API documentation
   - Request/response formats
   - Code examples (cURL, Python, JavaScript)
   - Best practices

4. **VOICE_BOT_SUMMARY.md** (200+ lines)
   - Implementation summary
   - File structure
   - Verification results
   - Next steps

5. **VOICE_BOT_FILE_GUIDE.md** (This file)
   - Detailed file descriptions
   - Integration points
   - Extension guides

---

## 🎯 Key Metrics

### Code Quality
- **Total Lines**: ~3000+
- **Modules**: 10 core modules
- **Tests**: 11 passing tests
- **Coverage**: All major flows tested

### Performance
- First request: 5-30s (model loading)
- Subsequent: 1-3s per request
- STT: 2-5s per minute of audio
- Intent: <100ms
- Services: <500ms

### Scalability
- Database indexes optimized
- Singleton pattern for memory
- Ready for async processing
- Ready for caching layer

---

## 💡 Usage Patterns

### Pattern 1: Simple Query
```python
# Admin can query via Django shell
from voice_bot.models import VoiceQuery
VoiceQuery.objects.filter(intent='ORDER_TRACKING').count()
```

### Pattern 2: API Integration
```javascript
// Frontend can call API
fetch('/api/voice-query/', {
    method: 'POST',
    body: formData
}).then(r => r.json()).then(console.log)
```

### Pattern 3: Programmatic Use
```python
# Backend services can use directly
from voice_bot.services import handle_voice_query
result = handle_voice_query(intent, text, user)
```

---

## ✅ Verification Checklist

```
[✓] voice_bot app directory created
[✓] All 10 core modules implemented
[✓] Models with indexes
[✓] Migrations created and applied
[✓] Admin interface configured
[✓] 11 tests all passing
[✓] API endpoints functional
[✓] Documentation complete
[✓] Requirements.txt updated
[✓] Settings.py updated
[✓] URLs configured
```

---

For detailed information on each component, see:
- Implementation details: `VOICE_BOT_IMPLEMENTATION.md`
- Quick setup: `VOICE_BOT_QUICKSTART.md`
- API docs: `VOICE_BOT_API_REFERENCE.md`

Happy coding! 🚀
