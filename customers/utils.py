from django.utils import timezone
from customers.models import Customer
from datetime import timedelta
from django.contrib.auth.models import User


def get_client_ip(request):
    """
    Get the real client IP address from request, considering X-Forwarded-For (Render proxy).
    Fallback to REMOTE_ADDR if header is missing.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # X-Forwarded-For: client, proxy1, proxy2
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_total_users_count():
    return User.objects.count()


def get_active_users_count(minutes=5):
    threshold = timezone.now() - timedelta(minutes=minutes)
    return Customer.objects.filter(last_activity__gte=threshold).count()
