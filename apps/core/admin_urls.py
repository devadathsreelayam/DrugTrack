from django.urls import path
from . import admin_views as views


urlpatterns = [
    # Admin panel
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('login/', views.admin_login_view, name='admin_login'),
    path('users/', views.admin_users, name='admin_users'),
    path('predictions/', views.admin_predictions, name='admin_predictions'),
    path('pharmacies/', views.admin_pharmacies, name='admin_pharmacies'),
    path('pharmacy-owners/', views.admin_pharmacy_owners, name='admin_pharmacy_owners'),
]