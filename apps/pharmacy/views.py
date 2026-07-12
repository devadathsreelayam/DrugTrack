from decimal import Decimal

from django.db import models, transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.http import JsonResponse
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import authenticate, get_user_model, login as auth_login
from .models import Order, OrderItem, Pharmacy, Drug, PharmacyStock, PharmacyRating, PharmacyOpeningHours
from .forms import OrderCreateForm, OrderStatusUpdateForm, PharmacyRegistrationForm, PharmacyStockForm, PharmacySearchForm
from .utils.distance import find_nearby_pharmacies, find_pharmacies_with_drug, haversine_distance
import json
import math


User = get_user_model()

# ======================================================
# PHARMACY REGISTRATION & AUTHENTICATION
# ======================================================


def pharmacy_login_view(request):
    """Pharmacy login view"""
    if request.user.is_authenticated:
        # Check if user owns a pharmacy
        if Pharmacy.objects.filter(owner=request.user).exists():
            return redirect('pharmacy_dashboard')
        else:
            return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            auth_login(request, user)
            # Check if user owns a pharmacy
            if Pharmacy.objects.filter(owner=user).exists():
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('pharmacy_dashboard')
            else:
                messages.info(request, 'You need to register a pharmacy first.')
                return redirect('pharmacy_register')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'pharmacy/pharmacy_login.html')


def pharmacy_register(request):
    """Register a new pharmacy with automatic user account creation"""
    
    if request.method == 'POST':
        form = PharmacyRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Create user account
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data.get('owner_name', ''),
                )
                
                # Create pharmacy
                pharmacy = form.save(commit=False)
                pharmacy.owner = user
                pharmacy.status = 'pending'
                pharmacy.save()
                
                # Log the user in
                auth_login(request, user)
                
                messages.success(
                    request, 
                    '🎉 Your pharmacy has been registered successfully! '
                    'Your account has been created and you will be notified once your pharmacy is approved.'
                )
                return redirect('pharmacy_dashboard')
                
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
                # Clean up if user was created but pharmacy failed
                if 'user' in locals():
                    user.delete()
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PharmacyRegistrationForm()
    
    return render(request, 'pharmacy/pharmacy_register.html', {'form': form})


@login_required
def pharmacy_dashboard(request):
    """Pharmacy owner dashboard"""
    try:
        pharmacy = Pharmacy.objects.get(owner=request.user)
    except Pharmacy.DoesNotExist:
        messages.info(request, 'You need to register a pharmacy first.')
        return redirect('pharmacy_register')
    
    # Get stock items with low stock
    low_stock_items = PharmacyStock.objects.filter(
        pharmacy=pharmacy,
        available_quantity__lte=models.F('reorder_level'),
        is_available=True
    )
    
    # Get statistics
    total_products = PharmacyStock.objects.filter(pharmacy=pharmacy).count()
    total_available = PharmacyStock.objects.filter(
        pharmacy=pharmacy, 
        is_available=True,
        available_quantity__gt=0
    ).count()
    
    # Get ratings
    ratings = PharmacyRating.objects.filter(pharmacy=pharmacy)
    avg_rating = ratings.aggregate(Avg('rating'))['rating__avg'] or 0
    total_ratings = ratings.count()
    
    context = {
        'pharmacy': pharmacy,
        'low_stock_items': low_stock_items[:10],
        'low_stock_count': low_stock_items.count(),
        'total_products': total_products,
        'total_available': total_available,
        'avg_rating': round(avg_rating, 1),
        'total_ratings': total_ratings,
        'status_badge': _get_status_badge(pharmacy.status),
    }
    return render(request, 'pharmacy/pharmacy_dashboard.html', context)


def _get_status_badge(status):
    """Helper to get status badge class"""
    badges = {
        'pending': 'warning',
        'approved': 'success',
        'rejected': 'danger',
        'suspended': 'secondary',
    }
    return badges.get(status, 'secondary')


# ======================================================
# PUBLIC PHARMACY LISTING & SEARCH
# ======================================================

