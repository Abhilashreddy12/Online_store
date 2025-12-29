from django.shortcuts import render
from customers.utils import get_total_users_count, get_active_users_count

def dashboard_stats(request):
    total_users = get_total_users_count()
    active_users = get_active_users_count()
    return render(request, "dashboard/stats.html", {
        "total_users": total_users,
        "active_users": active_users,
    })
