from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Count, Avg, Q
from django.http import JsonResponse
from django.core.paginator import Paginator

from apps.pharmacy.models import Drug, Pharmacy
from .forms import *
from .models import User, Prediction, Prescription, Medicine, UserHealthProfile, UserMedication, SymptomPrediction
# from .utils.ml_predictor import predictor
from datetime import datetime
import math

import json
from .utils.symptom_analyser import symptom_analyzer
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@staff_member_required
def admin_dashboard(request):
    """Simple admin dashboard for managing pharmacies, patients, and predictions."""
    total_users = User.objects.count()
    total_patients = User.objects.filter(is_staff=False).count()
    total_pharmacies = Pharmacy.objects.count()
    total_predictions = Prediction.objects.count()
    recent_predictions = Prediction.objects.select_related('user').order_by('-created_at')[:8]

    context = {
        'total_users': total_users,
        'total_patients': total_patients,
        'total_pharmacies': total_pharmacies,
        'total_predictions': total_predictions,
        'recent_predictions': recent_predictions,
    }
    return render(request, 'admin_panel/dashboard.html', context)


@staff_member_required
def admin_users(request):
    """List all non-staff users (patients)."""
    users = User.objects.filter(is_staff=False).order_by('-date_joined')
    search = request.GET.get('search', '')
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    return render(request, 'admin_panel/users.html', {'users': users, 'search': search})


@staff_member_required
def admin_predictions(request):
    """List symptom predictions made by users."""
    predictions = Prediction.objects.select_related('user').order_by('-created_at')
    search = request.GET.get('search', '')
    if search:
        predictions = predictions.filter(
            Q(user__username__icontains=search) |
            Q(predicted_drug__icontains=search)
        )
    return render(request, 'admin_panel/predictions.html', {'predictions': predictions, 'search': search})


@staff_member_required
def admin_pharmacies(request):
    """List and update pharmacy records."""
    pharmacies = Pharmacy.objects.select_related('owner').order_by('-created_at')
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')

    if search:
        pharmacies = pharmacies.filter(
            Q(name__icontains=search) |
            Q(owner__username__icontains=search) |
            Q(city__icontains=search)
        )
    if status:
        pharmacies = pharmacies.filter(status=status)

    return render(request, 'admin_panel/pharmacies.html', {
        'pharmacies': pharmacies,
        'search': search,
        'status': status,
    })


def home_view(request):
    """Home page view"""
    if request.user.is_authenticated:
        if request.user.is_pharmacy_owner:
            return redirect('pharmacy_dashboard')
        return redirect('dashboard')
    
    # Get some statistics for the home page
    total_pharmacies = Pharmacy.objects.filter(status='approved', is_active=True).count()
    total_medicines = Drug.objects.count()
    
    context = {
        'total_pharmacies': total_pharmacies,
        'total_medicines': total_medicines,
    }
    return render(request, 'home.html', context)


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SignupForm()
    
    return render(request, 'accounts/signup.html', {'form': form})


