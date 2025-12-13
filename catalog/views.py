from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Avg, Count, F
from django.utils import timezone
from datetime import timedelta
from .models import Product, Category, Brand, Review
from orders.models import OrderItem, Order
from customers.models import Customer


class ProductListView(ListView):
    """Display list of products"""
    model = Product
    template_name = 'catalog/product_list.html'
    context_object_name = 'products'
    paginate_by = 24

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related('category', 'brand')
        
        # Filter by category
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Filter by brand
        brand_slug = self.request.GET.get('brand')
        if brand_slug:
            queryset = queryset.filter(brand__slug=brand_slug)
        
        # Filter by gender
        gender = self.request.GET.get('gender')
        if gender:
            queryset = queryset.filter(gender=gender)
        
        # Sorting
        sort = self.request.GET.get('sort', '-created_at')
        queryset = queryset.order_by(sort)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True, parent=None)
        context['brands'] = Brand.objects.filter(is_active=True)
        return context


class ProductDetailView(DetailView):
    """Display product details"""
    model = Product
    template_name = 'catalog/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related('category', 'brand').prefetch_related(
            'images', 'variants__size', 'variants__color', 'reviews'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['related_products'] = Product.objects.filter(
            category=self.object.category,
            is_active=True
        ).exclude(id=self.object.id)[:4]
        context['approved_reviews'] = self.object.reviews.filter(is_approved=True)
        
        # Check if user can review (must have delivered order with this product)
        if self.request.user.is_authenticated:
            has_purchased = OrderItem.objects.filter(
                order__customer=self.request.user,
                order__status='DELIVERED',
                product=self.object
            ).exists()
            
            has_reviewed = Review.objects.filter(
                product=self.object,
                customer_email=self.request.user.email
            ).exists()
            
            context['can_review'] = has_purchased and not has_reviewed
        else:
            context['can_review'] = False
        
        return context


@login_required
def add_review(request, slug):
    """Add a product review - only for delivered orders"""
    product = get_object_or_404(Product, slug=slug, is_active=True)
    
    # Check if user has purchased and received this product
    has_purchased = OrderItem.objects.filter(
        order__customer=request.user,
        order__status='DELIVERED',
        product=product
    ).exists()
    
    if not has_purchased:
        messages.error(request, 'You can only review products you have purchased and received.')
        return redirect('catalog:product_detail', slug=slug)
    
    # Check if already reviewed
    if Review.objects.filter(product=product, customer_email=request.user.email).exists():
        messages.warning(request, 'You have already reviewed this product.')
        return redirect('catalog:product_detail', slug=slug)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        title = request.POST.get('title')
        comment = request.POST.get('comment')
        
        if not rating or not title or not comment:
            messages.error(request, 'Please fill in all fields.')
            return redirect('catalog:product_detail', slug=slug)
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            messages.error(request, 'Invalid rating. Please select 1-5 stars.')
            return redirect('catalog:product_detail', slug=slug)
        
        # Create review
        Review.objects.create(
            product=product,
            customer_name=request.user.get_full_name() or request.user.username,
            customer_email=request.user.email,
            rating=rating,
            title=title,
            comment=comment,
            is_verified_purchase=True,
            is_approved=False  # Requires admin approval
        )
        
        messages.success(request, 'Thank you for your review! It will be published after approval.')
        return redirect('catalog:product_detail', slug=slug)
    
    return redirect('catalog:product_detail', slug=slug)


def home(request):
    """Homepage view"""
    context = {
        'featured_products': Product.objects.filter(is_active=True, is_featured=True)[:8],
        'categories': Category.objects.filter(is_active=True, parent=None)[:6],
        'new_arrivals': Product.objects.filter(is_active=True).order_by('-created_at')[:8],
    }
    return render(request, 'catalog/home.html', context)


