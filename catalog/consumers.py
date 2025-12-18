import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
import aioredis
import os
from django.conf import settings

REDIS_HOST = os.environ.get('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))

class ProductLiveViewConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.product_id = self.scope['url_route']['kwargs']['product_id']
        self.group_name = f'product_live_{self.product_id}'
        self.session_key = self.scope['session'].session_key or await self._get_or_create_session()
        self.user_id = self.scope['user'].id if self.scope['user'].is_authenticated else None
        self.is_bot = self._is_bot()
        if self.is_bot:
            await self.close()
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self._add_viewer()
        await self.accept()
        await self._send_count()

    async def disconnect(self, close_code):
        if not self.is_bot:
            await self._remove_viewer()
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            await self._send_count()

    async def receive(self, text_data=None, bytes_data=None):
        # Optionally handle ping/pong or keepalive
        pass

    async def _send_count(self):
        count = await self._get_count()
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'live_count',
                'count': count
            }
        )

    async def live_count(self, event):
        await self.send(text_data=json.dumps({'count': event['count']}))

    def _is_bot(self):
        headers = dict(self.scope.get('headers', []))
        user_agent = headers.get(b'user-agent', b'').decode('utf-8').lower()
        return 'bot' in user_agent or 'spider' in user_agent or 'crawl' in user_agent

    async def _get_or_create_session(self):
        await database_sync_to_async(self.scope['session'].save)()
        return self.scope['session'].session_key

    async def _add_viewer(self):
        redis = await aioredis.create_redis_pool((REDIS_HOST, REDIS_PORT))
        key = f'product_live_users:{self.product_id}'
        # Use session_key or user_id to avoid duplicates
        unique_id = self.user_id or self.session_key
        await redis.sadd(key, unique_id)
        await redis.expire(key, 60)  # auto-expire after 60s inactivity
        redis.close()
        await redis.wait_closed()

    async def _remove_viewer(self):
        redis = await aioredis.create_redis_pool((REDIS_HOST, REDIS_PORT))
        key = f'product_live_users:{self.product_id}'
        unique_id = self.user_id or self.session_key
        await redis.srem(key, unique_id)
        redis.close()
        await redis.wait_closed()

    async def _get_count(self):
        redis = await aioredis.create_redis_pool((REDIS_HOST, REDIS_PORT))
        key = f'product_live_users:{self.product_id}'
        count = await redis.scard(key)
        redis.close()
        await redis.wait_closed()
        return count
