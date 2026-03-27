from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatbot'
    verbose_name = 'AI Shopping Assistant'

    def ready(self):
        """Initialize chatbot components when Django starts"""
        # Import signals to auto-generate embeddings for new products
        try:
            from . import signals
        except ImportError:
            pass
