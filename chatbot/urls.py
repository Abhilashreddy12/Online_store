"""
URL Configuration for Chatbot
"""

from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    # Main chat API
    path('api/chat/', views.chat_api, name='chat'),
    
    # Chat management
    path('api/history/', views.chat_history, name='history'),
    path('api/clear/', views.clear_chat_history, name='clear_history'),
    
    # Admin endpoints
    path('api/admin/rebuild-embeddings/', views.rebuild_embeddings, name='rebuild_embeddings'),
    path('api/admin/rebuild-faq/', views.rebuild_faq_index, name='rebuild_faq'),
    
    # Status
    path('api/status/', views.chatbot_status, name='status'),
]