@login_required
def admin_dashboard(request):
    """Admin dashboard with analytics and charts"""
    # Check if user is staff
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access the admin dashboard.')
        return redirect('catalog:home')
    
    # Date ranges
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    last_7_days = today - timedelta(days=7)
    
    # Key Metrics
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(
        status__in=['PROCESSING', 'SHIPPED', 'DELIVERED']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    total_sales = OrderItem.objects.filter(
        order__status__in=['PROCESSING', 'SHIPPED', 'DELIVERED']
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    # Calculate profit (revenue - cost)
    profit_data = OrderItem.objects.filter(
        order__status__in=['PROCESSING', 'SHIPPED', 'DELIVERED']
    ).annotate(
        item_profit=(F('unit_price') - F('product__cost_price')) * F('quantity')
    ).aggregate(total_profit=Sum('item_profit'))
    
    total_profit = profit_data['total_profit'] or 0
    
    # Recent metrics (last 30 days)
    recent_orders_count = Order.objects.filter(created_at__gte=last_30_days).count()
    recent_revenue = Order.objects.filter(
        created_at__gte=last_30_days,
        status__in=['PROCESSING', 'SHIPPED', 'DELIVERED']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Monthly Revenue Data (last 12 months)
    monthly_revenue = []
    for i in range(11, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        revenue = Order.objects.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end,
            status__in=['PROCESSING', 'SHIPPED', 'DELIVERED']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        monthly_revenue.append({
            'month': month_start.strftime('%b %Y'),
            'revenue': float(revenue)
        })
    
    # Sales by Category
    category_sales = OrderItem.objects.filter(
        order__status__in=['PROCESSING', 'SHIPPED', 'DELIVERED']
    ).values('product__category__name').annotate(
        total_sales=Sum('quantity'),
        total_revenue=Sum(F('unit_price') * F('quantity'))
    ).order_by('-total_sales')[:6]
    
    # Top Selling Products
    top_products = OrderItem.objects.filter(
        order__status__in=['PROCESSING', 'SHIPPED', 'DELIVERED']
    ).values('product__name').annotate(
        total_sold=Sum('quantity'),
        revenue=Sum(F('unit_price') * F('quantity'))
    ).order_by('-total_sold')[:10]
    
    # Recent Orders
    recent_orders_list = Order.objects.select_related(
        'customer'
    ).order_by('-created_at')[:10]
    
    # Low Stock Alerts
    low_stock_products = Product.objects.filter(
        is_active=True,
        stock_quantity__gt=0,
        stock_quantity__lte=F('low_stock_threshold')
    ).select_related('category')[:10]
    
    # Out of Stock
    out_of_stock_count = Product.objects.filter(
        is_active=True,
        stock_quantity=0
    ).count()
    
    # Customer Statistics
    total_customers = Customer.objects.count()
    new_customers_30d = Customer.objects.filter(
        user__date_joined__gte=last_30_days
    ).count()
    
    # Order Status Distribution
    order_status_dist = Order.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Average Order Value
    avg_order_value = Order.objects.filter(
        status__in=['PROCESSING', 'SHIPPED', 'DELIVERED']
    ).aggregate(avg=Avg('total_amount'))['avg'] or 0
    
    # Pending Reviews
    pending_reviews_count = Review.objects.filter(is_approved=False).count()
    
    context = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_sales': total_sales,
        'total_profit': total_profit,
        'recent_orders_count': recent_orders_count,
        'recent_revenue': recent_revenue,
        'monthly_revenue': monthly_revenue,
        'category_sales': category_sales,
        'top_products': top_products,
        'recent_orders_list': recent_orders_list,
        'low_stock_products': low_stock_products,
        'out_of_stock_count': out_of_stock_count,
        'total_customers': total_customers,
        'new_customers_30d': new_customers_30d,
        'order_status_dist': order_status_dist,
        'avg_order_value': avg_order_value,
        'pending_reviews_count': pending_reviews_count,
    }
    
    return render(request, 'catalog/admin_dashboard.html', context)
