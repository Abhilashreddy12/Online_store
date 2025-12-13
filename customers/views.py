from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Customer, Address


def register(request):
    """User registration with email support"""
    if request.user.is_authenticated:
        return redirect('catalog:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        # Validation
        errors = []
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters long.')
        if User.objects.filter(username=username).exists():
            errors.append('Username already exists.')
        if email and User.objects.filter(email=email).exists():
            errors.append('Email already registered.')
        if not password1 or len(password1) < 8:
            errors.append('Password must be at least 8 characters long.')
        if password1 != password2:
            errors.append('Passwords do not match.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'customers/register.html', {
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            })
        
        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name
            )
            # Create customer profile
            Customer.objects.create(user=user)
            
            # Auto login
            login(request, user)
            messages.success(request, f'Welcome {username}! Your account has been created successfully.')
            return redirect('catalog:home')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
    
    return render(request, 'customers/register.html')


def user_login(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('catalog:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            # Ensure customer profile exists
            Customer.objects.get_or_create(user=user)
            
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Redirect to next or home
            next_url = request.GET.get('next', 'catalog:home')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'customers/login.html')


@login_required
def user_logout(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('catalog:home')


@login_required
def profile(request):
    """User profile page"""
    customer, created = Customer.objects.get_or_create(user=request.user)
    addresses = Address.objects.filter(customer=request.user)
    
    # Get order statistics
    from orders.models import Order
    orders = Order.objects.filter(customer=request.user)
    total_orders = orders.count()
    delivered_orders = orders.filter(status='DELIVERED')
    
    return render(request, 'customers/profile.html', {
        'customer': customer,
        'addresses': addresses,
        'total_orders': total_orders,
        'delivered_orders': delivered_orders,
    })


@login_required
def add_address(request):
    """Add new address"""
    if request.method == 'POST':
        Address.objects.create(
            customer=request.user,
            address_type=request.POST.get('address_type'),
            full_name=request.POST.get('full_name'),
            phone=request.POST.get('phone'),
            address_line1=request.POST.get('address_line1'),
            address_line2=request.POST.get('address_line2', ''),
            city=request.POST.get('city'),
            state=request.POST.get('state'),
            postal_code=request.POST.get('postal_code'),
            country=request.POST.get('country', 'USA'),
            is_default=request.POST.get('is_default') == 'on'
        )
        messages.success(request, 'Address added successfully!')
        return redirect('customers:profile')
    
    return render(request, 'customers/add_address.html')


@login_required
def edit_address(request, address_id):
    """Edit address"""
    address = get_object_or_404(Address, id=address_id, customer=request.user)
    
    if request.method == 'POST':
        address.full_name = request.POST.get('full_name')
        address.phone = request.POST.get('phone')
        address.address_line1 = request.POST.get('address_line1')
        address.address_line2 = request.POST.get('address_line2', '')
        address.city = request.POST.get('city')
        address.state = request.POST.get('state')
        address.postal_code = request.POST.get('postal_code')
        address.country = request.POST.get('country', 'USA')
        address.is_default = request.POST.get('is_default') == 'on'
        address.save()
        
        messages.success(request, 'Address updated successfully!')
        return redirect('customers:profile')
    
    return render(request, 'customers/edit_address.html', {'address': address})


@login_required
def delete_address(request, address_id):
    """Delete address"""
    address = get_object_or_404(Address, id=address_id, customer=request.user)
    address.delete()
    messages.success(request, 'Address deleted successfully!')
    return redirect('customers:profile')


def register(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('catalog:home')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Customer.objects.create(user=user)
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('catalog:home')
    else:
        form = UserCreationForm()
    
    return render(request, 'customers/register.html', {'form': form})

