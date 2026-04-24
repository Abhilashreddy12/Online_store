"""
WebSocket routing for voice_bot
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/voice-stream/$', consumers.VoiceStreamConsumer.as_asgi()),
]
