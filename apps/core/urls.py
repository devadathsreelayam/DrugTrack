from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_stage1, name='signup_stage1'),
    path('signup/stage2/', views.signup_stage2, name='signup_stage2'),
    path('signup/stage3/', views.signup_stage3, name='signup_stage3'),
    path('signup/stage4/', views.signup_stage4, name='signup_stage4'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('logout/', views.logout_view, name='logout'),
    
    # Core features
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('symptom-history/', views.symptom_history_view, name='symptom_history'),
    path('profile/', views.profile_view, name='profile'),
    
    # Prescription
    path('prescription/upload/', views.prescription_upload_view, name='prescription_upload'),
    path('prescription/list/', views.prescription_list_view, name='prescription_list'),
    path('prescription/detail/<int:pk>/', views.prescription_detail_view, name='prescription_detail'),
    path('prescription/delete/<int:pk>/', views.delete_prescription_view, name='delete_prescription'),

    # Location - Add this
    path('update-location/', views.update_location_view, name='update_location'),

    # Medication
    path('update-health/', views.update_health, name='update_health'),
    path('add-medication/', views.add_medication, name='add_medication'),
    path('remove-medication/<int:med_id>/', views.remove_medication, name='remove_medication'),

    # Symptom Checker URLs
    path('symptom-checker/', views.symptom_checker_view, name='symptom_checker'),
    path('analyze-symptoms/', views.analyze_symptoms_api, name='analyze_symptoms'),
    path('symptom-detail/<int:pk>/', views.symptom_detail_view, name='symptom_detail'),

]