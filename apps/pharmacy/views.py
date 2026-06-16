from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.http import JsonResponse
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import authenticate, login as auth_login
from .models import Pharmacy, Drug, PharmacyStock, PharmacyRating, PharmacyOpeningHours
from .forms import PharmacyRegistrationForm, PharmacyStockForm, PharmacySearchForm
from .utils.distance import find_nearby_pharmacies, find_pharmacies_with_drug, haversine_distance
import json
import math


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

@login_required
def pharmacy_register(request):
    """Register a new pharmacy"""
    # Check if user already owns a pharmacy
    existing_pharmacy = Pharmacy.objects.filter(owner=request.user).first()
    if existing_pharmacy:
        messages.warning(request, 'You already have a registered pharmacy.')
        return redirect('pharmacy_dashboard')
    
    if request.method == 'POST':
        form = PharmacyRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            pharmacy = form.save(commit=False)
            pharmacy.owner = request.user
            pharmacy.status = 'pending'
            pharmacy.save()
            
            messages.success(
                request, 
                'Pharmacy registered successfully! Waiting for admin approval.'
            )
            return redirect('pharmacy_dashboard')
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
    
    # Get recent orders (if implemented)
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

@login_required
def pharmacy_list(request):
    """List all approved pharmacies with search and filters"""
    pharmacies = Pharmacy.objects.filter(status='approved', is_active=True)
    
    # Search by name, city, or address
    search_query = request.GET.get('search', '')
    if search_query:
        pharmacies = pharmacies.filter(
            Q(name__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(address__icontains=search_query)
        )
    
    # Filter by city
    city = request.GET.get('city', '')
    if city:
        pharmacies = pharmacies.filter(city__icontains=city)
    
    # Get user location for distance calculation
    user_lat = request.user.latitude
    user_lon = request.user.longitude
    
    # Calculate distance for each pharmacy
    pharmacy_list = []
    for pharmacy in pharmacies:
        if user_lat and user_lon and pharmacy.latitude and pharmacy.longitude:
            distance = haversine_distance(
                user_lat, user_lon, 
                pharmacy.latitude, pharmacy.longitude
            )
        else:
            distance = None
        
        # Get stock count
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
    
    # Sort by distance if available
    if user_lat and user_lon:
        pharmacy_list.sort(key=lambda x: x['distance'] if x['distance'] else float('inf'))
    
    # Pagination
    paginator = Paginator(pharmacy_list, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique cities for filter
    cities = Pharmacy.objects.filter(
        status='approved', 
        is_active=True
    ).values_list('city', flat=True).distinct()
    
    context = {
        'pharmacies': page_obj,
        'search_query': search_query,
        'city_filter': city,
        'cities': cities,
        'user_location_set': user_lat is not None,
    }
    return render(request, 'pharmacy/pharmacy_list.html', context)


@login_required
def pharmacy_detail(request, pk):
    """View pharmacy details"""
    pharmacy = get_object_or_404(Pharmacy, id=pk, status='approved', is_active=True)
    
    # Get user location for distance
    user_lat = request.user.latitude
    user_lon = request.user.longitude
    
    distance = None
    if user_lat and user_lon and pharmacy.latitude and pharmacy.longitude:
        distance = haversine_distance(
            user_lat, user_lon, 
            pharmacy.latitude, pharmacy.longitude
        )
    
    # Get stock items
    stock_items = PharmacyStock.objects.filter(
        pharmacy=pharmacy,
        is_available=True,
        available_quantity__gt=0
    ).select_related('drug')
    
    # Get ratings
    ratings = PharmacyRating.objects.filter(pharmacy=pharmacy).select_related('user')
    avg_rating = ratings.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Check if user has already rated
    user_rating = None
    if request.user.is_authenticated:
        user_rating = PharmacyRating.objects.filter(
            pharmacy=pharmacy, 
            user=request.user
        ).first()
    
    context = {
        'pharmacy': pharmacy,
        'distance': distance,
        'stock_items': stock_items,
        'ratings': ratings[:10],
        'total_ratings': ratings.count(),
        'avg_rating': round(avg_rating, 1),
        'user_rating': user_rating,
        'is_open': pharmacy.is_open_now(),
    }
    return render(request, 'pharmacy/pharmacy_detail.html', context)


@login_required
def pharmacy_search(request):
    """Search for pharmacies with specific drugs"""
    form = PharmacySearchForm(request.GET or None)
    results = []
    search_performed = False
    
    user_lat = request.user.latitude
    user_lon = request.user.longitude
    
    if form.is_valid() and request.GET:
        search_performed = True
        drug_name = form.cleaned_data.get('drug_name')
        city = form.cleaned_data.get('city')
        
        # Start with approved pharmacies
        pharmacies = Pharmacy.objects.filter(status='approved', is_active=True)
        
        if city:
            pharmacies = pharmacies.filter(city__icontains=city)
        
        # If drug name provided, find pharmacies with that drug
        if drug_name:
            # Find pharmacies that have the drug in stock
            pharmacy_ids = PharmacyStock.objects.filter(
                drug__name__icontains=drug_name,
                is_available=True,
                available_quantity__gt=0
            ).values_list('pharmacy_id', flat=True).distinct()
            
            pharmacies = pharmacies.filter(id__in=pharmacy_ids)
        
        # Calculate distances
        for pharmacy in pharmacies:
            if user_lat and user_lon and pharmacy.latitude and pharmacy.longitude:
                distance = haversine_distance(
                    user_lat, user_lon, 
                    pharmacy.latitude, pharmacy.longitude
                )
            else:
                distance = None
            
            # Get stock for this drug
            stock = None
            if drug_name:
                stock = PharmacyStock.objects.filter(
                    pharmacy=pharmacy,
                    drug__name__icontains=drug_name,
                    is_available=True,
                    available_quantity__gt=0
                ).first()
            
            results.append({
                'pharmacy': pharmacy,
                'distance': distance,
                'stock': stock,
                'rating': pharmacy.average_rating,
            })
        
        # Sort by distance
        if user_lat and user_lon:
            results.sort(key=lambda x: x['distance'] if x['distance'] else float('inf'))
    
    context = {
        'form': form,
        'results': results[:20],
        'search_performed': search_performed,
        'user_location_set': user_lat is not None,
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
