"""
Sitemap configuration for SEO optimization.
Includes: Homepage, Products, Categories
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product, Category


class StaticViewSitemap(Sitemap):
    """
    Sitemap for static views like homepage
    Priority: High (1.0) for homepage, Medium (0.8) for others
    Change frequency: Daily for homepage
    """
    changefreq = "daily"
    priority = 1.0

    def items(self):
        return ['catalog:home', 'catalog:product_list']

    def location(self, item):
        return reverse(item)


class ProductSitemap(Sitemap):
    """
    Sitemap for all active products.
    Priority: 0.8 (Medium)
    Change frequency: Weekly (products updated regularly)
    Last modified: Product's updated_at timestamp
    """
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        # Only include active products
        return Product.objects.filter(is_active=True).order_by('-updated_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('catalog:product_detail', kwargs={'slug': obj.slug})


class CategorySitemap(Sitemap):
    """
    Sitemap for product categories.
    Priority: 0.9 (High)
    Change frequency: Monthly
    Last modified: Category's updated_at timestamp
    """
    changefreq = "monthly"
    priority = 0.9

    def items(self):
        # Only include active categories
        return Category.objects.filter(is_active=True).order_by('-updated_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('catalog:product_list_by_category', kwargs={'category_slug': obj.slug})


# Sitemap dictionary for URL configuration
sitemaps = {
    'static': StaticViewSitemap(),
    'products': ProductSitemap(),
    'categories': CategorySitemap(),
}
