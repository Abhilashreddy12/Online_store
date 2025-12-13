from .models import Banner
from django.utils import timezone


def active_banners(request):
    """Add active banners to all templates"""
    now = timezone.now()
    banners = Banner.objects.filter(
        is_active=True,
        start_date__lte=now
    ).exclude(
        end_date__lt=now
    ).exclude(
        end_date__isnull=False,
        end_date__lt=now
    )[:3]  # Limit to top 3 banners
    
    return {
        'active_banners': [b for b in banners if b.is_valid],
    }