def signup_stage1(request):
    """Stage 1: Basic account creation"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = Stage1SignupForm(request.POST)
        if form.is_valid():
            # Create user but don't activate yet
            user = form.save(commit=False)
            user.is_active = True
            user.save()
            
            # Log the user in
            login(request, user)
            
            # Redirect to stage 2
            return redirect('signup_stage2')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = Stage1SignupForm()
    
    return render(request, 'accounts/signup_stage1.html', {'form': form, 'stage': 1})


@login_required
def signup_stage2(request):
    """Stage 2: Personal details"""
    # Check if user already completed profile
    if request.user.first_name and request.user.phone_number:
        return redirect('signup_stage3')
    
    if request.method == 'POST':
        form = Stage2ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Personal details saved!')
            return redirect('signup_stage3')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = Stage2ProfileForm(instance=request.user)
    
    return render(request, 'accounts/signup_stage2.html', {'form': form, 'stage': 2})


@login_required
def signup_stage3(request):
    """Stage 3: Optional health status"""
    health_profile = getattr(request.user, 'health_profile', None)

    if request.method == 'POST':
        form = Stage3HealthForm(request.POST)
        if form.is_valid():
            bp = form.cleaned_data.get('bp') or ''
            cholesterol = form.cleaned_data.get('cholesterol') or ''
            na_to_k = form.cleaned_data.get('na_to_k')

            if bp or cholesterol or na_to_k is not None:
                health_profile = health_profile or UserHealthProfile(user=request.user)
                health_profile.bp = bp
                health_profile.cholesterol = cholesterol
                health_profile.na_to_k = na_to_k
                health_profile.save()
                messages.success(request, 'Health details saved.')

            return redirect('signup_stage4')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        initial = {
            'bp': health_profile.bp if health_profile and health_profile.bp else '',
            'cholesterol': health_profile.cholesterol if health_profile and health_profile.cholesterol else '',
            'na_to_k': health_profile.na_to_k if health_profile and health_profile.na_to_k is not None else '',
        }
        form = Stage3HealthForm(initial=initial)

    return render(request, 'accounts/signup_stage3.html', {'form': form, 'stage': 3})


@login_required
def signup_stage4(request):
    """Stage 4: Optional medications"""
    current_meds = UserMedication.objects.filter(user=request.user).values_list('medication_name', flat=True)
    
    if request.method == 'POST':
        form = Stage4MedicationsForm(request.POST)
        if form.is_valid():
            UserMedication.objects.filter(user=request.user).delete()
            
            for med in form.cleaned_data.get('medications', []):
                UserMedication.objects.create(user=request.user, medication_name=med)
            
            other_meds = form.cleaned_data.get('other_medications', '')
            if other_meds:
                for med in other_meds.replace('\n', ',').split(','):
                    med = med.strip()
                    if med:
                        UserMedication.objects.get_or_create(user=request.user, medication_name=med)
            
            messages.success(request, 'Setup complete! Welcome to DrugTrack!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        initial = {'medications': list(current_meds)}
        form = Stage4MedicationsForm(initial=initial)
    
    return render(request, 'accounts/signup_stage4.html', {'form': form, 'stage': 4, 'current_meds': current_meds})


@login_required
def complete_profile(request):
    """Redirect user to appropriate stage based on profile completion"""
    user = request.user
    
    # Check what's missing
    if not user.first_name or not user.phone_number:
        return redirect('signup_stage2')
    
    try:
        health_profile = user.health_profile
        if not health_profile.bp:
            return redirect('signup_stage3')
    except UserHealthProfile.DoesNotExist:
        return redirect('signup_stage3')
    
    # Check if medications were added (optional, so don't force)
    return redirect('dashboard')


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_pharmacy_owner:
            return redirect('pharmacy_dashboard')
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            if user.is_pharmacy_owner:
                return redirect('pharmacy_dashboard')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def dashboard_view(request):
    user = request.user
    total_predictions = Prediction.objects.filter(user=user).count()
    latest_prediction = Prediction.objects.filter(user=user).first()
    total_prescriptions = Prescription.objects.filter(user=user).count()
    recent_predictions = Prediction.objects.filter(user=user)[:5]

    health_profile = getattr(user, 'health_profile', None)
    profile_complete = bool(
        user.first_name and user.last_name and user.phone_number and user.gender and user.age
    )

    latest_metrics = None
    if latest_prediction:
        latest_metrics = {
            'bp': latest_prediction.bp,
            'cholesterol': latest_prediction.cholesterol,
            'drug': latest_prediction.predicted_drug,
            'created_at': latest_prediction.created_at,
        }

    context = {
        'total_predictions': total_predictions,
        'latest_prediction': latest_prediction,
        'total_prescriptions': total_prescriptions,
        'latest_metrics': latest_metrics,
        'recent_predictions': recent_predictions,
        'profile_complete': profile_complete,
        'health_profile': health_profile,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    
    # Get user stats
    total_predictions = Prediction.objects.filter(user=request.user).count()
    total_prescriptions = Prescription.objects.filter(user=request.user).count()
    most_predicted = Prediction.objects.filter(user=request.user).values('predicted_drug').annotate(
        count=Count('predicted_drug')
    ).order_by('-count').first()
    
    context = {
        'form': form,
        'total_predictions': total_predictions,
        'total_prescriptions': total_prescriptions,
        'most_predicted': most_predicted,
    }
    return render(request, 'core/profile.html', context)

@login_required
def prescription_upload_view(request):
    if request.method == 'POST':
        form = PrescriptionForm(request.POST, request.FILES)
        if form.is_valid():
            prescription = form.save(commit=False)
            prescription.user = request.user
            prescription.save()
            messages.success(request, 'Prescription uploaded successfully!')
            return redirect('prescription_list')
    else:
        form = PrescriptionForm()
    
    return render(request, 'core/prescription_upload.html', {'form': form})

@login_required
def prescription_list_view(request):
    prescriptions = Prescription.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'core/prescription_list.html', {'prescriptions': prescriptions})

@login_required
def delete_prescription_view(request, pk):
    prescription = get_object_or_404(Prescription, id=pk, user=request.user)
    if request.method == 'POST':
        prescription.delete()
        messages.success(request, 'Prescription deleted successfully.')
    return redirect('prescription_list')



@login_required
def update_health(request):
    """Update user's health profile"""
    if request.method == 'POST':
        health_profile, created = UserHealthProfile.objects.get_or_create(user=request.user)
        health_profile.bp = request.POST.get('bp')
        health_profile.cholesterol = request.POST.get('cholesterol')
        health_profile.na_to_k = request.POST.get('na_to_k')
        health_profile.save()
        messages.success(request, 'Health information updated successfully!')
    return redirect('profile')


