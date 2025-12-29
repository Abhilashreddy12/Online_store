from django.utils import timezone
from customers.utils import get_client_ip
from customers.models import Customer

class UserActivityMiddleware:
    """
    Middleware to update last_activity and last_ip for authenticated users.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            try:
                customer = request.user.customer_profile
                customer.last_activity = timezone.now()
                customer.last_ip = get_client_ip(request)
                customer.save(update_fields=["last_activity", "last_ip"])
            except Customer.DoesNotExist:
                pass
        return response
