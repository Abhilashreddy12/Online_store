# Live Product Viewers Feature

This feature shows a real-time count of users currently viewing a product page.

## How it works
- Uses Django Channels and Redis for real-time WebSocket communication.
- Tracks unique sessions (or user IDs) per product in Redis.
- Updates the count live on the product detail page without refresh.
- Ignores bots and duplicate sessions.

## Setup
1. Install dependencies:
   pip install -r requirements.txt

2. Ensure Redis is running (default: 127.0.0.1:6379).
   - For production, set REDIS_HOST and REDIS_PORT in your environment or .env file.

3. Run Django with Channels (ASGI):
   daphne shopping_store.asgi:application
   # or
   python manage.py runserver  # (if using Django 4+ with Channels)

4. Open a product page. The live viewer count will update in real time.

## Notes
- If you deploy, ensure your ASGI server supports WebSockets (e.g., Daphne, Uvicorn, or via Render's ASGI support).
- The count is per product and only counts real users (not bots or duplicate sessions).
- If you want to customize the session timeout, adjust the expire time in ProductLiveViewConsumer.
