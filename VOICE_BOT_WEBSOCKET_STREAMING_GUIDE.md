# Real-Time Voice Bot WebSocket Streaming - Complete Guide

## Overview

This guide provides comprehensive instructions for testing and using the real-time voice bot streaming feature. The system uses WebSockets for bidirectional communication, allowing users to speak queries and receive real-time transcription, intent classification, and responses.

---

## Quick Start (2 minutes)

### 1. Start Development Server
```bash
cd shopping_store
python manage.py runserver
```

### 2. Open Streaming Interface
Navigate to: `http://localhost:8000/voice-bot-streaming/`

### 3. Test Voice Query
1. Click "🎙️ Start Recording"
2. Speak: "Can I track my order?"
3. Watch real-time transcription appear
4. Click "⏹️ Stop" when done
5. See intent detected and response generated

---

## Architecture Overview

### Components

```
Frontend (WebSocket Client)
    ↓
WebSocket Connection (/ws/voice-stream/)
    ↓
Django Channels AsyncWebsocketConsumer
    ↓
Audio Processing Pipeline:
    ├── Whisper STT (transcription)
    ├── Intent Classifier
    ├── Service Handler
    └── gTTS (optional text-to-speech)
    ↓
Response Streaming Back to Frontend
```

### Message Flow

#### Initialization
```javascript
Client → Server: {type: 'init', language: 'en', include_tts: true}
Server → Client: {type: 'session_ready'}
```

#### Audio Streaming
```javascript
Client → Server: {type: 'audio_chunk', data: 'base64_audio'}
Server → Client: {type: 'chunk_received', chunk_index: 1}
```

#### Processing Updates
```javascript
Server → Client: {type: 'partial_transcript', text: 'Can I...', confidence: 0.95}
Server → Client: {type: 'intent_detected', intent: 'ORDER_TRACKING', confidence: 0.92}
```

#### Final Response
```javascript
Server → Client: {
  type: 'final_result',
  detected_text: 'Can I track my order?',
  intent: 'ORDER_TRACKING',
  confidence: 0.92,
  response: 'Sure! What is your order number?',
  processing_time_ms: 1250
}
```

---

## Testing Methods

### Method 1: Browser Interface (Easiest)

**Location**: `http://localhost:8000/voice-bot-streaming/`

**Features**:
- Visual feedback with real-time updates
- Confidence scoring display
- Intent classification badges
- Audio response playback
- Session tracking

**Steps**:
1. Select language (English, Spanish, etc.)
2. Check "Include Audio Response" for TTS
3. Click "Start Recording"
4. Speak a query:
   - "Track my order" → ORDER_TRACKING
   - "Show me hoodies" → PRODUCT_SEARCH
   - "I have a payment issue" → PAYMENT_ISSUE
5. Click "Stop" to process
6. View results and listen to response

---

### Method 2: JavaScript WebSocket Client

**Example Implementation**:

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/voice-stream/');

// Handle connection
ws.onopen = () => {
    console.log('Connected');
    
    // Initialize session
    ws.send(JSON.stringify({
        type: 'init',
        language: 'en',
        include_tts: true
    }));
};

// Handle messages
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'session_ready':
            console.log('Session ready, send audio chunks');
            break;
            
        case 'partial_transcript':
            console.log('Transcription:', data.text);
            console.log('Confidence:', data.confidence);
            break;
            
        case 'intent_detected':
            console.log('Intent:', data.intent);
            console.log('Confidence:', data.confidence);
            break;
            
        case 'final_result':
            console.log('Response:', data.response);
            console.log('Processing time:', data.processing_time_ms, 'ms');
            break;
            
        case 'tts_response':
            // Play audio response
            const audio = new Audio('data:audio/mp3;base64,' + data.audio);
            audio.play();
            break;
    }
};

// Send audio chunks
async function sendAudio() {
    const stream = await navigator.mediaDevices.getUserMedia({audio: true});
    const recorder = new MediaRecorder(stream);
    
    recorder.ondataavailable = (event) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const base64 = btoa(
                new Uint8Array(e.target.result).reduce((d, b) => 
                    d + String.fromCharCode(b), '')
            );
            
            ws.send(JSON.stringify({
                type: 'audio_chunk',
                data: base64
            }));
        };
        reader.readAsArrayBuffer(event.data);
    };
    
    recorder.start(200);  // Send chunks every 200ms
    
    setTimeout(() => {
        recorder.stop();
        ws.send(JSON.stringify({type: 'process', final: true}));
    }, 5000);  // Record for 5 seconds
}
```

---

### Method 3: Python WebSocket Client

**Installation**:
```bash
pip install websockets python-dotenv
```

**Example Script**:

```python
import asyncio
import websockets
import json
import base64