@login_required
def remove_medication(request, med_id):
    """Remove a medication from user's list"""
    medication = get_object_or_404(UserMedication, id=med_id, user=request.user)
    medication.delete()
    messages.success(request, 'Medication removed successfully.')
    return redirect('profile')


@login_required
def symptom_checker_view(request):
    """Render the symptom checker page"""
    return render(request, 'core/symptom_checker.html')


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def analyze_symptoms_api(request):
    """API endpoint to analyze symptoms using Groq"""
    try:
        data = json.loads(request.body)
        symptoms_text = data.get('symptoms', '')
        
        if not symptoms_text:
            return JsonResponse({'error': 'No symptoms provided'}, status=400)
        
        # Get prediction from Groq
        result = symptom_analyzer.predict_disease(symptoms_text)
        
        # Save to database
        symptom_prediction = SymptomPrediction.objects.create(
            user=request.user,
            symptoms=symptoms_text,
            predicted_disease=result.get('predicted_disease', 'Unknown'),
            confidence_score=result.get('confidence_score', 0),
            severity=result.get('severity', 'Unknown'),
            reasoning=result.get('reasoning', ''),
            suggested_drugs=result.get('suggested_drugs', []),
            common_symptoms_matched=result.get('common_symptoms_matched', []),
            full_response=result
        )
        
        # Add advice based on severity
        severity_advice = {
            "Mild": "Rest and over-the-counter medications may help. Monitor symptoms.",
            "Moderate": "Consider scheduling a doctor's appointment within 24-48 hours.",
            "Severe": "Seek medical attention promptly."
        }
        result['general_advice'] = severity_advice.get(
            result.get('severity', ''), 
            "Consult a healthcare provider."
        )
        
        # Add drug interaction warning
        if result.get('confidence_score', 0) > 60:
            result['interaction_warning'] = "Always inform your doctor about any medications you're currently taking."
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def symptom_history_view(request):
    """View past symptom analyses with search and filter"""
    predictions = SymptomPrediction.objects.filter(user=request.user)
    
    # Get filter parameters
    severity_filter = request.GET.get('severity', '')
    search_query = request.GET.get('search', '')
    
    # Apply severity filter
    if severity_filter:
        predictions = predictions.filter(severity=severity_filter)
    
    # Apply search filter
    if search_query:
        predictions = predictions.filter(
            Q(symptoms__icontains=search_query) |
            Q(predicted_disease__icontains=search_query) |
            Q(suggested_drugs__icontains=search_query)
        )
    
    # Order by newest first
    predictions = predictions.order_by('-created_at')
    
    # Pagination (12 per page)
    paginator = Paginator(predictions, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics for the filtered queryset
    total_predictions = predictions.count()
    
    # Most common disease
    most_common_disease = predictions.values('predicted_disease').annotate(
        count=Count('predicted_disease')
    ).order_by('-count').first()
    
    # Severity counts
    severity_counts = {}
    for p in predictions:
        severity_counts[p.severity] = severity_counts.get(p.severity, 0) + 1
    
    # Disease distribution for chart
    disease_counts = {}
    for p in predictions:
        disease_counts[p.predicted_disease] = disease_counts.get(p.predicted_disease, 0) + 1
    
    context = {
        'predictions': page_obj,
        'total_predictions': total_predictions,
        'most_common_disease': most_common_disease,
        'severity_counts': severity_counts,
        'disease_labels': list(disease_counts.keys()),
        'disease_data': list(disease_counts.values()),
        'current_severity': severity_filter,
        'current_search': search_query,
    }
    return render(request, 'core/symptom_history.html', context)


@login_required
def symptom_detail_view(request, pk):
    """View detailed symptom analysis"""
    prediction = get_object_or_404(SymptomPrediction, id=pk, user=request.user)
    return render(request, 'core/symptom_detail.html', {'prediction': prediction})
