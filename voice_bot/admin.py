from django.contrib import admin
from django.utils.html import format_html
from .models import VoiceQuery, VoiceQueryLog


@admin.register(VoiceQuery)
class VoiceQueryAdmin(admin.ModelAdmin):
    """Admin interface for Voice Queries"""
    
    list_display = (
        'id',
        'user',
        'intent_badge',
        'confidence_badge',
        'transcribed_text_short',
        'processing_time_display',
        'created_at'
    )
    
    list_filter = (
        'intent',
        'confidence_level',
        'created_at',
        'user'
    )
    
    search_fields = (
        'transcribed_text',
        'response_message',
        'user__username',
        'session_id'
    )
    
    readonly_fields = (
        'session_id',
        'detected_language',
        'confidence_score',
        'confidence_level',
        'processing_time_ms',
        'created_at',
        'updated_at'
    )
    
    fieldsets = (
        ('Query Information', {
            'fields': ('user', 'session_id', 'created_at', 'updated_at')
        }),
        ('Audio & Transcription', {
            'fields': ('audio_file', 'audio_duration', 'transcribed_text', 'detected_language')
        }),
        ('Intent & Classification', {
            'fields': ('intent', 'confidence_score', 'confidence_level')
        }),
        ('Response', {
            'fields': ('response_message', 'response_audio')
        }),
        ('Performance', {
            'fields': ('processing_time_ms',)
        }),
        ('Error Handling', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        })
    )
    
    def intent_badge(self, obj):
        """Display intent as colored badge"""
        colors = {
            'ORDER_TRACKING': '#0066cc',
            'PRODUCT_SEARCH': '#00cc66',
            'PAYMENT_ISSUE': '#ff6600',
            'RETURN_REQUEST': '#ff3300',
            'GENERAL_QUERY': '#9933ff',
            'UNKNOWN': '#999999'
        }
        color = colors.get(obj.intent, '#999999')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_intent_display()
        )
    intent_badge.short_description = 'Intent'
    
    def confidence_badge(self, obj):
        """Display confidence as colored badge"""
        if obj.confidence_level == 'HIGH':
            color = '#00cc66'
        elif obj.confidence_level == 'MEDIUM':
            color = '#ff9900'
        else:
            color = '#ff3300'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{:.0%}</span>',
            color,
            obj.confidence_score
        )
    confidence_badge.short_description = 'Confidence'
    
    def transcribed_text_short(self, obj):
        """Display truncated transcribed text"""
        text = obj.transcribed_text[:50]
        if len(obj.transcribed_text) > 50:
            text += '...'
        return text
    transcribed_text_short.short_description = 'Transcribed Text'
    
    def processing_time_display(self, obj):
        """Display processing time with formatting"""
        return f"{obj.processing_time_ms}ms"
    processing_time_display.short_description = 'Processing Time'
    
    actions = ['mark_reviewed']
    
    def has_add_permission(self, request):
        """Disable adding queries manually"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete"""
        return request.user.is_superuser


@admin.register(VoiceQueryLog)
class VoiceQueryLogAdmin(admin.ModelAdmin):
    """Admin interface for Voice Query Logs"""
    
    list_display = (
        'id',
        'voice_query',
        'stt_model_display',
        'intent_classifier',
        'created_at'
    )
    
    list_filter = (
        'stt_model',
        'stt_model_size',
        'intent_classifier',
        'created_at'
    )
    
    search_fields = (
        'voice_query__transcribed_text',
        'voice_query__session_id'
    )
    
    readonly_fields = (
        'voice_query',
        'stt_model',
        'stt_model_size',
        'intent_classifier',
        'intent_candidates',
        'raw_response',
        'created_at'
    )
    
    fieldsets = (
        ('Query Reference', {
            'fields': ('voice_query', 'created_at')
        }),
        ('Speech-to-Text', {
            'fields': ('stt_model', 'stt_model_size')
        }),
        ('Intent Classification', {
            'fields': ('intent_classifier', 'intent_candidates')
        }),
        ('Response Data', {
            'fields': ('raw_response',)
        })
    )
    
    def stt_model_display(self, obj):
        """Display STT model with size"""
        return f"{obj.stt_model} ({obj.stt_model_size})"
    stt_model_display.short_description = 'STT Model'
    
    def has_add_permission(self, request):
        """Disable adding logs manually"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Disable editing"""
        return False
