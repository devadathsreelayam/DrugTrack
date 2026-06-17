from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone

from apps.pharmacy.models import Drug, Pharmacy
from .forms import *
from .models import User, Prescription, Medicine, UserHealthProfile, UserMedication, SymptomPrediction
from datetime import datetime
import math

import json
from .utils.symptom_analyser import symptom_analyzer
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


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
    """Stage 3: Optional health status - Updated with realistic metrics"""
    health_profile = getattr(request.user, 'health_profile', None)

    if request.method == 'POST':
        form = Stage3HealthForm(request.POST)
        if form.is_valid():
            health_profile = health_profile or UserHealthProfile(user=request.user)
            
            # Update only if values are provided
            if form.cleaned_data.get('bp'):
                health_profile.bp = form.cleaned_data['bp']
            
            if form.cleaned_data.get('cholesterol'):
                health_profile.cholesterol = form.cleaned_data['cholesterol']
            
            if form.cleaned_data.get('blood_sugar'):
                health_profile.blood_sugar = form.cleaned_data['blood_sugar']
            
            if form.cleaned_data.get('weight') is not None:
                health_profile.weight = form.cleaned_data['weight']
            
            if form.cleaned_data.get('height') is not None:
                health_profile.height = form.cleaned_data['height']
            
            if form.cleaned_data.get('allergies'):
                health_profile.allergies = form.cleaned_data['allergies']
            
            if form.cleaned_data.get('chronic_conditions'):
                health_profile.chronic_conditions = form.cleaned_data['chronic_conditions']
            
            health_profile.save()
            messages.success(request, 'Health details saved successfully!')
            return redirect('signup_stage4')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        initial = {}
        if health_profile:
            initial = {
                'bp': health_profile.bp or '',
                'cholesterol': health_profile.cholesterol or '',
                'blood_sugar': health_profile.blood_sugar or '',
                'weight': health_profile.weight or '',
                'height': health_profile.height or '',
                'allergies': health_profile.allergies or '',
                'chronic_conditions': health_profile.chronic_conditions or '',
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
    total_symptom_checks = SymptomPrediction.objects.filter(user=user).count()
    recent_symptom_checks = SymptomPrediction.objects.filter(user=user).order_by('-created_at')[:5]
    latest_symptom = SymptomPrediction.objects.filter(user=user).first()
    total_prescriptions = Prescription.objects.filter(user=user).count()

    health_profile = getattr(user, 'health_profile', None)
    profile_complete = bool(
        user.first_name and user.last_name and user.phone_number and user.gender and user.age
    )

    context = {
        'total_symptom_checks': total_symptom_checks,
        'latest_symptom': latest_symptom,
        'total_prescriptions': total_prescriptions,
        'recent_symptom_checks': recent_symptom_checks,
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
    
    total_symptom_checks = SymptomPrediction.objects.filter(user=request.user).count()
    total_prescriptions = Prescription.objects.filter(user=request.user).count()
    
    context = {
        'form': form,
        'total_symptom_checks': total_symptom_checks,
        'total_prescriptions': total_prescriptions,
    }
    return render(request, 'core/profile.html', context)


@login_required
def add_medication(request):
    """Add a medication to user's list"""
    if request.method == 'POST':
        medication_name = request.POST.get('medication_name', '').strip()
        if medication_name:
            UserMedication.objects.get_or_create(
                user=request.user,
                medication_name=medication_name
            )
            messages.success(request, f'Added {medication_name} to your medications.')
        else:
            messages.error(request, 'Please enter a medication name.')
    return redirect('profile')


@login_required
def prescription_upload_view(request):
    """Upload a new prescription with structured data"""
    if request.method == 'POST':
        form = PrescriptionForm(request.POST, request.FILES)
        if form.is_valid():
            prescription = form.save(commit=False)
            prescription.user = request.user
            
            # Parse medicines from textarea
            medicines_text = request.POST.get('medicines', '')
            if medicines_text:
                structured_medicines = []
                for line in medicines_text.strip().split('\n'):
                    line = line.strip()
                    if line:
                        # Parse: Medicine Name - Dosage - Frequency - Duration
                        parts = [p.strip() for p in line.split('-')]
                        if len(parts) >= 1:
                            med_entry = {
                                'name': parts[0],
                                'dosage': parts[1] if len(parts) > 1 else '',
                                'frequency': parts[2] if len(parts) > 2 else '',
                                'duration': parts[3] if len(parts) > 3 else '',
                            }
                            structured_medicines.append(med_entry)
                            
                            # Add to user's medication list
                            med_name = parts[0].strip()
                            if med_name:
                                UserMedication.objects.get_or_create(
                                    user=request.user,
                                    medication_name=med_name
                                )
                prescription.medicines = structured_medicines
            
            prescription.save()
            messages.success(request, f'✅ Prescription for "{prescription.diagnosed_disease}" added successfully!')
            return redirect('prescription_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PrescriptionForm()
    
    return render(request, 'core/prescription_upload.html', {'form': form})


@login_required
def prescription_list_view(request):
    """List all prescriptions for the user"""
    prescriptions = Prescription.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'prescriptions': prescriptions,
        'total': prescriptions.count(),
    }
    return render(request, 'core/prescription_list.html', context)


@login_required
def prescription_detail_view(request, pk):
    """View detailed prescription information"""
    prescription = get_object_or_404(Prescription, id=pk, user=request.user)
    return render(request, 'core/prescription_detail.html', {'prescription': prescription})


@login_required
def delete_prescription_view(request, pk):
    """Delete a prescription"""
    prescription = get_object_or_404(Prescription, id=pk, user=request.user)
    
    if request.method == 'POST':
        disease_name = prescription.diagnosed_disease
        prescription.delete()
        messages.success(request, f'🗑️ Prescription for "{disease_name}" deleted successfully.')
    
    return redirect('prescription_list')


@login_required
def update_health(request):
    """Update user's health profile with new fields"""
    if request.method == 'POST':
        health_profile, created = UserHealthProfile.objects.get_or_create(user=request.user)
        
        # Update only if values are provided
        if request.POST.get('bp'):
            health_profile.bp = request.POST.get('bp')
        if request.POST.get('cholesterol'):
            health_profile.cholesterol = request.POST.get('cholesterol')
        if request.POST.get('blood_sugar'):
            health_profile.blood_sugar = request.POST.get('blood_sugar')
        if request.POST.get('weight'):
            try:
                health_profile.weight = float(request.POST.get('weight'))
            except ValueError:
                pass
        if request.POST.get('height'):
            try:
                health_profile.height = float(request.POST.get('height'))
            except ValueError:
                pass
        if request.POST.get('allergies'):
            health_profile.allergies = request.POST.get('allergies')
        if request.POST.get('chronic_conditions'):
            health_profile.chronic_conditions = request.POST.get('chronic_conditions')
        
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
    """API endpoint to analyze symptoms using Groq with full user context"""
    try:
        data = json.loads(request.body)
        symptoms_text = data.get('symptoms', '')
        
        if not symptoms_text:
            return JsonResponse({'error': 'No symptoms provided'}, status=400)
        
        # Get prediction from Groq with user context
        result = symptom_analyzer.predict_disease(symptoms_text, request.user)
        
        # Save to database with new fields
        symptom_prediction = SymptomPrediction.objects.create(
            user=request.user,
            symptoms=symptoms_text,
            predicted_disease=result.get('predicted_disease', 'Unknown'),
            confidence_score=result.get('confidence_score', 0),
            severity=result.get('severity', 'Unknown'),
            reasoning=result.get('reasoning', ''),
            suggested_drugs=result.get('suggested_drugs', []),
            common_symptoms_matched=result.get('common_symptoms_matched', []),
            drug_interactions=result.get('drug_interactions', []),
            safety_precautions=result.get('safety_precautions', []),
            when_to_see_doctor=result.get('when_to_see_doctor', ''),
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


@login_required
def update_location_view(request):
    """Update user's location"""
    if request.method == 'POST':
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        if latitude and longitude:
            try:
                request.user.latitude = float(latitude)
                request.user.longitude = float(longitude)
                request.user.save()
                messages.success(request, 'Location updated successfully!')
            except ValueError:
                messages.error(request, 'Invalid location coordinates.')
        else:
            messages.error(request, 'Please provide both latitude and longitude.')
    
    # Redirect back to the page they came from
    next_url = request.META.get('HTTP_REFERER', 'profile')
    return redirect(next_url)
