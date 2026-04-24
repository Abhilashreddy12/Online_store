# Voice Bot - Quick Start Guide

## 5-Minute Setup

### Step 1: Install Dependencies
```bash
cd shopping_store
pip install openai-whisper gtts librosa soundfile
```

### Step 2: Run Migrations
```bash
python manage.py migrate voice_bot
```

### Step 3: Create Superuser (if not exists)
```bash
python manage.py createsuperuser
```

### Step 4: Start Development Server
```bash
python manage.py runserver
```

### Step 5: Access Admin
Visit: `http://localhost:8000/admin/voice_bot/`

---

## Testing the API

### Test 1: Order Tracking Query

**cURL:**
```bash
# Create a test audio file (or use existing .wav/.mp3)
curl -X POST http://localhost:8000/api/voice-query/ \
  -F "audio=@test_audio.wav" \
  -F "language=en" \
  -F "include_audio_response=false"
```

**Python:**
```python
import requests

with open('test_audio.wav', 'rb') as f:
    files = {'audio': f}
    data = {'language': 'en', 'include_audio_response': 'false'}
    
    response = requests.post(
        'http://localhost:8000/api/voice-query/',
        files=files,
        data=data
    )
    
    print(response.json())
```

**JavaScript:**
```javascript
const formData = new FormData();
formData.append('audio', audioFile);  // File from <input type="file">
formData.append('language', 'en');
formData.append('include_audio_response', 'false');

fetch('/api/voice-query/', {
    method: 'POST',
    body: formData
})
.then(res => res.json())
.then(data => console.log(data));
```

### Expected Response
```json
{
    "success": true,
    "session_id": "abc-123-def-456",
    "detected_text": "where is my order",
    "intent": "ORDER_TRACKING",
    "confidence": 0.92,
    "response": "Your order ORD-20260422-ABC123 has been shipped.",
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

---

## Frontend Integration Example

### HTML
```html
<!DOCTYPE html>
<html>
<head>
    <title>Voice Bot Demo</title>
</head>
<body>
    <div id="voice-bot-container">
        <button id="start-recording">🎤 Start Recording</button>
        <button id="stop-recording" disabled>⏹️ Stop Recording</button>
        
        <div id="status"></div>
        <div id="response"></div>
    </div>

    <script src="voice-bot.js"></script>
</body>
</html>
```

### JavaScript - voice-bot.js
```javascript
class VoiceBot {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        
        this.startBtn = document.getElementById('start-recording');
        this.stopBtn = document.getElementById('stop-recording');
        this.statusDiv = document.getElementById('status');
        this.responseDiv = document.getElementById('response');
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        this.startBtn.addEventListener('click', () => this.startRecording());
        this.stopBtn.addEventListener('click', () => this.stopRecording());
    }
    
    async startRecording() {
        this.audioChunks = [];
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        this.mediaRecorder = new MediaRecorder(stream);
        this.mediaRecorder.ondataavailable = (e) => {
            this.audioChunks.push(e.data);
        };
        
        this.mediaRecorder.start();
        this.isRecording = true;
        
        this.startBtn.disabled = true;
        this.stopBtn.disabled = false;
        this.statusDiv.textContent = '🎤 Recording...';
    }
    
    async stopRecording() {
        this.mediaRecorder.stop();
        this.isRecording = false;
        
        this.startBtn.disabled = false;
        this.stopBtn.disabled = true;
        this.statusDiv.textContent = '⏳ Processing...';
        
        // Wait for mediaRecorder to finish
        await new Promise(resolve => {
            this.mediaRecorder.onstop = resolve;
        });
        
        // Send to API
        await this.sendAudio();
    }
    
    async sendAudio() {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');
        formData.append('language', 'en');
        formData.append('include_audio_response', 'true');
        
        try {
            const response = await fetch('/api/voice-query/', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.displayResponse(result);
            } else {
                this.statusDiv.textContent = `❌ Error: ${result.error}`;
            }
        } catch (error) {
            this.statusDiv.textContent = `❌ Request failed: ${error.message}`;
        }
    }
    
    displayResponse(result) {
        this.statusDiv.textContent = `✅ Processing took ${result.processing_time_ms}ms`;
        
        let html = `
            <div class="voice-response">
                <h3>You said:</h3>
                <p>"${result.detected_text}"</p>
                
                <h3>Intent: ${result.intent}</h3>
                <p>Confidence: ${(result.confidence * 100).toFixed(1)}%</p>
                
                <h3>Response:</h3>
                <p>${result.response}</p>
        `;
        
        if (result.data && result.data.orders) {
            html += `<h3>Your Orders:</h3>`;
            result.data.orders.forEach(order => {
                html += `
                    <div class="order">
                        <p><strong>${order.order_number}</strong></p>
                        <p>Status: ${order.status_display}</p>
                        <p>Total: ₹${order.total_amount}</p>
                    </div>
                `;
            });
        }
        
        if (result.response_audio_url) {
            html += `
                <h3>🔊 Listen to Response</h3>
                <audio controls>
                    <source src="${result.response_audio_url}" type="audio/mpeg">
                </audio>
            `;
        }
        
        html += `</div>`;
        this.responseDiv.innerHTML = html;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    new VoiceBot();
});
```

### CSS Styling
```css
#voice-bot-container {
    max-width: 600px;
    margin: 20px auto;
    padding: 20px;
    border: 1px solid #ddd;
    border-radius: 8px;
}