async def test_voice_bot():
    uri = "ws://localhost:8000/ws/voice-stream/"
    
    async with websockets.connect(uri) as websocket:
        # Initialize
        await websocket.send(json.dumps({
            'type': 'init',
            'language': 'en',
            'include_tts': False
        }))
        
        # Read session ready
        msg = await websocket.recv()
        print(f"Server: {msg}")
        
        # Send audio chunk (example with actual audio file)
        with open('sample_audio.mp3', 'rb') as f:
            audio_data = base64.b64encode(f.read()).decode('utf-8')
            
        await websocket.send(json.dumps({
            'type': 'audio_chunk',
            'data': audio_data
        }))
        
        # Process audio
        await websocket.send(json.dumps({
            'type': 'process',
            'final': True
        }))
        
        # Read responses
        while True:
            try:
                msg = await websocket.recv()
                data = json.loads(msg)
                
                if data['type'] == 'final_result':
                    print(f"\nDetected: {data['detected_text']}")
                    print(f"Intent: {data['intent']}")
                    print(f"Confidence: {data['confidence']:.2%}")
                    print(f"Response: {data['response']}")
                    break
                
                elif data['type'] == 'partial_transcript':
                    print(f"Transcript: {data['text']}")
                
                elif data['type'] == 'error':
                    print(f"Error: {data['message']}")
                    break
            
            except Exception as e:
                print(f"Error: {e}")
                break

asyncio.run(test_voice_bot())
```

---

### Method 4: cURL WebSocket Testing

**Test Connection**:
```bash
# Using wscat (npm install -g wscat)
wscat -c ws://localhost:8000/ws/voice-stream/

# Then send JSON:
{"type":"init","language":"en","include_tts":false}

# Send audio chunk
{"type":"audio_chunk","data":"base64_encoded_audio"}

# Process
{"type":"process","final":true}
```

---

## Test Cases & Scenarios

### Test Case 1: Order Tracking Query
```
Input: "Can I track my order?"
Expected Intent: ORDER_TRACKING
Expected Output: Order status or tracking number
Real-time Updates: 
  - Partial transcription appears as user speaks
  - Intent classified as ORDER_TRACKING
  - Database saves query
```

### Test Case 2: Product Search Query
```
Input: "Show me blue jackets"
Expected Intent: PRODUCT_SEARCH
Expected Output: Product list or product count
Real-time Updates:
  - Live transcription update
  - Intent changes to PRODUCT_SEARCH
  - Products shown from database
```

### Test Case 3: Payment Issue Query
```
Input: "I have a payment problem"
Expected Intent: PAYMENT_ISSUE
Expected Output: Support contact information
Real-time Updates:
  - Transcription shows in real-time
  - Payment issue detected
  - Support info returned
```

### Test Case 4: Return Request Query
```
Input: "Can I return this item?"
Expected Intent: RETURN_REQUEST
Expected Output: Return policy information
Real-time Updates:
  - Live updates as user speaks
  - Intent detected correctly
  - Return policy provided
```

### Test Case 5: General Query
```
Input: "Hello, how are you?"
Expected Intent: GENERAL_QUERY
Expected Output: Greeting response
Real-time Updates:
  - Transcription shown immediately
  - GENERAL_QUERY intent detected
  - Friendly response generated
```

### Test Case 6: Unknown Query
```
Input: "Blah blah blah blah"
Expected Intent: UNKNOWN
Expected Output: Fallback message
Real-time Updates:
  - Transcription attempts to match
  - Falls back to UNKNOWN
  - Generic response
```

---

## Performance Monitoring

### Metrics to Track

**1. Connection Performance**
- WebSocket connection time: Should be < 100ms
- Session initialization: Should be < 500ms
- Chunk reception: Should be immediate

**2. Processing Performance**
```
Processing Time Breakdown:
├── Whisper STT: 1-3 seconds (cached model)
├── Intent Classification: 50-200ms
├── Service Handler: 100-500ms (DB query)
└── TTS Generation: 2-5 seconds (if enabled)
```

**3. Real-Time Updates**
- Partial transcription: Should appear within 500ms
- Intent detection: Should appear within 1-2 seconds
- Final result: Should appear within 3-5 seconds

**4. Database Performance**
- Query save time: Should be < 500ms
- Index query time: Should be < 100ms

### Monitoring Dashboard

```
Frontend Indicators:
├── 🟢 Connected - WebSocket active
├── 🎙️ Recording - Chunks being sent (shows count)
├── ⏳ Processing - Text → Intent → Response
├── ✅ Complete - Results ready
└── ❌ Error - Issue occurred
```

---

## Error Handling

### Common Errors & Solutions

**Error 1: WebSocket Connection Failed**
```
Error: "WebSocket connection error"
Cause: Server not running or Channels not configured
Solution: 
  - Ensure ASGI_APPLICATION in settings.py
  - Check INSTALLED_APPS has 'channels'
  - Verify voice_bot.routing in asgi.py
```

**Error 2: Microphone Access Denied**
```
Error: "Microphone access denied"
Cause: Browser permission not granted
Solution:
  - Click "Allow" when browser asks for microphone
  - Use HTTPS in production
```

**Error 3: Empty Audio**
```
Error: "No audio data"
Cause: Recording didn't capture audio
Solution:
  - Check microphone is working
  - Ensure at least 2 seconds of audio
  - Check audio format support
