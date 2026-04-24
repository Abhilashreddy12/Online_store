# Voice Bot - API Reference

## Endpoint: /api/voice-query/

### Method: POST

Process a voice query and get intelligent response.

#### Request Format

**Content-Type:** `multipart/form-data`

**Required Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `audio` | File | Audio file (mp3, wav, ogg, m4a, flac). Max 25MB |

**Optional Fields:**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `language` | String | 'en' | Language code (e.g., 'en', 'es', 'hi', 'fr') |
| `include_audio_response` | String | 'false' | 'true' or 'false' - Include TTS audio response |

#### cURL Examples

**Basic Usage:**
```bash
curl -X POST http://localhost:8000/api/voice-query/ \
  -F "audio=@recording.wav"
```

**With Options:**
```bash
curl -X POST http://localhost:8000/api/voice-query/ \
  -F "audio=@recording.wav" \
  -F "language=en" \
  -F "include_audio_response=true"
```

**Spanish Query with TTS:**
```bash
curl -X POST http://localhost:8000/api/voice-query/ \
  -F "audio=@recording.wav" \
  -F "language=es" \
  -F "include_audio_response=true"
```

#### Python Examples

**Simple Query:**
```python
import requests

with open('audio.wav', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/voice-query/',
        files={'audio': f}
    )
    print(response.json())
```

**With All Options:**
```python
import requests

with open('audio.wav', 'rb') as f:
    files = {'audio': f}
    data = {
        'language': 'en',
        'include_audio_response': 'true'
    }
    
    response = requests.post(
        'http://localhost:8000/api/voice-query/',
        files=files,
        data=data
    )
    
    result = response.json()
    print(f"Intent: {result['intent']}")
    print(f"Response: {result['response']}")
    if 'response_audio_url' in result:
        print(f"Audio: {result['response_audio_url']}")
```

**JavaScript (Fetch):**
```javascript
const audioFile = document.getElementById('audio-input').files[0];

const formData = new FormData();
formData.append('audio', audioFile);
formData.append('language', 'en');
formData.append('include_audio_response', 'false');

fetch('/api/voice-query/', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => {
    console.log('Intent:', data.intent);
    console.log('Response:', data.response);
    console.log('Processing Time:', data.processing_time_ms, 'ms');
});
```

**jQuery:**
```javascript
var formData = new FormData();
formData.append('audio', $('#audio-file')[0].files[0]);
formData.append('language', 'en');

$.ajax({
    url: '/api/voice-query/',
    type: 'POST',
    data: formData,
    processData: false,
    contentType: false,
    success: function(data) {
        console.log(data);
    }
});
```

#### Response Format

**Success Response (200):**
```json
{
    "success": true,
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "detected_text": "where is my order",
    "detected_language": "en",
    "intent": "ORDER_TRACKING",
    "confidence": 0.95,
    "response": "Your order ORD-20260422-ABC123 has been shipped. Tracking: TRK123456",
    "data": {
        "orders": [
            {
                "order_number": "ORD-20260422-ABC123",
                "status": "SHIPPED",
                "status_display": "Shipped",
                "total_amount": 5999.0,
                "created_at": "2026-04-20",
                "shipped_date": "2026-04-22",
                "tracking_number": "TRK123456",
                "carrier": "DHL"
            }
        ]
    },
    "processing_time_ms": 2341
}
```

