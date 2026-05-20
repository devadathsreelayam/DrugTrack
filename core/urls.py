from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    
    # Core features
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('predict/', views.predict_view, name='predict'),
    path('history/', views.history_view, name='history'),
    path('profile/', views.profile_view, name='profile'),
    path('medicine-details/', views.medicine_details_view, name='medicine_details'),
    
    # Prescription
    path('prescription/upload/', views.prescription_upload_view, name='prescription_upload'),
    path('prescription/list/', views.prescription_list_view, name='prescription_list'),
    path('prescription/delete/<int:pk>/', views.delete_prescription_view, name='delete_prescription'),
    
    # Pharmacy
    path('pharmacy/', views.pharmacy_list_view, name='pharmacy_list'),
    path('update-location/', views.update_location_view, name='update_location'),
]