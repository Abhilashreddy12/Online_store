import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
import os
from django.conf import settings

logger = logging.getLogger(__name__)

# Redis configuration with environment variable support
REDIS_URL = os.environ.get('REDIS_URL', None)
REDIS_HOST = os.environ.get('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)
REDIS_SSL = os.environ.get('REDIS_SSL', 'false').lower() == 'true'

# Flag to track Redis availability
_redis_available = True


async def get_redis_connection():
    """
    Get a Redis connection with proper error handling.
    Returns None if Redis is unavailable.
    """
    global _redis_available
    
    if not _redis_available:
        return None
    
    try:
        import redis.asyncio as aioredis
        
        if REDIS_URL:
            # Use Redis URL (production - Render, etc.)
            redis = await aioredis.from_url(
                REDIS_URL,
                encoding='utf-8',
                decode_responses=True
            )
        else:
            # Use host/port configuration (local development)
            redis = await aioredis.from_url(
                f"redis://{REDIS_HOST}:{REDIS_PORT}",
                password=REDIS_PASSWORD,
                encoding='utf-8',
                decode_responses=True
            )
        
        # Test the connection
        await redis.ping()
        return redis
        
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Falling back to in-memory tracking.")
        _redis_available = False
        return None


class ProductLiveViewConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for tracking live product viewers.
    Falls back to channel layer if Redis is unavailable.
    """
    
    # In-memory fallback for viewer counts when Redis is unavailable
    _viewer_counts = {}
    _viewer_sessions = {}
    
    async def connect(self):
        self.product_id = self.scope['url_route']['kwargs']['product_id']
        self.group_name = f'product_live_{self.product_id}'
        self.session_key = self.scope['session'].session_key or await self._get_or_create_session()
        self.user_id = self.scope['user'].id if self.scope['user'].is_authenticated else None
        self.is_bot = self._is_bot()
        
        if self.is_bot:
            await self.close()
            return
        
        # Join the channel group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        
        # Add viewer to tracking
        await self._add_viewer()
        
        # Accept the connection
        await self.accept()
        
        # Send initial count
        await self._send_count()

    async def disconnect(self, close_code):
        if not self.is_bot:
            # Remove viewer from tracking
            await self._remove_viewer()
            
            # Leave the channel group
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            
            # Broadcast updated count to remaining viewers
            await self._send_count()

    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming messages - primarily keepalive pings."""
        if text_data:
            try:
                data = json.loads(text_data)
                if data.get('type') == 'ping':
                    # Respond to ping with pong
                    await self.send(text_data=json.dumps({'type': 'pong'}))
                    # Refresh viewer tracking
                    await self._refresh_viewer()
            except json.JSONDecodeError:
                pass

    async def _send_count(self):
        """Broadcast the current viewer count to all connected clients."""
        count = await self._get_count()
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'live_count',
                'count': count
            }
        )

    async def live_count(self, event):
        """Handle live_count message from channel layer."""
        await self.send(text_data=json.dumps({
            'count': event['count'],
            'type': 'count_update'
        }))

    def _is_bot(self):
        """Check if the connection is from a bot/crawler."""
        headers = dict(self.scope.get('headers', []))
        user_agent = headers.get(b'user-agent', b'').decode('utf-8').lower()
        bot_indicators = ['bot', 'spider', 'crawl', 'slurp', 'baidu', 'yandex', 'googlebot']
        return any(indicator in user_agent for indicator in bot_indicators)

    async def _get_or_create_session(self):
        """Ensure session exists and return the session key."""
        await database_sync_to_async(self.scope['session'].save)()
        return self.scope['session'].session_key

    async def _add_viewer(self):
        """Add a viewer to the tracking system."""
        unique_id = str(self.user_id or self.session_key)
        key = f'product_live_users:{self.product_id}'
        
        redis = await get_redis_connection()
        
        if redis:
            try:
                await redis.sadd(key, unique_id)
                await redis.expire(key, 120)  # Auto-expire after 2 minutes
                await redis.aclose()
            except Exception as e:
                logger.error(f"Redis add_viewer error: {e}")
                self._fallback_add_viewer(unique_id)
        else:
            self._fallback_add_viewer(unique_id)

    def _fallback_add_viewer(self, unique_id):
        """Fallback to in-memory tracking when Redis is unavailable."""
        key = f'product_live_users:{self.product_id}'
        if key not in self._viewer_sessions:
            self._viewer_sessions[key] = set()
        self._viewer_sessions[key].add(unique_id)

    async def _remove_viewer(self):
        """Remove a viewer from the tracking system."""
        unique_id = str(self.user_id or self.session_key)
        key = f'product_live_users:{self.product_id}'
        
        redis = await get_redis_connection()
        
        if redis:
            try:
                await redis.srem(key, unique_id)
                await redis.aclose()
            except Exception as e:
                logger.error(f"Redis remove_viewer error: {e}")
                self._fallback_remove_viewer(unique_id)
        else:
            self._fallback_remove_viewer(unique_id)

    def _fallback_remove_viewer(self, unique_id):
        """Fallback to in-memory tracking when Redis is unavailable."""
        key = f'product_live_users:{self.product_id}'
        if key in self._viewer_sessions:
            self._viewer_sessions[key].discard(unique_id)

    async def _refresh_viewer(self):
        """Refresh viewer's presence in tracking."""
        unique_id = str(self.user_id or self.session_key)
        key = f'product_live_users:{self.product_id}'
        
        redis = await get_redis_connection()
        
        if redis:
            try:
                # Re-add to set and refresh expiry
                await redis.sadd(key, unique_id)
                await redis.expire(key, 120)
                await redis.aclose()
            except Exception as e:
                logger.error(f"Redis refresh_viewer error: {e}")

    async def _get_count(self):
        """Get the current viewer count."""
        key = f'product_live_users:{self.product_id}'
        
        redis = await get_redis_connection()
        
        if redis:
            try:
                count = await redis.scard(key)
                await redis.aclose()
                return count
            except Exception as e:
                logger.error(f"Redis get_count error: {e}")
                return self._fallback_get_count()
        else:
            return self._fallback_get_count()

    def _fallback_get_count(self):
        """Fallback to in-memory count when Redis is unavailable."""
        key = f'product_live_users:{self.product_id}'
        if key in self._viewer_sessions:
            return len(self._viewer_sessions[key])
        return 1  # At least the current user
