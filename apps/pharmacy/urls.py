from django.urls import path
from . import views

urlpatterns = [
    # Pharmacy registration
    path('register/', views.pharmacy_register, name='pharmacy_register'),
    path('dashboard/', views.pharmacy_dashboard, name='pharmacy_dashboard'),
    
    # Public pharmacy listing
    path('list/', views.pharmacy_list, name='pharmacy_list'),
    path('detail/<int:pk>/', views.pharmacy_detail, name='pharmacy_detail'),
    path('search/', views.pharmacy_search, name='pharmacy_search'),
    
    # Stock management
    path('stock/', views.stock_management, name='stock_management'),
    path('stock/add/', views.add_stock, name='add_stock'),
    path('stock/edit/<int:pk>/', views.edit_stock, name='edit_stock'),
    path('stock/delete/<int:pk>/', views.delete_stock, name='delete_stock'),
    
    # Ratings
    path('rate/<int:pk>/', views.rate_pharmacy, name='rate_pharmacy'),
]
