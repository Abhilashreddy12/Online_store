from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class VoiceQuery(models.Model):
    """Store voice queries for analytics and auditing"""
    
    INTENT_CHOICES = [
        ('ORDER_TRACKING', 'Order Tracking'),
        ('PRODUCT_SEARCH', 'Product Search'),
        ('PAYMENT_ISSUE', 'Payment Issue'),
        ('RETURN_REQUEST', 'Return Request'),
        ('GENERAL_QUERY', 'General Query'),
        ('UNKNOWN', 'Unknown Intent'),
    ]
    
    CONFIDENCE_LEVELS = [
        ('HIGH', 'High (>0.8)'),
        ('MEDIUM', 'Medium (0.5-0.8)'),
        ('LOW', 'Low (<0.5)'),
    ]
    
    # User and timestamp
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='voice_queries', null=True, blank=True)
    session_id = models.CharField(max_length=100, blank=True)
    
    # Audio and transcription
    audio_file = models.FileField(upload_to='voice_queries/%Y/%m/%d/', null=True, blank=True)
    audio_duration = models.FloatField(help_text="Duration in seconds", default=0)
    
    # Processing results
    transcribed_text = models.TextField()
    detected_language = models.CharField(max_length=10, default='en')
    
    # Intent classification
    intent = models.CharField(max_length=50, choices=INTENT_CHOICES, default='UNKNOWN')
    confidence_score = models.FloatField(default=0.0, validators=[])
    confidence_level = models.CharField(max_length=10, choices=CONFIDENCE_LEVELS, default='MEDIUM')
    
    # Response
    response_message = models.TextField()
    response_audio = models.FileField(upload_to='voice_responses/%Y/%m/%d/', null=True, blank=True)
    
    # Metadata
    error_message = models.TextField(blank=True)
    processing_time_ms = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['intent', 'created_at']),
            models.Index(fields=['session_id']),
        ]
        verbose_name = 'Voice Query'
        verbose_name_plural = 'Voice Queries'
    
    def __str__(self):
        return f"Voice Query - {self.intent} ({self.created_at})"
    
    def calculate_confidence_level(self):
        """Calculate confidence level based on score"""
        if self.confidence_score > 0.8:
            self.confidence_level = 'HIGH'
        elif self.confidence_score > 0.5:
            self.confidence_level = 'MEDIUM'
        else:
            self.confidence_level = 'LOW'


class VoiceQueryLog(models.Model):
    """Detailed logs for debugging and monitoring"""
    
    voice_query = models.OneToOneField(VoiceQuery, on_delete=models.CASCADE, related_name='log')
    
    stt_model = models.CharField(max_length=50, default='whisper')
    stt_model_size = models.CharField(max_length=20, default='base')  # tiny, base, small, medium, large
    
    intent_classifier = models.CharField(max_length=50, default='rule_based')
    intent_candidates = models.JSONField(default=dict)  # Store top-3 intents with scores
    
    raw_response = models.JSONField(default=dict)  # Store complete response before serialization
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Voice Query Log'
        verbose_name_plural = 'Voice Query Logs'
    
    def __str__(self):
        return f"Log - {self.voice_query.id}"
