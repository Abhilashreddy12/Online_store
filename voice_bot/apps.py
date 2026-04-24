from django.apps import AppConfig


class VoiceBotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'voice_bot'
    verbose_name = 'Voice AI Assistant'

    def ready(self):
        """Initialize the app - load Whisper model on startup"""
        # Lazy load - only initialize when first needed in production
        pass
