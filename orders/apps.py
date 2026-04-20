from django.apps import AppConfig


class OrdersConfig(AppConfig):
    name = 'orders'
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        """
        Import signals when the app is ready
        This ensures email notifications are triggered on order events
        """
        import orders.signals  # noqa: F401
