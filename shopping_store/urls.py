"""
URL configuration for shopping_store project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import set_language
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from dashboard.views import dashboard_stats
from catalog.sitemap import sitemaps

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('catalog.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    path('account/', include('customers.urls')),
    path('chatbot/', include('chatbot.urls')),
    path('', include('voice_bot.urls')),
    # Dashboard stats demo
    path('dashboard/stats/', dashboard_stats, name='dashboard_stats'),
    # SEO - Sitemap and Robots
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain'), name='robots'),
    path('manifest.json', TemplateView.as_view(template_name='manifest.json', content_type='application/json'), name='manifest'),
    # Password reset URLs
    path(
        'account/password_reset/',
        auth_views.PasswordResetView.as_view(
            template_name='customers/password_reset_form.html',
            email_template_name='customers/password_reset_email.txt',
            html_email_template_name='customers/password_reset_email.html',
            subject_template_name='customers/password_reset_subject.txt',
            success_url='/account/password_reset/done/'
        ),
        name='password_reset'
    ),
    path('account/password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='customers/password_reset_done.html'), name='password_reset_done'),
    path('account/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='customers/password_reset_confirm.html'), name='password_reset_confirm'),
    path('account/reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='customers/password_reset_complete.html'), name='password_reset_complete'),

    # Add set_language for Jazzmin language chooser
    path('set_language/', set_language, name='set_language'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
