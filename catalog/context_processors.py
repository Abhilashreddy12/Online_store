from django.utils import timezone
from django.db.utils import ProgrammingError


def active_banners(request):
    """Add active banners to all templates"""
    try:
        from .models import Banner
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
    except (ProgrammingError, Exception):
        # Table doesn't exist yet (migrations not run) or other error
        return {
            'active_banners': [],
        }
