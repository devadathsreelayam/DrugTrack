from django.urls import path
from . import views

urlpatterns = [
    # Pharmacy registration
    path('login/', views.pharmacy_login_view, name='pharmacy_login'),
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
    
    # Orders (Direct)
    path('buy-now/<int:pharmacy_id>/<int:drug_id>/', views.buy_now, name='buy_now'),
    path('create-order-direct/', views.create_order_direct, name='create_order_direct'),
    path('orders/', views.order_list, name='order_list'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order/cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
    
    # Pharmacy order management
    path('pharmacy/orders/', views.pharmacy_order_list, name='pharmacy_order_list'),
    path('pharmacy/order/<int:order_id>/', views.pharmacy_order_detail, name='pharmacy_order_detail'),
    path('pharmacy/order/update/<int:order_id>/', views.update_order_status, name='update_order_status'),
]