```

**Error 4: Transcription Failed**
```
Error: "Transcription failed"
Cause: Audio quality or format issue
Solution:
  - Use clear audio
  - Ensure sample rate is 16kHz
  - Try different microphone
```

**Error 5: Processing Timeout**
```
Error: "Still processing previous audio"
Cause: Previous request still in progress
Solution:
  - Wait for completion
  - Check server logs
  - Restart connection if needed
```

---

## Advanced Configuration

### Performance Tuning

**1. Channels Configuration** (`settings.py`):
```python
# Development: In-memory
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}

# Production: Redis
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': ['127.0.0.1:6379'],
            'capacity': 5000,
            'expiry': 3600,
        },
    },
}
```

**2. Audio Chunk Configuration**:
```python
# Frequency of partial processing
PARTIAL_PROCESS_THRESHOLD = 50  # Process every 50 chunks

# Maximum audio chunk size
MAX_CHUNK_SIZE = 64 * 1024  # 64KB
```

**3. Model Caching**:
```python
# Whisper model stays in memory
# Intent classifier stays in memory
# Service handler stays in memory
# This provides excellent performance after first request
```

---

## Deployment Configuration

### Production Deployment (Render.com)

**1. Update settings.py**:
```python
# Channels ASGI
ASGI_APPLICATION = 'shopping_store.asgi.application'

# Use Redis on production
if ENVIRONMENT == 'production':
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [os.environ.get('REDIS_URL')],
            },
        },
    }
```

**2. Update Procfile**:
```
web: gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker shopping_store.wsgi:application
```

**3. requirements.txt additions**:
```
channels>=4.0.0
channels-redis>=4.0.0
daphne>=4.0.0
```

---

## WebSocket Message Reference

### Client → Server Messages

```javascript
// Initialize session
{
    type: 'init',
    language: 'en|es|fr|de|hi',
    include_tts: true|false
}

// Audio chunk
{
    type: 'audio_chunk',
    data: 'base64_encoded_audio_data'
}

// Process accumulated audio
{
    type: 'process',
    final: true|false
}

// Stop streaming
{
    type: 'stop'
}
```

### Server → Client Messages

```javascript
// Connection established
{
    type: 'connection_established',
    session_id: 'uuid',
    timestamp: '2024-01-01T00:00:00'
}

// Session ready
{
    type: 'session_ready',
    message: 'Ready to receive audio'
}

// Chunk received
{
    type: 'chunk_received',
    chunk_index: 1,
    total_bytes: 2048
}

// Partial transcription
{
    type: 'partial_transcript',
    text: 'Can I track...',
    confidence: 0.95,
    language: 'en'
}

// Intent detected
{
    type: 'intent_detected',
    intent: 'ORDER_TRACKING',
    confidence: 0.92,
    candidates: [
        {intent: 'ORDER_TRACKING', confidence: 0.92},
        {intent: 'GENERAL_QUERY', confidence: 0.05}
    ]
}

// Final result
{
    type: 'final_result',
    detected_text: 'Can I track my order?',
    detected_language: 'en',
    intent: 'ORDER_TRACKING',
    confidence: 0.92,
    response: 'Sure! What is your order number?',
    data: {},
    processing_time_ms: 1250
}

// TTS audio response
{
    type: 'tts_response',
    audio: 'base64_audio',
    format: 'mp3',
    duration_approx: 2.5
}

// Error
{
    type: 'error',
    message: 'Error description'
}
```

---

## Troubleshooting Checklist

### Before Testing
- [ ] Django development server running
- [ ] SQLite/PostgreSQL database available
- [ ] Whisper model installed (`pip install openai-whisper`)
- [ ] Channels configured in settings
- [ ] ASGI configured in main asgi.py
- [ ] voice_bot app in INSTALLED_APPS
- [ ] Migrations applied

### During Testing
- [ ] Check browser console for errors
- [ ] Check Django server logs for warnings
- [ ] Verify WebSocket connection (DevTools > Network)
- [ ] Check browser microphone permissions
- [ ] Verify audio input device working
- [ ] Monitor processing times

### After Testing
- [ ] Verify database saved queries
- [ ] Check admin interface for new entries
- [ ] Review server logs for any errors
- [ ] Test all 6 intent types
- [ ] Verify confidence scores are reasonable

---

## Next Steps

1. **Production Deployment**: Configure Redis and deploy to Render
2. **Frontend Integration**: Embed streaming widget in main store
3. **Mobile Support**: Create React Native app
4. **Advanced NLP**: Upgrade intent classifier to RoBERTa model
5. **Multi-language Support**: Add more language models
6. **Analytics Dashboard**: Track usage patterns

---

## Support & Documentation

- **Main Documentation**: [VOICE_BOT_IMPLEMENTATION.md](VOICE_BOT_IMPLEMENTATION.md)
- **API Reference**: [VOICE_BOT_API_REFERENCE.md](VOICE_BOT_API_REFERENCE.md)
- **File Guide**: [VOICE_BOT_FILE_GUIDE.md](VOICE_BOT_FILE_GUIDE.md)
- **Architecture**: [VOICE_BOT_ARCHITECTURE.md](VOICE_BOT_ARCHITECTURE.md)