button {
    padding: 10px 20px;
    font-size: 16px;
    margin: 5px;
    cursor: pointer;
    border-radius: 4px;
    border: none;
}

button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

#start-recording {
    background: #4CAF50;
    color: white;
}

#stop-recording {
    background: #f44336;
    color: white;
}

.voice-response {
    margin-top: 20px;
    padding: 15px;
    background: #f9f9f9;
    border-left: 4px solid #4CAF50;
}

.order {
    padding: 10px;
    margin: 10px 0;
    background: white;
    border: 1px solid #ddd;
    border-radius: 4px;
}
```

---

## Using Query History API

### Get Your Query History
```bash
curl -X GET "http://localhost:8000/api/voice-query/history/?limit=10&offset=0" \
  -H "Cookie: sessionid=YOUR_SESSION_ID"
```

### Get Statistics
```bash
curl -X GET "http://localhost:8000/api/voice-query/stats/" \
  -H "Cookie: sessionid=YOUR_SESSION_ID"
```

---

## Key Intents & Example Queries

### ORDER_TRACKING
- "where is my order"
- "track my package"
- "order status"
- "when will it arrive"

### PRODUCT_SEARCH
- "find me a shirt"
- "show me dresses"
- "do you have sneakers"
- "search for jackets"

### PAYMENT_ISSUE
- "payment failed"
- "refund my money"
- "why was i charged"

### RETURN_REQUEST
- "how to return"
- "return policy"
- "damaged product"

### GENERAL_QUERY
- "hello"
- "help"
- "what can you do"

---

## Troubleshooting

### Issue: Audio file not recognized
**Solution:** Ensure audio format is one of: mp3, wav, ogg, m4a, flac

### Issue: "Whisper not installed" error
**Solution:** 
```bash
pip install openai-whisper
```

### Issue: High latency on first request
**Solution:** First request loads the Whisper model (~1-2 seconds). Subsequent requests are faster.

### Issue: Wrong intent classification
**Solution:** Try being more specific in your query. Current system uses keyword matching.

---

## Database Access

View all voice queries:
```bash
python manage.py shell
>>> from voice_bot.models import VoiceQuery
>>> VoiceQuery.objects.all()[:10]
```

Check specific user's queries:
```bash
>>> from django.contrib.auth.models import User
>>> user = User.objects.get(username='john')
>>> VoiceQuery.objects.filter(user=user).order_by('-created_at')[:5]
```

---

## Admin Dashboard Features

1. **List View**: Filter by intent, date, user
2. **Colored Badges**: Quick visual identification
3. **Search**: Search by text, user, session ID
4. **Detailed View**: Full query details and logs
5. **Statistics**: Intent distribution, response times

---

## Performance Tips

1. **First Request**: Will take 5-30 seconds (model loading)
2. **Subsequent Requests**: 1-3 seconds (model cached)
3. **Audio Processing**: Use shorter audio clips (<1 min) for faster processing
4. **TTS Optional**: Disable audio response generation for faster API responses

---

## Next Steps

1. ✅ Setup complete
2. 📝 Customize intents in `intent.py`
3. 🔒 Implement authentication (replace CSRF exemption)
4. 📊 Monitor usage in admin panel
5. 🚀 Deploy to production (Render, Heroku, etc.)

For detailed documentation, see: `VOICE_BOT_IMPLEMENTATION.md`
