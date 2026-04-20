from django.apps import AppConfig


class CustomersConfig(AppConfig):
    name = 'customers'
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        """
        Import signals when the app is ready
        This ensures email notifications are triggered on customer events
        """
        import customers.signals  # noqa: F401
