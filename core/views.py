from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Avg
from django.http import JsonResponse
from .forms import SignupForm, PredictionForm, PrescriptionForm, ProfileForm
from .models import User, Prediction, Prescription, Medicine
from .utils.ml_predictor import predictor
from datetime import datetime
import math

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
