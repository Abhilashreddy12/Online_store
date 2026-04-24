from django.urls import path
from . import views

app_name = 'voice_bot'

urlpatterns = [
    # Main voice query endpoint
    path('api/voice-query/', views.voice_query_view, name='voice-query'),
    
    # History and analytics endpoints
    path('api/voice-query/history/', views.query_history_view, name='query-history'),
    path('api/voice-query/stats/', views.query_stats_view, name='query-stats'),
    
    # Real-time streaming interface
    path('voice-bot-streaming/', views.voice_bot_streaming_interface, name='streaming-interface'),
]