def pharmacy_list(request):
    """List all approved pharmacies with search and filters."""
    pharmacies = Pharmacy.objects.filter(status='approved', is_active=True)
    
    search_query = request.GET.get('search', '')
    if search_query:
        pharmacies = pharmacies.filter(
            Q(name__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(address__icontains=search_query)
        )
    
    city = request.GET.get('city', '')
    if city:
        pharmacies = pharmacies.filter(city__icontains=city)
    
    user_lat = request.user.latitude if request.user.is_authenticated else None
    user_lon = request.user.longitude if request.user.is_authenticated else None
    
    pharmacy_list = []
    for pharmacy in pharmacies:
        if user_lat and user_lon and pharmacy.latitude and pharmacy.longitude:
            distance = haversine_distance(user_lat, user_lon, pharmacy.latitude, pharmacy.longitude)
        else:
            distance = None
        
        stock_count = PharmacyStock.objects.filter(
            pharmacy=pharmacy,
            is_available=True,
            available_quantity__gt=0
        ).count()
        
        pharmacy_list.append({
            'pharmacy': pharmacy,
            'distance': distance,
            'stock_count': stock_count,
            'rating': pharmacy.average_rating,
            'total_ratings': pharmacy.total_ratings,
        })
    
    if user_lat and user_lon:
        pharmacy_list.sort(key=lambda x: x['distance'] if x['distance'] else float('inf'))
    
    paginator = Paginator(pharmacy_list, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    cities = Pharmacy.objects.filter(
        status='approved', 
        is_active=True
    ).values_list('city', flat=True).distinct()

    context = {
        'pharmacies': page_obj,
        'search_query': search_query,
        'city_filter': city,
        'cities': cities,
        'user_location_set': user_lat is not None and user_lon is not None,
    }
    return render(request, 'pharmacy/pharmacy_list.html', context)


@login_required
def pharmacy_detail(request, pk):
    """View pharmacy details with direct order option"""
    pharmacy = get_object_or_404(Pharmacy, id=pk, status='approved', is_active=True)
    
    user_lat = request.user.latitude
    user_lon = request.user.longitude
    
    distance = None
    if user_lat and user_lon and pharmacy.latitude and pharmacy.longitude:
        distance = haversine_distance(user_lat, user_lon, pharmacy.latitude, pharmacy.longitude)
    
    stock_items = PharmacyStock.objects.filter(
        pharmacy=pharmacy,
        is_available=True,
        available_quantity__gt=0
    ).select_related('drug')
    
    ratings = PharmacyRating.objects.filter(pharmacy=pharmacy).select_related('user')
    avg_rating = ratings.aggregate(Avg('rating'))['rating__avg'] or 0
    
    user_rating = None
    is_owner = request.user.is_authenticated and pharmacy.owner_id == request.user.id
    if request.user.is_authenticated and not is_owner:
        user_rating = PharmacyRating.objects.filter(
            pharmacy=pharmacy,
            user=request.user
        ).first()
    
    # Handle direct order
    if request.method == 'POST' and 'buy_now' in request.POST:
        stock_id = request.POST.get('stock_id')
        quantity = int(request.POST.get('quantity', 1))
        
        try:
            stock = PharmacyStock.objects.get(id=stock_id, pharmacy=pharmacy, is_available=True)
            if stock.available_quantity >= quantity:
                # Store in session for order creation
                request.session['direct_order'] = {
                    'stock_id': stock.id,
                    'quantity': quantity,
                    'pharmacy_id': pharmacy.id
                }
                request.session.modified = True
                return redirect('create_order_direct')
            else:
                messages.error(request, f'Only {stock.available_quantity} units available.')
        except PharmacyStock.DoesNotExist:
            messages.error(request, 'Selected medicine is not available.')
    
    context = {
        'pharmacy': pharmacy,
        'distance': distance,
        'stock_items': stock_items,
        'ratings': ratings[:10],
        'total_ratings': ratings.count(),
        'avg_rating': round(avg_rating, 1),
        'user_rating': user_rating,
        'is_open': pharmacy.is_open_now(),
        'is_owner': is_owner,
    }
    return render(request, 'pharmacy/pharmacy_detail.html', context)


@login_required
def pharmacy_search(request):
    """Search for pharmacies with multiple drugs"""
    form = PharmacySearchForm(request.GET or None)
    results = []
    search_performed = False
    
    user_lat = request.user.latitude
    user_lon = request.user.longitude
    
    if form.is_valid() and request.GET:
        search_performed = True
        drug_names = form.cleaned_data.get('drug_names', [])
        city = form.cleaned_data.get('city')
        radius = form.cleaned_data.get('radius', 10)
        radius = radius if radius else float('inf')
        match_type = form.cleaned_data.get('match_type', 'any')
        
        # Start with approved pharmacies
        pharmacies = Pharmacy.objects.filter(status='approved', is_active=True)
        
        if city:
            pharmacies = pharmacies.filter(city__icontains=city)
        
        # If drugs provided, find pharmacies with those drugs
        if drug_names:
            # Build dynamic Q objects for each drug name
            q_objects = Q()
            for name in drug_names:
                q_objects |= Q(name__icontains=name) | Q(generic_name__icontains=name)

            drug_objects = Drug.objects.filter(q_objects).distinct()
            
            # Map drug names to their objects
            drug_map = {}
            for drug in drug_objects:
                for search_name in drug_names:
                    if search_name.lower() in drug.name.lower() or search_name.lower() in (drug.generic_name or '').lower():
                        if drug.id not in drug_map:
                            drug_map[drug.id] = {
                                'drug': drug,
                                'search_names': []
                            }
                        drug_map[drug.id]['search_names'].append(search_name)
            
            # Find pharmacies with stock for these drugs
            pharmacy_results = {}
            for drug_id, drug_info in drug_map.items():
                stock_items = PharmacyStock.objects.filter(
                    drug_id=drug_id,
                    is_available=True,
                    available_quantity__gt=0
                ).select_related('pharmacy', 'drug')
                
                for stock in stock_items:
                    pharmacy_id = stock.pharmacy.id
                    if pharmacy_id not in pharmacy_results:
                        pharmacy_results[pharmacy_id] = {
                            'pharmacy': stock.pharmacy,
                            'drugs_found': [],
                            'total_required': len(drug_map)
                        }
                    pharmacy_results[pharmacy_id]['drugs_found'].append({
                        'drug': stock.drug,
                        'stock': stock,
                        'search_names': drug_info['search_names']
                    })
            
            # Filter by match type
            for pharmacy_id, result in list(pharmacy_results.items()):
                found_count = len(result['drugs_found'])
                total_required = result['total_required']
                
                if match_type == 'all' and found_count < total_required:
                    del pharmacy_results[pharmacy_id]
                elif match_type == 'most' and found_count < total_required / 2:
                    del pharmacy_results[pharmacy_id]
                # 'any' keeps all pharmacies with at least one drug
            
            # Calculate distances and build results
            for pharmacy_id, result in pharmacy_results.items():
                pharmacy = result['pharmacy']
                
                # Calculate distance - handle None properly
                distance = None
                if user_lat is not None and user_lon is not None:
                    if pharmacy.latitude is not None and pharmacy.longitude is not None:
                        try:
                            distance = haversine_distance(
                                user_lat, user_lon, 
                                pharmacy.latitude, pharmacy.longitude
                            )
                        except Exception:
                            distance = None
                        # Only check radius if distance is not None
                        if distance is not None and distance > radius:
                            continue
                
                # Check which drugs were found
                found_drugs = result['drugs_found']
                found_names = [f['drug'].name for f in found_drugs]
                missing_names = [name for name in drug_names if name not in found_names]
                
                results.append({
                    'pharmacy': pharmacy,
                    'distance': distance,
                    'found_drugs': found_drugs,
                    'found_count': len(found_drugs),
                    'total_count': len(drug_names),
                    'missing_count': len(drug_names) - len(found_drugs),
                    'missing_drugs': missing_names,
                    'match_percentage': round((len(found_drugs) / len(drug_names)) * 100) if len(drug_names) > 0 else 0,
                    'rating': pharmacy.average_rating,
                    'total_ratings': pharmacy.total_ratings,
                    'is_open': pharmacy.is_open_now(),
                })
            
            # Sort by match percentage (highest first), then by distance
            # SAFE sorting with None handling
            def safe_sort_key(item):
                match_pct = item.get('match_percentage', 0)
                dist = item.get('distance')
                # Convert None to a very large number
                if dist is None:
                    dist = 999999999
                return (-match_pct, dist)
            
            results.sort(key=safe_sort_key)
        
        else:
            # No drugs specified, just show nearby pharmacies
            for pharmacy in pharmacies:
                distance = None
                if user_lat is not None and user_lon is not None:
                    if pharmacy.latitude is not None and pharmacy.longitude is not None:
                        try:
                            distance = haversine_distance(
                                user_lat, user_lon, 
                                pharmacy.latitude, pharmacy.longitude
                            )
                        except Exception:
                            distance = None
                
                stock_count = PharmacyStock.objects.filter(
                    pharmacy=pharmacy,
                    is_available=True,
                    available_quantity__gt=0
                ).count()
                
                results.append({
                    'pharmacy': pharmacy,
                    'distance': distance,
                    'found_drugs': [],
                    'found_count': 0,
                    'total_count': 0,
                    'missing_count': 0,
                    'missing_drugs': [],
                    'match_percentage': 0,
                    'rating': pharmacy.average_rating,
                    'total_ratings': pharmacy.total_ratings,
                    'is_open': pharmacy.is_open_now(),
                    'stock_count': stock_count,
                })
            
            # Sort by distance (handle None values safely)
            def safe_distance_sort(item):
                dist = item.get('distance')
                if dist is None:
                    return 999999999
                return dist
            
            results.sort(key=safe_distance_sort)
    
    # Get popular drugs for suggestions
    popular_drugs = Drug.objects.filter(
        pharmacy_stock__is_available=True,
        pharmacy_stock__available_quantity__gt=0
    ).distinct().order_by('name')[:20]
    
    context = {
        'form': form,
        'results': results[:30],
        'search_performed': search_performed,
        'user_location_set': user_lat is not None,
        'popular_drugs': popular_drugs,
    }
    return render(request, 'pharmacy/pharmacy_search.html', context)


# ======================================================
# STOCK MANAGEMENT
# ======================================================

@login_required
def stock_management(request):
    """Manage pharmacy stock"""
    try:
        pharmacy = Pharmacy.objects.get(owner=request.user, status='approved')
    except Pharmacy.DoesNotExist:
        messages.error(request, 'You need an approved pharmacy to manage stock.')
        return redirect('pharmacy_register')
    
    stock_items = PharmacyStock.objects.filter(pharmacy=pharmacy).select_related('drug')
    
    # Search filter
    search = request.GET.get('search', '')
    if search:
        stock_items = stock_items.filter(drug__name__icontains=search)
    
    # Filter by availability
    availability = request.GET.get('availability', '')
    if availability == 'available':
        stock_items = stock_items.filter(is_available=True, available_quantity__gt=0)
    elif availability == 'out_of_stock':
        stock_items = stock_items.filter(Q(is_available=False) | Q(available_quantity=0))
    elif availability == 'low_stock':
        stock_items = stock_items.filter(available_quantity__lte=models.F('reorder_level'))
    
    context = {
        'pharmacy': pharmacy,
        'stock_items': stock_items,
        'total_items': stock_items.count(),
        'search': search,
        'availability_filter': availability,
    }
    return render(request, 'pharmacy/stock_management.html', context)


@login_required
def add_stock(request):
    """Add new stock item"""
    try:
        pharmacy = Pharmacy.objects.get(owner=request.user, status='approved')
    except Pharmacy.DoesNotExist:
        messages.error(request, 'You need an approved pharmacy to manage stock.')
        return redirect('pharmacy_register')
    
    if request.method == 'POST':
        form = PharmacyStockForm(request.POST)
        if form.is_valid():
            stock = form.save(commit=False)
            stock.pharmacy = pharmacy
            stock.updated_by = request.user
            stock.save()
            messages.success(request, f'Stock added for {stock.drug.name}')
            return redirect('stock_management')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PharmacyStockForm()
    
    return render(request, 'pharmacy/add_stock.html', {'form': form, 'pharmacy': pharmacy})


@login_required
def edit_stock(request, pk):
    """Edit existing stock item"""
    try:
        pharmacy = Pharmacy.objects.get(owner=request.user, status='approved')
    except Pharmacy.DoesNotExist:
        messages.error(request, 'You need an approved pharmacy to manage stock.')
        return redirect('pharmacy_register')
    
    stock = get_object_or_404(PharmacyStock, id=pk, pharmacy=pharmacy)
    
    if request.method == 'POST':
        form = PharmacyStockForm(request.POST, instance=stock)
        if form.is_valid():
            stock = form.save(commit=False)
            stock.updated_by = request.user
            stock.save()
            messages.success(request, f'Stock updated for {stock.drug.name}')
            return redirect('stock_management')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PharmacyStockForm(instance=stock)
    
    return render(request, 'pharmacy/edit_stock.html', {'form': form, 'stock': stock, 'pharmacy': pharmacy})


@login_required
def delete_stock(request, pk):
    """Delete stock item"""
    try:
        pharmacy = Pharmacy.objects.get(owner=request.user)
    except Pharmacy.DoesNotExist:
        messages.error(request, 'Pharmacy not found.')
        return redirect('pharmacy_dashboard')
    
    stock = get_object_or_404(PharmacyStock, id=pk, pharmacy=pharmacy)
    
    if request.method == 'POST':
        drug_name = stock.drug.name
        stock.delete()
        messages.success(request, f'Removed {drug_name} from stock.')
        return redirect('stock_management')
    
    return render(request, 'pharmacy/delete_stock.html', {'stock': stock})


# ======================================================
# RATINGS & REVIEWS
# ======================================================

@login_required
def rate_pharmacy(request, pk):
    """Rate a pharmacy"""
    pharmacy = get_object_or_404(Pharmacy, id=pk, status='approved', is_active=True)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        review = request.POST.get('review', '')
        
        try:
            rating_value = int(rating)
            if 1 <= rating_value <= 5:
                # Check if user already rated
                existing_rating = PharmacyRating.objects.filter(
                    pharmacy=pharmacy,
                    user=request.user
                ).first()
                
                if existing_rating:
                    existing_rating.rating = rating_value
                    existing_rating.review = review
                    existing_rating.save()
                    messages.success(request, 'Rating updated successfully!')
                else:
                    PharmacyRating.objects.create(
                        pharmacy=pharmacy,
                        user=request.user,
                        rating=rating_value,
                        review=review
                    )
                    messages.success(request, 'Thank you for your rating!')
            else:
                messages.error(request, 'Invalid rating value.')
        except ValueError:
            messages.error(request, 'Invalid rating value.')
        
        return redirect('pharmacy_detail', pk=pk)
    
    return redirect('pharmacy_detail', pk=pk)


# ======================================================
# DIRECT ORDER (No Cart)
# ======================================================

@login_required
def buy_now(request, pharmacy_id, drug_id):
    """Direct buy now - add to session and redirect to order page"""
    pharmacy = get_object_or_404(Pharmacy, id=pharmacy_id, status='approved', is_active=True)
    
    # Get the stock item for this pharmacy and drug
    stock = get_object_or_404(PharmacyStock, pharmacy=pharmacy, drug_id=drug_id, is_available=True)
    
    if stock.available_quantity < 1:
        messages.error(request, f'{stock.drug.name} is out of stock.')
        return redirect('pharmacy_detail', pk=pharmacy_id)
    
    # Store in session for order creation
    request.session['direct_order'] = {
        'stock_id': stock.id,
        'quantity': 1,  # Default quantity, user can change in order page
        'pharmacy_id': pharmacy.id
    }
    request.session.modified = True
    
    return redirect('create_order_direct')


@login_required
def create_order_direct(request):
    """Create order directly from pharmacy detail (no cart)"""
    # Get direct order from session
    direct_order = request.session.get('direct_order')
    
    if not direct_order:
        messages.error(request, 'No items to order.')
        return redirect('pharmacy_list')
    
    try:
        stock = PharmacyStock.objects.get(id=direct_order['stock_id'], is_available=True)
        pharmacy = stock.pharmacy
        quantity = direct_order.get('quantity', 1)
        
        if stock.available_quantity < quantity:
            messages.error(request, f'{stock.drug.name} only has {stock.available_quantity} units available.')
            return redirect('pharmacy_detail', pk=pharmacy.id)
        
    except PharmacyStock.DoesNotExist:
        messages.error(request, 'Item is no longer available.')
        return redirect('pharmacy_list')
    
    # Calculate total
    total_amount = stock.price * quantity
    packaging_charge = Decimal('0.00')
    delivery_charge = Decimal('0.00')
    distance_km = None
    if request.user.latitude is not None and request.user.longitude is not None and pharmacy.latitude is not None and pharmacy.longitude is not None:
        distance_km = haversine_distance(request.user.latitude, request.user.longitude, pharmacy.latitude, pharmacy.longitude)
    
    if request.method == 'POST':
        # Get updated quantity from form
        quantity = int(request.POST.get('quantity', 1))
        if quantity > stock.available_quantity:
            messages.error(request, f'Only {stock.available_quantity} units available.')
            return redirect('create_order_direct')
        
        total_amount = stock.price * quantity
        
        form = OrderCreateForm(request.POST)
        delivery_option = request.POST.get('delivery_option', 'pickup')
        warehouse_distance = distance_km
        packaging_charge = Decimal('0.00')
        delivery_charge = Decimal('0.00')

        if delivery_option == 'delivery':
            packaging_charge = Decimal('25.00')
            delivery_charge = Order.calculate_delivery_charge(warehouse_distance)

        delivery_address = ''
        if delivery_option == 'delivery':
            delivery_address = request.user.address.strip() if getattr(request.user, 'address', '') else ''

        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create order
                    order = Order.objects.create(
                        user=request.user,
                        pharmacy=pharmacy,
                        delivery_option=delivery_option,
                        delivery_address=delivery_address,
                        delivery_charge=delivery_charge,
                        packaging_charge=packaging_charge,
                        total_amount=total_amount + delivery_charge + packaging_charge,
                        notes=form.cleaned_data.get('notes', ''),
                        status='pending'
                    )
                    
                    # Create order item and reduce stock
                    OrderItem.objects.create(
                        order=order,
                        stock=stock,
                        quantity=quantity,
                        price=stock.price,
                        total=total_amount
                    )
                    
                    # Reduce stock
                    stock.available_quantity -= quantity
                    stock.quantity -= quantity
                    stock.save()
                    
                    # Clear session
                    del request.session['direct_order']
                    request.session.modified = True
                    
                    messages.success(request, f'Order {order.order_number} placed successfully!')
                    return redirect('order_detail', order_id=order.id)
                    
            except Exception as e:
                messages.error(request, f'Error placing order: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        # Pre-fill delivery address with user's address if available
        initial = {}
        if request.user.address:
            initial['delivery_address'] = request.user.address
        form = OrderCreateForm(initial=initial)
    
    context = {
        'pharmacy': pharmacy,
        'stock': stock,
        'quantity': quantity,
        'form': form,
        'total_amount': total_amount,
        'packaging_charge': packaging_charge,
        'delivery_charge': delivery_charge,
        'grand_total': total_amount + delivery_charge + packaging_charge,
        'distance_km': distance_km,
    }
    return render(request, 'pharmacy/create_order_direct.html', context)


@login_required
def order_detail(request, order_id):
    """View order details"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'pharmacy/order_detail.html', {'order': order})


@login_required
def order_list(request):
    """View user's orders"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'pharmacy/order_list.html', {'orders': orders})


@login_required
def cancel_order(request, order_id):
    """Cancel an order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if not order.can_cancel():
        messages.error(request, 'This order cannot be cancelled.')
        return redirect('order_detail', order_id=order.id)
    
    if request.method == 'POST':
        with transaction.atomic():
            # Restore stock
            for item in order.items.all():
                stock = item.stock
                stock.available_quantity += item.quantity
                stock.quantity += item.quantity
                stock.save()
            
            order.status = 'cancelled'
            order.save()
        
        messages.success(request, f'Order {order.order_number} cancelled successfully.')
        return redirect('order_list')
    
    return render(request, 'pharmacy/cancel_order.html', {'order': order})


# ======================================================
# PHARMACY ORDER MANAGEMENT
# ======================================================

@login_required
def pharmacy_order_list(request):
    """Pharmacy owner view of orders"""
    try:
        pharmacy = Pharmacy.objects.get(owner=request.user)
    except Pharmacy.DoesNotExist:
        messages.error(request, 'You need to register a pharmacy first.')
        return redirect('pharmacy_register')
    
    orders = Order.objects.filter(pharmacy=pharmacy).order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
        'pharmacy': pharmacy,
    }
    return render(request, 'pharmacy/pharmacy_order_list.html', context)


@login_required
def update_order_status(request, order_id):
    """Pharmacy owner update order status"""
    try:
        pharmacy = Pharmacy.objects.get(owner=request.user)
    except Pharmacy.DoesNotExist:
        messages.error(request, 'You need to register a pharmacy first.')
        return redirect('pharmacy_register')
    
    order = get_object_or_404(Order, id=order_id, pharmacy=pharmacy)
    
    if order.status == 'cancelled' or order.status == 'delivered':
        messages.warning(request, 'This order cannot be updated.')
        return redirect('pharmacy_order_list')
    
    if request.method == 'POST':
        form = OrderStatusUpdateForm(request.POST, instance=order)
        if form.is_valid():
            old_status = order.status
            new_status = form.cleaned_data['status']
            
            # Check if status change is valid
            if old_status == 'out_for_delivery' and new_status != 'delivered':
                messages.error(request, 'Cannot change status after out for delivery.')
                return redirect('pharmacy_order_list')
            
            form.save()
            messages.success(request, f'Order {order.order_number} status updated to {order.get_status_display()}')
            return redirect('pharmacy_order_list')
    else:
        form = OrderStatusUpdateForm(instance=order)
    
    return render(request, 'pharmacy/update_order_status.html', {'order': order, 'form': form})


# ======================================================
# ADMIN VIEWS (Staff only)
# ======================================================

@staff_member_required
def admin_pharmacy_list(request):
    """Admin view to manage all pharmacies"""
    pharmacies = Pharmacy.objects.all().order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        pharmacies = pharmacies.filter(status=status_filter)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        pharmacies = pharmacies.filter(
            Q(name__icontains=search) |
            Q(owner__username__icontains=search) |
            Q(email__icontains=search)
        )
    
    context = {
        'pharmacies': pharmacies,
        'status_filter': status_filter,
        'search': search,
        'status_counts': {
            'pending': Pharmacy.objects.filter(status='pending').count(),
            'approved': Pharmacy.objects.filter(status='approved').count(),
            'rejected': Pharmacy.objects.filter(status='rejected').count(),
            'suspended': Pharmacy.objects.filter(status='suspended').count(),
        }
    }
    return render(request, 'admin/pharmacy_list.html', context)


@staff_member_required
def admin_pharmacy_approve(request, pk):
    """Approve or reject pharmacy registration"""
    pharmacy = get_object_or_404(Pharmacy, id=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('reason', '')
        
        if action == 'approve':
            pharmacy.status = 'approved'
            pharmacy.approved_at = timezone.now()
            pharmacy.approved_by = request.user
            pharmacy.verified_badge = True
            messages.success(request, f'{pharmacy.name} approved successfully!')
        elif action == 'reject':
            pharmacy.status = 'rejected'
            pharmacy.rejection_reason = reason
            messages.warning(request, f'{pharmacy.name} rejected.')
        elif action == 'suspend':
            pharmacy.status = 'suspended'
            pharmacy.is_active = False
            pharmacy.rejection_reason = reason
            messages.warning(request, f'{pharmacy.name} suspended.')
        
        pharmacy.save()
        return redirect('admin_pharmacy_list')
    
    return render(request, 'admin/pharmacy_approve.html', {'pharmacy': pharmacy})
