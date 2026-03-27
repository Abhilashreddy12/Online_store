# AI Shopping Assistant Chatbot - Setup Guide

## Overview

This document provides instructions for setting up and configuring the AI-powered Shopping Assistant Chatbot for your Django e-commerce application.

## Features

- 🔍 **Semantic Product Search** - Natural language product discovery using embeddings
- 💡 **Smart Recommendations** - AI-powered product recommendations based on user preferences
- 🛒 **Cart Operations** - Add/remove items and view cart via chat
- 📦 **Order Tracking** - Track orders and view order history
- ❓ **FAQ Support** - RAG-based FAQ retrieval for common questions
- 📏 **Size Recommendations** - Personalized size suggestions
- 💬 **Conversation Memory** - Context-aware chat with history
- 🤖 **LangChain Agent** - Advanced AI agent with tool-based architecture

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

The following packages are required:
- `langchain>=0.1.0` - AI agent framework
- `langchain-openai>=0.0.2` - OpenAI integration
- `sentence-transformers>=2.2.2` - Embedding model
- `faiss-cpu>=1.7.4` - Vector similarity search
- `numpy>=1.24.0` - Numerical operations
- `tiktoken>=0.5.0` - Token counting

### 2. Run Database Migrations

```bash
python manage.py makemigrations chatbot
python manage.py migrate
```

### 3. Initialize the Chatbot

```bash
python manage.py setup_chatbot
```

This command will:
- Generate embeddings for all existing products
- Set up the FAISS vector index
- Load default FAQ documents

### 4. (Optional) Configure OpenAI API Key

For advanced AI capabilities with LangChain:

Add to your `.env` file or environment:
```
OPENAI_API_KEY=your-api-key-here
```

Or in `settings.py`:
```python
OPENAI_API_KEY = 'your-api-key-here'
```

**Note:** Without an OpenAI API key, the chatbot will use a rule-based fallback agent.

## Configuration Options

Add these to your `settings.py` to customize behavior:

```python
# Chatbot Settings
CHATBOT_CONFIG = {
    # Model for embeddings (all-MiniLM-L6-v2 is lightweight and fast)
    'EMBEDDING_MODEL': 'all-MiniLM-L6-v2',
    
    # Maximum products to return in search
    'MAX_SEARCH_RESULTS': 5,
    
    # OpenAI model for LangChain agent (if API key is set)
    'LLM_MODEL': 'gpt-3.5-turbo',
    
    # Conversation history length
    'MEMORY_WINDOW': 10,
}
```

## Architecture

### Components

```
chatbot/
├── models.py          # Database models (ChatLog, ProductEmbedding, FAQDocument)
├── embeddings.py      # FAISS vector store and embedding generation
├── memory.py          # Conversation memory management
├── tools.py           # LangChain tools for product/cart/order operations
├── rag_pipeline.py    # FAQ retrieval system
├── agent.py           # Main AI agent (SimpleAgent + LangChainAgent)
├── signals.py         # Auto-embed products on save
├── views.py           # API endpoints
└── urls.py            # URL routing
```

### Flow

1. User sends message via chat widget
2. Message processed by `/chatbot/api/chat/` endpoint
3. Agent determines intent and selects appropriate tools
4. Tools query database/vector store
5. Response formatted and returned to user

### Agent Architecture

The chatbot uses a two-tier agent system:

**SimpleAgent (Default/Fallback)**
- Rule-based pattern matching
- Works without external API
- Handles common queries (search, cart, orders, FAQ)

**LangChainAgent (When OpenAI configured)**
- LLM-powered reasoning
- Dynamic tool selection
- More natural conversations
- Better context understanding

## API Endpoints

### Chat API
```
POST /chatbot/api/chat/
Content-Type: application/json

{
    "message": "Show me red dresses under 5000",
    "session_id": "optional-session-id"
}
```

Response:
```json
{
    "type": "product_list",
    "message": "Here are 5 red dresses under ₹5000:",
    "data": {
        "products": [...],
        "count": 5
    },
    "session_id": "abc123"
}
```

### Chat History
```
GET /chatbot/api/history/?session_id=abc123
```

### Clear History
```
POST /chatbot/api/clear/
Content-Type: application/json

{
    "session_id": "abc123"
}
```

### Rebuild Embeddings (Admin)
```
POST /chatbot/api/admin/rebuild-embeddings/
```

## Response Types

| Type | Description |
|------|-------------|
| `product_list` | List of products with pagination |
| `cart` | Current cart contents |
| `cart_action` | Cart add/remove confirmation |
| `order` | Single order details |
| `order_list` | List of user orders |
| `faq` | FAQ answer |
| `size_recommendation` | Size suggestion |
| `general` | General text response |
| `error` | Error message |

## Frontend Widget

The chatbot widget is automatically included in `base.html`. The widget consists of:

- `static/css/chatbot.css` - Styling
- `static/js/chatbot.js` - JavaScript functionality

### Customization

**Changing Colors:**
Edit CSS variables in `chatbot.css`:
```css
:root {
    --chatbot-primary: #667eea;
    --chatbot-secondary: #764ba2;
}
```

**Changing Position:**
```css
.chatbot-toggle,
.chatbot-window {
    right: 20px; /* Change to left: 20px; for left side */
}
```

## Maintenance

### Rebuilding Product Embeddings

When products are updated in bulk:
```bash
python manage.py setup_chatbot
```

Or via API (admin only):
```bash
curl -X POST http://localhost:8000/chatbot/api/admin/rebuild-embeddings/
```

### Monitoring Chat Logs

View in Django Admin:
- Navigate to Admin > Chatbot > Chat Logs

Or query directly:
```python
from chatbot.models import ChatLog

# Recent chats
recent = ChatLog.objects.order_by('-timestamp')[:50]

# Failed queries (for improvement)
errors = ChatLog.objects.filter(response_type='error')
```

### Adding Custom FAQs

```python
from chatbot.models import FAQDocument

FAQDocument.objects.create(
    title="Custom Question Title",
    content="Detailed answer here...",
    category="general"
)
```

Then rebuild FAQ embeddings:
```bash
python manage.py setup_chatbot
```

## Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### Embeddings not generating
Check that `sentence-transformers` downloaded the model:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
```

### FAISS index errors
Delete and rebuild:
```bash
rm chatbot/data/products.index
rm chatbot/data/product_mapping.json
python manage.py setup_chatbot
```

### Chat widget not appearing
1. Check browser console for JS errors
2. Verify CSS/JS files are in staticfiles
3. Run `python manage.py collectstatic`

### OpenAI API errors
- Verify API key is correct
- Check API rate limits
- Chatbot will fall back to SimpleAgent automatically

## Performance Tips

1. **Preload embeddings on startup** - The first chat may be slow as the model loads
2. **Use caching** - Consider Redis for frequent queries
3. **Limit product scope** - Index only active products
4. **Monitor vector index size** - Rebuild periodically to remove orphaned entries

## Security Notes

- CSRF protection is enabled on all POST endpoints
- User IDs are validated for cart/order operations
- Admin endpoints require staff permissions
- Sanitize all user inputs before processing

## Support

For issues or feature requests, please contact the development team.
