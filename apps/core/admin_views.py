from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from functools import wraps

from apps.pharmacy.models import Pharmacy
from apps.core.models import User, SymptomPrediction


def admin_required(function=None, redirect_field_name='next', login_url='admin_login'):
    """Decorator for views that checks admin access."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.is_staff:
                return view_func(request, *args, **kwargs)
            
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            login_url_with_next = f"{reverse(login_url)}?{redirect_field_name}={request.get_full_path()}"
            return HttpResponseRedirect(login_url_with_next)
        return _wrapped_view
    
    if function:
        return decorator(function)
    return decorator


def admin_login_view(request):
    """Custom admin login page"""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff:
            login(request, user)
            next_url = request.GET.get('next', 'admin_dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid admin credentials or you do not have admin access.')
    
    return render(request, 'admin_panel/login.html')


@admin_required
def admin_dashboard(request):
    """Admin dashboard with all statistics"""
    total_users = User.objects.count()
    # Only count patients (not pharmacy owners)
    total_patients = User.objects.filter(user_type='patient').count()
    total_pharmacies = Pharmacy.objects.count()
    pending_pharmacies = Pharmacy.objects.filter(status='pending').count()
    approved_pharmacies = Pharmacy.objects.filter(status='approved').count()
    total_predictions = SymptomPrediction.objects.count()
    
    # Recent activity
    recent_predictions = SymptomPrediction.objects.select_related('user').order_by('-created_at')[:8]
    recent_pharmacies = Pharmacy.objects.select_related('owner').order_by('-created_at')[:8]
    
    # Monthly stats
    from django.utils.timezone import now, timedelta
    thirty_days_ago = now() - timedelta(days=30)
    new_users = User.objects.filter(date_joined__gte=thirty_days_ago).count()
    new_patients = User.objects.filter(user_type='patient', date_joined__gte=thirty_days_ago).count()
    new_predictions = SymptomPrediction.objects.filter(created_at__gte=thirty_days_ago).count()
    new_pharmacies = Pharmacy.objects.filter(created_at__gte=thirty_days_ago).count()
    
    context = {
        'total_users': total_users,
        'total_patients': total_patients,
        'total_pharmacies': total_pharmacies,
        'pending_pharmacies': pending_pharmacies,
        'approved_pharmacies': approved_pharmacies,
        'total_predictions': total_predictions,
        'recent_predictions': recent_predictions,
        'recent_pharmacies': recent_pharmacies,
        'new_users': new_users,
        'new_patients': new_patients,
        'new_predictions': new_predictions,
        'new_pharmacies': new_pharmacies,
    }
    return render(request, 'admin_panel/dashboard.html', context)


@admin_required
def admin_users(request):
    """List and manage patients only (not pharmacy owners)"""
    # Filter to only show patients (user_type is 'patient' or 'both')
    users = User.objects.filter(
        Q(user_type='patient') | Q(user_type='both')
    ).order_by('-date_joined')
    
    search = request.GET.get('search', '')
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Also show pharmacy owners count for reference
    pharmacy_owners_count = User.objects.filter(user_type='pharmacy_owner').count()
    
    return render(request, 'admin_panel/users.html', {
        'users': users, 
        'search': search,
        'pharmacy_owners_count': pharmacy_owners_count,
    })


@admin_required
def admin_predictions(request):
    """List symptom analyses"""
    predictions = SymptomPrediction.objects.select_related('user').order_by('-created_at')
    search = request.GET.get('search', '')
    if search:
        predictions = predictions.filter(
            Q(user__username__icontains=search) |
            Q(predicted_disease__icontains=search) |
            Q(symptoms__icontains=search)
        )
    return render(request, 'admin_panel/predictions.html', {'predictions': predictions, 'search': search})


@admin_required
def admin_pharmacies(request):
    """Comprehensive pharmacy management"""
    pharmacies = Pharmacy.objects.select_related('owner').order_by('-created_at')
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    if search:
        pharmacies = pharmacies.filter(
            Q(name__icontains=search) |
            Q(owner__username__icontains=search) |
            Q(city__icontains=search) |
            Q(email__icontains=search)
        )
    if status_filter:
        pharmacies = pharmacies.filter(status=status_filter)
    
    # Counts for each status
    status_counts = {
        'pending': Pharmacy.objects.filter(status='pending').count(),
        'approved': Pharmacy.objects.filter(status='approved').count(),
        'rejected': Pharmacy.objects.filter(status='rejected').count(),
        'suspended': Pharmacy.objects.filter(status='suspended').count(),
    }
    
    if request.method == 'POST':
        pharmacy_id = request.POST.get('pharmacy_id')
        action = request.POST.get('action')
        pharmacy = get_object_or_404(Pharmacy, id=pharmacy_id)
        
        if action == 'approve':
            pharmacy.status = 'approved'
            pharmacy.is_active = True
            pharmacy.approved_at = timezone.now()
            pharmacy.approved_by = request.user
            pharmacy.rejection_reason = ''
            pharmacy.save()
            messages.success(request, f'✅ {pharmacy.name} approved successfully.')
        elif action == 'verify':
            pharmacy.verified_badge = True
            pharmacy.save()
            messages.success(request, f'✅ {pharmacy.name} marked as verified.')
        elif action == 'unverify':
            pharmacy.verified_badge = False
            pharmacy.save()
            messages.info(request, f'ℹ️ {pharmacy.name} unverified.')
        elif action == 'reject':
            pharmacy.status = 'rejected'
            pharmacy.is_active = False
            pharmacy.rejection_reason = request.POST.get('reason', 'Rejected by admin.')
            pharmacy.save()
            messages.warning(request, f'❌ {pharmacy.name} rejected.')
        elif action == 'suspend':
            pharmacy.status = 'suspended'
            pharmacy.is_active = False
            pharmacy.rejection_reason = request.POST.get('reason', 'Suspended by admin.')
            pharmacy.save()
            messages.warning(request, f'⛔ {pharmacy.name} suspended.')
        elif action == 'restore':
            pharmacy.status = 'pending'
            pharmacy.is_active = True
            pharmacy.rejection_reason = ''
            pharmacy.save()
            messages.info(request, f'🔄 {pharmacy.name} restored to pending.')
        elif action == 'remove':
            pharmacy.delete()
            messages.success(request, f'🗑️ {pharmacy.name} removed permanently.')
        
        return redirect('admin_pharmacies')
    
    context = {
        'pharmacies': pharmacies,
        'search': search,
        'status_filter': status_filter,
        'status_counts': status_counts,
    }
    return render(request, 'admin_panel/pharmacies.html', context)


@admin_required
def admin_pharmacy_owners(request):
    """List pharmacy owners separately"""
    owners = User.objects.filter(
        Q(user_type='pharmacy_owner') | Q(user_type='both')
    ).order_by('-date_joined')
    
    search = request.GET.get('search', '')
    if search:
        owners = owners.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    return render(request, 'admin_panel/pharmacy_owners.html', {'owners': owners, 'search': search})