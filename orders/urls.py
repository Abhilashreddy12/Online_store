from django.urls import path
from . import views
from . import payment_views

app_name = 'orders'

urlpatterns = [
    # Order management
    path('checkout/', views.checkout, name='checkout'),
    path('place-order/', views.place_order, name='place_order'),
    path('my-orders/', views.order_list, name='order_list'),
    path('order/<str:order_number>/', views.order_detail, name='order_detail'),
    path('order/<str:order_number>/cancel/', views.cancel_order, name='cancel_order'),
    
    # Payment endpoints
    path('api/create-razorpay-order/', payment_views.create_razorpay_order, name='create_razorpay_order'),
    path('api/verify-razorpay-payment/', payment_views.verify_razorpay_payment, name='verify_razorpay_payment'),
    path('payment-success/<str:order_number>/', payment_views.payment_success, name='payment_success'),
    path('payment-failure/<str:order_number>/', payment_views.payment_failure, name='payment_failure'),
    
    # Invoice
    path('order/<str:order_number>/download-invoice/', payment_views.download_invoice, name='download_invoice'),
]