**Error Response (400):**
```json
{
    "success": false,
    "error": "No audio file provided",
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Server Error Response (500):**
```json
{
    "success": false,
    "error": "Internal server error: [error details]",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "processing_time_ms": 1234
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | Boolean | True if request succeeded |
| `session_id` | String | Unique identifier for this session |
| `detected_text` | String | Transcribed text from audio |
| `detected_language` | String | Detected language code |
| `intent` | String | Classified intent (ORDER_TRACKING, PRODUCT_SEARCH, etc.) |
| `confidence` | Float | Confidence score (0-1) |
| `response` | String | Natural language response |
| `data` | Object | Intent-specific data (orders, products, etc.) |
| `response_audio_url` | String | (Optional) URL to TTS audio response |
| `processing_time_ms` | Integer | Total processing time in milliseconds |
| `error` | String | (Error responses only) Error message |

#### Intent-Specific Response Data

**ORDER_TRACKING:**
```json
"data": {
    "orders": [
        {
            "order_number": "ORD-20260422-ABC123",
            "status": "SHIPPED",
            "status_display": "Shipped",
            "payment_status": "Paid",
            "total_amount": 5999.0,
            "created_at": "2026-04-20",
            "shipped_date": "2026-04-22",
            "delivered_date": null,
            "tracking_number": "TRK123456",
            "carrier": "DHL"
        }
    ]
}
```

**PRODUCT_SEARCH:**
```json
"data": {
    "products": [
        {
            "name": "Premium Cotton T-Shirt",
            "price": 499.0,
            "category": "T-Shirts",
            "brand": "CoolBrand",
            "in_stock": true,
            "short_description": "Premium quality..."
        }
    ],
    "total_found": 12
}
```

**PAYMENT_ISSUE:**
```json
"data": {
    "support_email": "support@madiriclet.com",
    "issue_type": "payment"
}
```

**RETURN_REQUEST:**
```json
"data": {
    "return_window_days": 30,
    "refund_processing_days": "5-7",
    "support_email": "support@madiriclet.com"
}
```

---

## Endpoint: /api/voice-query/history/

### Method: GET

Retrieve voice query history for authenticated user.

#### Parameters

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | Integer | 20 | Results per page (max 100) |
| `offset` | Integer | 0 | Pagination offset |

#### Examples

**Get recent queries:**
```bash
curl "http://localhost:8000/api/voice-query/history/" \
  -H "Cookie: sessionid=YOUR_SESSION_ID"
```

**Get with pagination:**
```bash
curl "http://localhost:8000/api/voice-query/history/?limit=10&offset=20" \
  -H "Cookie: sessionid=YOUR_SESSION_ID"
```

**Python:**
```python
import requests

response = requests.get(
    'http://localhost:8000/api/voice-query/history/',
    params={'limit': 10, 'offset': 0},
    cookies={'sessionid': 'YOUR_SESSION_ID'}
)

result = response.json()
print(f"Total queries: {result['pagination']['total_count']}")
for query in result['results']:
    print(f"- {query['created_at']}: {query['intent']} ({query['confidence']:.0%})")
```

#### Response Format

```json
{
    "success": true,
    "results": [
        {
            "id": 1,
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "transcribed_text": "where is my order",
            "intent": "ORDER_TRACKING",
            "confidence": 0.95,
            "response": "Your order has been shipped",
            "created_at": "2026-04-22T10:30:00Z",
            "processing_time_ms": 2341
        }
    ],
    "pagination": {
        "limit": 20,
        "offset": 0,
        "total_count": 125
    }
}
```

#### Errors

**Authentication Required (401):**
```json
{
    "success": false,
    "error": "Authentication required"
}
```

**Invalid Parameters (400):**
```json
{
    "success": false,
    "error": "Invalid pagination parameters"
}
```

---

## Endpoint: /api/voice-query/stats/

### Method: GET

Get voice query statistics for authenticated user (last 30 days).

#### Examples

```bash
curl "http://localhost:8000/api/voice-query/stats/" \
  -H "Cookie: sessionid=YOUR_SESSION_ID"
```

**Python:**
```python
import requests

response = requests.get(
    'http://localhost:8000/api/voice-query/stats/',
    cookies={'sessionid': 'YOUR_SESSION_ID'}
)

stats = response.json()['stats']
print(f"Total queries: {stats['total_queries_30d']}")
print(f"Avg confidence: {stats['avg_confidence']:.1%}")
print(f"Avg processing: {stats['avg_processing_time_ms']}ms")
```

#### Response Format

```json
{
    "success": true,
    "stats": {
        "total_queries_30d": 42,
        "avg_confidence": 0.856,
        "avg_processing_time_ms": 2145,
        "intent_distribution": [
            {
                "intent": "ORDER_TRACKING",
                "count": 18
            },
            {
                "intent": "PRODUCT_SEARCH",
                "count": 15
            },
            {
                "intent": "GENERAL_QUERY",
                "count": 6
            },
            {
                "intent": "PAYMENT_ISSUE",
                "count": 3
            }
        ]
    }
}
```

---

## Supported Languages

Whisper supports transcription and translation for:
- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Dutch (nl)
- Russian (ru)
- Chinese (zh)
- Japanese (ja)
- Korean (ko)
- Hindi (hi)
- And 95+ more languages

### Usage

Specify language in request:
```bash
curl -X POST http://localhost:8000/api/voice-query/ \
  -F "audio=@spanish_audio.wav" \
  -F "language=es"
```

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (validation error) |
| 401 | Unauthorized (authentication required) |
| 500 | Internal server error |

---

## Rate Limiting (Future)

Currently no rate limiting. Production deployment should implement:
- Per-user limits (e.g., 100 queries/hour)
- Per-IP limits (e.g., 1000 queries/hour)
- Per-session limits

---

## Best Practices

1. **Handle errors gracefully** - Check `success` field before using `data`
2. **Cache results** - Session ID enables conversation context
3. **Optimize audio** - Shorter audio clips process faster
4. **Monitor performance** - Track `processing_time_ms`
5. **Batch requests** - Use history API for analytics, not frequent checks

---

## Webhooks (Future)

Future versions may support webhooks for:
- Async processing
- Real-time updates
- Integration with external systems

---

## Changelog

### v1.0.0 (Initial Release)
- ✅ Speech-to-text (Whisper)
- ✅ Intent classification (Rule-based)
- ✅ Business logic handlers
- ✅ Text-to-speech (gTTS)
- ✅ Query history
- ✅ Statistics API

### v1.1.0 (Planned)
- [ ] ML-based intent classification
- [ ] Rate limiting
- [ ] Webhooks
- [ ] Real-time streaming
- [ ] Conversation context

---

## Support

For issues or questions:
1. Check admin dashboard: `/admin/voice_bot/`
2. Review logs in VoiceQueryLog
3. Check documentation: `VOICE_BOT_IMPLEMENTATION.md`
4. Test queries manually in shell: `python manage.py shell`
