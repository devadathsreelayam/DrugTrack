from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Avg
from django.http import JsonResponse
from .forms import *
from .models import User, Prediction, Prescription, Medicine, UserHealthProfile, UserMedication, SymptomPrediction
from .utils.ml_predictor import predictor
from datetime import datetime
import math

import json
from .utils.symptom_analyser import symptom_analyzer
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


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
    """Stage 3: Health status"""
    # Check if health profile exists
    health_profile, created = UserHealthProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = Stage3HealthForm(request.POST)
        if form.is_valid():
            health_profile.bp = form.cleaned_data['bp']
            health_profile.cholesterol = form.cleaned_data['cholesterol']
            health_profile.na_to_k = form.cleaned_data['na_to_k']
            health_profile.save()
            
            messages.success(request, 'Health information saved!')
            return redirect('signup_stage4')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        # Pre-populate if exists
        initial = {
            'bp': health_profile.bp if health_profile.bp else '',
            'cholesterol': health_profile.cholesterol if health_profile.cholesterol else '',
            'na_to_k': health_profile.na_to_k if health_profile.na_to_k else '',
        }
        form = Stage3HealthForm(initial=initial)
    
    return render(request, 'accounts/signup_stage3.html', {'form': form, 'stage': 3})


@login_required
def signup_stage4(request):
    """Stage 4: Existing medications"""
    # Get user's current medications
    current_meds = UserMedication.objects.filter(user=request.user).values_list('medication_name', flat=True)
    
    if request.method == 'POST':
        form = Stage4MedicationsForm(request.POST)
        if form.is_valid():
            # Clear existing medications
            UserMedication.objects.filter(user=request.user).delete()
            
            # Add selected medications
            for med in form.cleaned_data['medications']:
                UserMedication.objects.create(user=request.user, medication_name=med)
            
            # Add other medications (split by comma or new line)
            other_meds = form.cleaned_data['other_medications']
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
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')

@login_required
def dashboard_view(request):
    user = request.user
    
    # Get statistics
    total_predictions = Prediction.objects.filter(user=user).count()
    latest_prediction = Prediction.objects.filter(user=user).first()
    total_prescriptions = Prescription.objects.filter(user=user).count()
    
    # Latest health metrics
    latest_metrics = None
    if latest_prediction:
        latest_metrics = {
            'bp': latest_prediction.bp,
            'cholesterol': latest_prediction.cholesterol,
            'drug': latest_prediction.predicted_drug
        }
    
    # Recent predictions (last 5)
    recent_predictions = Prediction.objects.filter(user=user)[:5]
    
    context = {
        'total_predictions': total_predictions,
        'latest_prediction': latest_prediction,
        'total_prescriptions': total_prescriptions,
        'latest_metrics': latest_metrics,
        'recent_predictions': recent_predictions,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def predict_view(request):
    prediction_result = None
    
    if request.method == 'POST':
        form = PredictionForm(request.POST)
        if form.is_valid():
            age = int(form.cleaned_data['age'])
            sex = form.cleaned_data['sex']
            bp = form.cleaned_data['bp']
            cholesterol = form.cleaned_data['cholesterol']
            na_to_k = form.cleaned_data['na_to_k']
            
            # Get prediction from ML model
            predicted_drug, confidence = predictor.predict(age, sex, bp, cholesterol, na_to_k)
            
            # Save to database
            prediction = Prediction.objects.create(
                user=request.user,
                age=age,
                sex=sex,
                bp=bp,
                cholesterol=cholesterol,
                na_to_k=na_to_k,
                predicted_drug=predicted_drug,
                confidence_score=confidence
            )
            
            # Get medicine details
            try:
                medicine = Medicine.objects.get(name__iexact=predicted_drug)
            except Medicine.DoesNotExist:
                medicine = None
            
            prediction_result = {
                'drug': predicted_drug,
                'confidence': round(confidence * 100, 1),
                'medicine': medicine,
                'prediction_id': prediction.id
            }
            
            messages.success(request, f'Prediction complete! Recommended: {predicted_drug}')
    else:
        form = PredictionForm()
    
    return render(request, 'core/predict.html', {
        'form': form,
        'prediction': prediction_result
    })

@login_required
def history_view(request):
    predictions = Prediction.objects.filter(user=request.user)
    
    # Statistics for charts
    drug_counts = {}
    bp_counts = {}
    chol_counts = {}
    
    for p in predictions:
        drug_counts[p.predicted_drug] = drug_counts.get(p.predicted_drug, 0) + 1
        bp_counts[p.bp] = bp_counts.get(p.bp, 0) + 1
        chol_counts[p.cholesterol] = chol_counts.get(p.cholesterol, 0) + 1
    
    # Prepare data for charts (convert to lists for JSON)
    drug_labels = list(drug_counts.keys())
    drug_data = list(drug_counts.values())
    bp_labels = list(bp_counts.keys())
    bp_data = list(bp_counts.values())
    chol_labels = list(chol_counts.keys())
    chol_data = list(chol_counts.values())
    
    context = {
        'predictions': predictions,
        'total': predictions.count(),
        'drug_counts': drug_counts,
        'bp_counts': bp_counts,
        'chol_counts': chol_counts,
        # Add these for JavaScript
        'drug_labels': drug_labels,
        'drug_data': drug_data,
        'bp_labels': bp_labels,
        'bp_data': bp_data,
        'chol_labels': chol_labels,
        'chol_data': chol_data,
    }
    return render(request, 'core/history.html', context)

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
def medicine_details_view(request):
    medicines = Medicine.objects.all()
    selected_medicine = None
    
    if request.method == 'POST':
        drug_name = request.POST.get('drug_name')
        if drug_name:
            try:
                selected_medicine = Medicine.objects.get(name__iexact=drug_name)
            except Medicine.DoesNotExist:
                messages.warning(request, f'Details for {drug_name} not found.')
    
    # Get all unique drug names from predictions for this user
    user_drugs = Prediction.objects.filter(user=request.user).values_list('predicted_drug', flat=True).distinct()
    
    context = {
        'medicines': medicines,
        'selected_medicine': selected_medicine,
        'user_drugs': user_drugs,
    }
    return render(request, 'core/medicine_details.html', context)

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

# Pharmacy related views (using admin-managed data)
@login_required
def pharmacy_list_view(request):
    from .models import Pharmacy
    
    pharmacies = Pharmacy.objects.filter(is_active=True)
    user_lat = request.user.latitude
    user_lon = request.user.longitude
    
    # Calculate distance for each pharmacy if user location exists
    for pharmacy in pharmacies:
        if user_lat and user_lon and pharmacy.latitude and pharmacy.longitude:
            pharmacy.distance = calculate_distance(
                user_lat, user_lon, 
                pharmacy.latitude, pharmacy.longitude
            )
        else:
            pharmacy.distance = None
    
    # Sort by distance
    pharmacies = sorted(pharmacies, key=lambda x: x.distance if x.distance else float('inf'))
    
    context = {
        'pharmacies': pharmacies,
        'user_location_set': user_lat is not None
    }
    return render(request, 'core/pharmacy_list.html', context)

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate Euclidean distance (simplified)"""
    return math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2) * 111  # Rough km conversion

@login_required
def update_location_view(request):
    if request.method == 'POST':
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        if latitude and longitude:
            request.user.latitude = float(latitude)
            request.user.longitude = float(longitude)
            request.user.save()
            messages.success(request, 'Location updated successfully!')
        else:
            messages.error(request, 'Invalid location data.')
    
    return redirect('pharmacy_list')


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
    """View past symptom analyses"""
    predictions = SymptomPrediction.objects.filter(user=request.user)
    
    context = {
        'predictions': predictions,
        'total': predictions.count(),
    }
    return render(request, 'core/symptom_history.html', context)


@login_required
def symptom_detail_view(request, pk):
    """View detailed symptom analysis"""
    prediction = get_object_or_404(SymptomPrediction, id=pk, user=request.user)
    return render(request, 'core/symptom_detail.html', {'prediction': prediction})
